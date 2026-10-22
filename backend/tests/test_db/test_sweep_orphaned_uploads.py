"""The orphaned-upload sweep (#938).

Local storage is real files in a per-test directory and MongoDB is real. S3 and
Cloudinary have no local form, so their SDK clients are stand-ins answering in
the shape the real calls return; the listing, matching and deleting are the
real code.
"""

import os
import time
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from bson import ObjectId
from botocore.exceptions import ClientError

import app.scripts.sweep_orphaned_uploads as sweep_module
import app.services.file_upload_service as fus
from app.db import base
from app.scripts.sweep_orphaned_uploads import (
    LocalUploads,
    _main,
    sweep_orphaned_uploads,
)
from app.services.cloud_storage_service import (
    CloudinaryStorageService,
    S3StorageService,
)
from tests.conftest import TEST_MONGO_URI

pytestmark = pytest.mark.asyncio

HOUR = timedelta(hours=1)
BOOK = "64b000000000000000000001"
HEX = "0123456789abcdef0123456789abcdef"
HEX2 = "fedcba9876543210fedcba9876543210"
OLD = time.time() - 3 * 3600


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    covers = tmp_path / "cover_images"
    avatars = tmp_path / "profile_pictures"
    covers.mkdir()
    avatars.mkdir()
    monkeypatch.setattr(fus, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(fus, "COVER_IMAGES_DIR", covers)
    monkeypatch.setattr(fus, "PROFILE_PICTURES_DIR", avatars)
    return SimpleNamespace(root=tmp_path, covers=covers, avatars=avatars)


def _file(directory, name, mtime=OLD):
    path = directory / name
    path.write_bytes(b"img")
    os.utime(path, (mtime, mtime))
    return path


async def _seed_local(uploads):
    """A referenced cover pair and avatar, an orphan of each kind, a young
    orphan, and files outside the two prefixes."""
    db = base.get_database()
    cover, thumb = f"{BOOK}_{HEX}.jpg", f"{BOOK}_{HEX}_thumb.jpg"
    for name in (cover, thumb, f"{BOOK}_{HEX2}.jpg", f"{BOOK}_{HEX2}_thumb.jpg"):
        _file(uploads.covers, name)
    _file(uploads.avatars, f"alice_{HEX}.png")
    _file(uploads.avatars, f"gone_{HEX}.png")
    _file(uploads.covers, f"{BOOK}_{'a' * 32}.jpg", mtime=time.time())  # young
    (uploads.root / "exports").mkdir()
    _file(uploads.root / "exports", "book.pdf")
    _file(uploads.root, "stray.jpg")
    await db["books"].insert_one(
        {
            "_id": ObjectId(BOOK),
            "owner_id": "alice",
            "cover_image_url": f"/uploads/cover_images/{cover}",
            "cover_thumbnail_url": f"/uploads/cover_images/{thumb}",
        }
    )
    await db["users"].insert_one(
        {"auth_id": "alice", "avatar_url": f"/uploads/profile_pictures/alice_{HEX}.png"}
    )
    return db


def _names(directory):
    return sorted(p.name for p in directory.iterdir())


ORPHANS = [
    f"cover_images/{BOOK}_{HEX2}.jpg",
    f"cover_images/{BOOK}_{HEX2}_thumb.jpg",
    f"profile_pictures/gone_{HEX}.png",
]


# --- local storage -----------------------------------------------------------


async def test_dry_run_reports_orphans_and_deletes_nothing(reinit_db, uploads):
    db = await _seed_local(uploads)
    before = sorted(str(p) for p in uploads.root.rglob("*"))

    stats = await sweep_orphaned_uploads(db, LocalUploads(), grace=HOUR)

    assert sorted(stats["orphans"]) == ORPHANS
    assert stats["deleted"] == [] and stats["dry_run"] is True
    assert sorted(str(p) for p in uploads.root.rglob("*")) == before


async def test_apply_removes_only_the_orphans(reinit_db, uploads):
    db = await _seed_local(uploads)

    stats = await sweep_orphaned_uploads(db, LocalUploads(), grace=HOUR, apply=True)

    assert sorted(stats["deleted"]) == ORPHANS and stats["failed"] == []
    assert _names(uploads.covers) == sorted(
        [f"{BOOK}_{HEX}.jpg", f"{BOOK}_{HEX}_thumb.jpg", f"{BOOK}_{'a' * 32}.jpg"]
    )
    assert _names(uploads.avatars) == [f"alice_{HEX}.png"]
    assert (uploads.root / "stray.jpg").exists()
    assert (uploads.root / "exports" / "book.pdf").exists()


async def test_a_file_inside_the_grace_window_is_skipped(reinit_db, uploads):
    db = await _seed_local(uploads)

    stats = await sweep_orphaned_uploads(db, LocalUploads(), grace=HOUR, apply=True)

    assert stats["young"] == [f"cover_images/{BOOK}_{'a' * 32}.jpg"]
    assert (uploads.covers / f"{BOOK}_{'a' * 32}.jpg").exists()

    # A zero window makes it a candidate like any other.
    stats = await sweep_orphaned_uploads(db, LocalUploads(), grace=timedelta(0))
    assert stats["orphans"] == [f"cover_images/{BOOK}_{'a' * 32}.jpg"]


async def test_objects_outside_the_prefixes_are_never_listed(reinit_db, uploads):
    db = await _seed_local(uploads)

    stats = await sweep_orphaned_uploads(db, LocalUploads(), grace=timedelta(0))

    listed = stats["referenced"] + stats["orphans"] + stats["young"]
    assert all(k.startswith(("cover_images/", "profile_pictures/")) for k in listed)
    assert len(listed) == 7


async def test_the_command_line_is_a_dry_run_by_default(reinit_db, uploads, monkeypatch, caplog):
    db = await _seed_local(uploads)
    monkeypatch.setattr(sweep_module, "get_cloud_storage_service", lambda: None)
    args = ["--mongodb-uri", TEST_MONGO_URI, "--database", db.name]

    with caplog.at_level("INFO", logger=sweep_module.__name__):
        assert await _main(args) == 0
    assert len(_names(uploads.covers)) == 5
    assert all(any(k in r.getMessage() for r in caplog.records) for k in ORPHANS)

    assert await _main([*args, "--apply"]) == 0
    assert len(_names(uploads.covers)) == 3


# --- S3 ----------------------------------------------------------------------


def _s3():
    service = S3StorageService.__new__(S3StorageService)
    service.bucket_name = "bkt"
    service.region = "us-east-1"
    service.ClientError = ClientError
    service.s3_client = Mock()
    return service


async def test_s3_lists_every_page_under_the_prefix():
    s3 = _s3()
    when = sweep_module.datetime(2026, 1, 1, tzinfo=sweep_module.timezone.utc)
    s3.s3_client.get_paginator.return_value.paginate.return_value = [
        {"Contents": [{"Key": f"cover_images/{BOOK}/{HEX}.jpg", "LastModified": when}]},
        {"Contents": [{"Key": f"cover_images/{BOOK}/thumbnails/{HEX2}.jpg", "LastModified": when}]},
        {},  # an empty listing has no Contents key
    ]

    objects = await s3.list_objects("cover_images/")

    s3.s3_client.get_paginator.assert_called_once_with("list_objects_v2")
    s3.s3_client.get_paginator.return_value.paginate.assert_called_once_with(
        Bucket="bkt", Prefix="cover_images/"
    )
    assert [o.key for o in objects] == [
        f"cover_images/{BOOK}/{HEX}.jpg",
        f"cover_images/{BOOK}/thumbnails/{HEX2}.jpg",
    ]
    assert objects[0].url == f"https://bkt.s3.us-east-1.amazonaws.com/cover_images/{BOOK}/{HEX}.jpg"
    assert objects[0].modified == when


async def test_s3_sweep_deletes_only_the_unreferenced_key(reinit_db):
    db = base.get_database()
    s3 = _s3()
    host = "https://bkt.s3.us-east-1.amazonaws.com"
    live, orphan = f"cover_images/{BOOK}/{HEX}.jpg", f"cover_images/{BOOK}/{HEX2}.jpg"
    old = sweep_module.datetime(2020, 1, 1, tzinfo=sweep_module.timezone.utc)
    s3.s3_client.get_paginator.return_value.paginate.side_effect = lambda Bucket, Prefix: (
        [{"Contents": [{"Key": k, "LastModified": old} for k in (live, orphan) if k.startswith(Prefix)]}]
    )
    await db["books"].insert_one({"owner_id": "a", "cover_image_url": f"{host}/{live}"})

    stats = await sweep_orphaned_uploads(db, s3, grace=HOUR, apply=True)

    assert stats["deleted"] == [orphan]
    s3.s3_client.delete_object.assert_called_once_with(Bucket="bkt", Key=orphan)


# --- Cloudinary --------------------------------------------------------------


def _cloudinary():
    service = CloudinaryStorageService.__new__(CloudinaryStorageService)
    service.cloudinary_uploader = Mock()
    service.cloudinary_uploader.destroy.return_value = {"result": "ok"}
    service.cloudinary_api = Mock()
    return service


def _resource(public_id, created_at="2020-01-01T00:00:00Z"):
    return {
        "public_id": public_id,
        "secure_url": f"https://res.cloudinary.com/demo/image/upload/v1577836800/{public_id}.jpg",
        "created_at": created_at,
    }


async def test_cloudinary_lists_every_page_under_the_prefix():
    cld = _cloudinary()
    cld.cloudinary_api.resources.side_effect = [
        {"resources": [_resource(f"cover_images/{BOOK}/{HEX}")], "next_cursor": "c2"},
        {"resources": [_resource(f"cover_images/{BOOK}/thumbnails/{HEX2}")]},
    ]

    objects = await cld.list_objects("cover_images/")

    calls = cld.cloudinary_api.resources.call_args_list
    assert [c.kwargs for c in calls] == [
        {"type": "upload", "prefix": "cover_images/", "max_results": 500},
        {"type": "upload", "prefix": "cover_images/", "max_results": 500, "next_cursor": "c2"},
    ]
    assert [o.key for o in objects] == [
        f"cover_images/{BOOK}/{HEX}",
        f"cover_images/{BOOK}/thumbnails/{HEX2}",
    ]
    assert objects[0].modified.year == 2020 and objects[0].modified.tzinfo is not None


async def test_cloudinary_sweep_matches_the_stored_url_to_the_public_id(reinit_db):
    db = base.get_database()
    cld = _cloudinary()
    live, orphan = _resource(f"profile_pictures/alice/{HEX}"), _resource(f"profile_pictures/alice/{HEX2}")
    cld.cloudinary_api.resources.side_effect = lambda **kw: {
        "resources": [r for r in (live, orphan) if r["public_id"].startswith(kw["prefix"])]
    }
    await db["users"].insert_one({"auth_id": "alice", "avatar_url": live["secure_url"]})

    stats = await sweep_orphaned_uploads(db, cld, grace=HOUR, apply=True)

    assert stats["referenced"] == [live["public_id"]]
    assert stats["deleted"] == [orphan["public_id"]]
    cld.cloudinary_uploader.destroy.assert_called_once_with(orphan["public_id"])


async def test_apply_refuses_when_no_record_references_anything(reinit_db, uploads, monkeypatch):
    """A wrong or empty --database makes every file look orphaned; --apply must not
    delete them all unless told the empty database is intended."""
    _file(uploads.covers, f"{BOOK}_{HEX}.jpg")
    _file(uploads.avatars, f"alice_{HEX}.png")
    monkeypatch.setattr(sweep_module, "get_cloud_storage_service", lambda: None)
    args = ["--mongodb-uri", TEST_MONGO_URI, "--database", base.get_database().name, "--apply"]

    assert await _main(args) == 2
    assert len(_names(uploads.covers)) == 1 and len(_names(uploads.avatars)) == 1

    assert await _main([*args, "--allow-no-references"]) == 0
    assert _names(uploads.covers) == [] and _names(uploads.avatars) == []
