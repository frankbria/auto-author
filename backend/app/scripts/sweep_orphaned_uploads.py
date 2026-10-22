#!/usr/bin/env python3
"""
Orphaned upload sweep (issue #938)
==================================

Lists the stored objects under ``cover_images/`` and ``profile_pictures/`` that no
``books`` document (``cover_image_url``, ``cover_thumbnail_url``) and no ``users``
document (``avatar_url``) points at, and deletes them when asked to. Covers the
files every best-effort delete can leave behind: a storage delete that failed, a
process that died after the database delete committed, uploads that raced, and
files written before those paths cleaned up after themselves.

Rules:

* **Orphan:** any object under the two prefixes whose key no record's URL holds.
  A URL is reduced to the part from the first ``cover_images/`` or
  ``profile_pictures/`` on, without query or fragment, which is the key for local
  storage and S3; the same without its extension is a Cloudinary public_id. A URL
  that holds a key protects it, so a URL this cannot read keeps a file rather than
  losing one.
* **Grace window:** an object written in the last ``--grace-minutes`` (default 60)
  is skipped. An upload is stored before the record that names it is written, and
  this must not sweep it in between.
* Objects are listed *before* the records are read, so a record written after the
  listing still protects its file. Nothing outside the two prefixes is listed, and
  each delete goes through the provider's prefix guard.

Storage is whatever the backend is configured for (``settings.storage_provider``:
S3, Cloudinary, or the local ``uploads/`` directory under the working directory).

Run it from a throwaway container off the deployed image, exactly like the
account-issuer backfill (``docs/STAGING-DEPLOYMENT.md``)::

    python -m app.scripts.sweep_orphaned_uploads             # dry run, deletes nothing
    python -m app.scripts.sweep_orphaned_uploads --apply     # deletes the candidates

Exit codes: ``0`` success, ``1`` at least one delete failed (each is logged),
``2`` connection, configuration or argument error.
"""

import argparse
import asyncio
import logging
import os
import posixpath
import sys
from datetime import datetime, timedelta, timezone

from pymongo import AsyncMongoClient

import app.services.file_upload_service as fus
from app.scripts.migration_account_issuer import (
    AccountIssuerBackfillError,
    _client_kwargs,
    _resolve_connection,
)
from app.services.cloud_storage_service import (
    StoredObject,
    _is_owned_key,
    get_cloud_storage_service,
)

logger = logging.getLogger(__name__)

PREFIXES = ("cover_images/", "profile_pictures/")
LOCAL_URL_PREFIX = "/uploads/"


class LocalUploads:
    """The local ``uploads/`` directory, behind the same two calls as a cloud
    provider. Directories are read at call time so tests can point them elsewhere."""

    @staticmethod
    def _dir(prefix):
        return {"cover_images/": fus.COVER_IMAGES_DIR, "profile_pictures/": fus.PROFILE_PICTURES_DIR}[prefix]

    async def list_objects(self, prefix):
        base = self._dir(prefix)
        if not base.exists():
            return []
        objects = []
        for path in base.rglob("*"):
            if path.is_file():
                key = prefix + path.relative_to(base).as_posix()
                modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                objects.append(StoredObject(key, LOCAL_URL_PREFIX + key, modified))
        return objects

    async def delete_image(self, url, key_prefix):
        key = url.removeprefix(LOCAL_URL_PREFIX)
        if not _is_owned_key(key, key_prefix):
            return False
        (self._dir(key_prefix) / key[len(key_prefix):]).unlink()
        return True


def _keys_named_by(url):
    """The storage keys a stored URL can name (see the module docstring)."""
    if not isinstance(url, str):
        return set()
    starts = [i for i in (url.find(p) for p in PREFIXES) if i >= 0]
    if not starts:
        return set()
    key = url[min(starts):].split("?", 1)[0].split("#", 1)[0]
    return {key, posixpath.splitext(key)[0]}


async def _referenced_keys(db):
    keys = set()
    async for book in db["books"].find({}, {"cover_image_url": 1, "cover_thumbnail_url": 1}):
        keys |= _keys_named_by(book.get("cover_image_url"))
        keys |= _keys_named_by(book.get("cover_thumbnail_url"))
    async for user in db["users"].find({}, {"avatar_url": 1}):
        keys |= _keys_named_by(user.get("avatar_url"))
    return keys


async def sweep_orphaned_uploads(db, storage, *, grace, apply=False, now=None) -> dict:
    """Find (and with ``apply``, delete) unreferenced objects under ``PREFIXES``.

    ``storage`` is a cloud provider or :class:`LocalUploads`. Returns the keys in
    each outcome; a failed delete is logged and listed, never raised.
    """
    cutoff = (now or datetime.now(timezone.utc)) - grace
    objects = [obj for prefix in PREFIXES for obj in await storage.list_objects(prefix)]
    referenced = await _referenced_keys(db)  # after the listing: see the docstring
    stats = {"referenced": [], "young": [], "orphans": [], "deleted": [], "failed": [], "dry_run": not apply}

    for obj in objects:
        prefix = next((p for p in PREFIXES if obj.key.startswith(p)), None)
        if prefix is None:
            continue  # a provider that ignored the prefix; never touch it
        if obj.key in referenced:
            stats["referenced"].append(obj.key)
            continue
        if obj.modified > cutoff:
            logger.info("Skipping %s: written %s, inside the grace window", obj.key, obj.modified.isoformat())
            stats["young"].append(obj.key)
            continue
        stats["orphans"].append(obj.key)
        logger.info("Orphan: %s (written %s)", obj.key, obj.modified.isoformat())
        if not apply:
            continue
        try:
            removed = await storage.delete_image(obj.url, prefix)
        except Exception as exc:  # noqa: BLE001 - one failure must not stop the sweep
            logger.error("Failed to delete %s: %s", obj.key, exc)
            removed = False
        if removed:
            logger.info("Deleted: %s", obj.key)
            stats["deleted"].append(obj.key)
        else:
            logger.error("Storage did not delete %s", obj.key)
            stats["failed"].append(obj.key)
    return stats


async def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="List (and with --apply, delete) uploads no record references (#938).",
    )
    parser.add_argument("--mongodb-uri", help="MongoDB connection string (default: $MONGODB_URI, else $DATABASE_URL)")
    parser.add_argument("--database", help="database name (default: $DATABASE_NAME)")
    parser.add_argument("--apply", action="store_true", help="delete the orphans; without it nothing is deleted")
    parser.add_argument(
        "--grace-minutes", type=int, default=60,
        help="skip objects written this recently (default: 60)",
    )
    args = parser.parse_args(argv)
    if args.grace_minutes < 0:
        parser.error("--grace-minutes cannot be negative")

    try:
        uri, database = _resolve_connection(args.mongodb_uri, args.database, os.environ)
        storage = get_cloud_storage_service() or LocalUploads()
    except AccountIssuerBackfillError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:  # noqa: BLE001 - operator-facing CLI
        logger.error("Storage is not configured: %s", exc)
        return 2

    client = AsyncMongoClient(uri, **_client_kwargs(uri))
    try:
        stats = await sweep_orphaned_uploads(
            client[database], storage, grace=timedelta(minutes=args.grace_minutes), apply=args.apply
        )
    except Exception as exc:  # noqa: BLE001 - operator-facing CLI
        logger.error("Sweep failed: %s", exc)
        return 2
    finally:
        await client.close()

    logger.info(
        "%s (%s): referenced=%d in_grace_window=%d orphans=%d deleted=%d failed=%d",
        "DRY RUN (nothing deleted)" if stats["dry_run"] else "APPLIED",
        type(storage).__name__,
        len(stats["referenced"]),
        len(stats["young"]),
        len(stats["orphans"]),
        len(stats["deleted"]),
        len(stats["failed"]),
    )
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    sys.exit(asyncio.run(_main()))
