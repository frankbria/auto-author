#!/usr/bin/env python3
"""
better-auth 1.7 account-identity backfill (issue #556)
======================================================

better-auth 1.7 made ``account.issuer`` a required field and keys accounts on the
unique pair ``(issuer, accountId)``. Its credential lookups all filter on it::

    // better-auth/dist/api/routes/sign-in.mjs
    const credentialIssuer = createLocalAccountIssuer("credential");  // "local:credential"
    const credentialAccount = userRecord?.accounts.find((account) =>
      account.providerId === "credential" &&
      account.issuer === credentialIssuer &&
      account.accountId === userRecord.user.id);

Rows written by 1.6 carry no ``issuer``, so the lookup misses and the server
answers ``401 INVALID_EMAIL_OR_PASSWORD`` while logging ``User not found`` about a
user it has already loaded. Deploying 1.7 without this backfill is a total auth
outage for every pre-1.7 account.

Two more paths go through the same ``findCredentialAccount`` filter, and they fail
differently — which is why running this *before* the deploy matters rather than
after:

* ``/change-password`` (``api/routes/update-user.mjs``) throws
  ``CREDENTIAL_ACCOUNT_NOT_FOUND``. Reachable only with a session cookie minted
  before the deploy, since sign-in is already refusing.
* ``/reset-password`` (``api/routes/password.mjs``) does **not** fail. Finding no
  credential account, it *creates a second one* with the correct issuer, and the
  user gets back in. The stale row stays. Both rows then key on
  ``(local:credential, <userId>)``, so this backfill refuses on the collision and
  the operator has to reconcile each one by hand. Every hour 1.7 serves pre-1.7
  accounts adds more of them.

The values below are the ones upstream prescribes for a credential account
(https://better-auth.com/docs/guides/1-7-upgrade-guide, "Account identity is
scoped by issuer"): ``issuer = "local:credential"`` and ``accountId`` = the linked
user's stable id. MongoDB needs no DDL — it is schemaless, and better-auth's Mongo
adapter creates the ``(issuer, accountId)`` unique index itself — so the whole
migration is this data backfill plus the collision check the guide requires before
that index exists.

This lives in the backend even though the ``account`` collection belongs to the
frontend's better-auth instance: the repo's migration pattern, a real MongoDB in
CI, and the test suite are all here, and the surgery is plain document editing.
Point it at whichever database better-auth writes to (the frontend's
``DATABASE_URL`` / ``DATABASE_NAME``), which need not be the backend's own.

Runbook
-------

1. **Stop authentication writes.** Take the app down, or at minimum stop sign-up
   and account linking. The guide asks for a maintenance window because a row
   inserted mid-run is not covered by the collision check.
2. **Back up the ``account`` and ``user`` collections.**
3. **Dry run** (the default — it writes nothing). Run it where better-auth's
   ``MONGODB_URI``/``DATABASE_NAME`` are set, which in the deployment means the
   backend container::

       docker compose exec backend python -m app.scripts.migration_account_issuer

   Read the counts and resolve anything it refuses on before going further. Do
   *not* spell it out as ``--mongodb-uri "$MONGODB_URI"``: under
   ``docker compose exec`` your host shell expands that, where it is unset, and
   the run would target an empty string. The flags exist only for a database the
   backend's own settings do not point at.
4. **Apply**::

       docker compose exec backend python -m app.scripts.migration_account_issuer --apply

5. **Re-run the dry run.** It is idempotent, so a clean second pass reports
   ``issuer_backfilled: 0`` and every row already migrated.
6. **Deploy 1.7**, then verify the acceptance test from #556: an account created
   under 1.6 still signs in.

Exit codes: ``0`` success, ``1`` refused (see the message), ``2`` connection or
argument error.
"""

import argparse
import asyncio
import logging
import os
import sys
from collections import defaultdict

from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

#: ``createLocalAccountIssuer("credential")`` in @better-auth/core.
LOCAL_CREDENTIAL_ISSUER = "local:credential"

ACCOUNT_COLLECTION = "account"
USER_COLLECTION = "user"
CREDENTIAL_PROVIDER = "credential"


class AccountIssuerBackfillError(RuntimeError):
    """The backfill refused to run. Nothing was written."""


async def backfill_account_issuer(db, *, dry_run: bool = True) -> dict:
    """Give every pre-1.7 credential account its 1.7 identity fields.

    Refuses (raising :class:`AccountIssuerBackfillError`, having written nothing)
    when it would have to guess: an unmigrated non-credential provider, whose
    trusted issuer is a deployment decision the guide says never to derive; or an
    ``(issuer, accountId)`` collision, which the new unique index would reject
    halfway through the write.

    Accounts whose ``userId`` matches no user are reported and skipped — they can
    never sign in with or without an issuer, and minting an identity for a user
    that does not exist is worse than leaving dead data alone.
    """
    accounts = await db[ACCOUNT_COLLECTION].find({}).to_list(length=None)
    stats = {
        "scanned": len(accounts),
        "already_migrated": 0,
        "issuer_backfilled": 0,
        "account_id_repaired": 0,
        "orphans": [],
        "dry_run": dry_run,
    }
    if not accounts:
        return stats

    needs_issuer = [a for a in accounts if not a.get("issuer")]
    stats["already_migrated"] = len(accounts) - len(needs_issuer)

    foreign = sorted(
        {a.get("providerId") for a in needs_issuer} - {CREDENTIAL_PROVIDER}
    )
    if foreign:
        raise AccountIssuerBackfillError(
            f"{len(needs_issuer)} account(s) need an issuer but "
            f"{', '.join(repr(p) for p in foreign)} is not a credential provider. "
            "A trusted issuer for an OAuth or SSO provider is a deployment "
            "decision and must never be derived from the row — see the 1.7 "
            "upgrade guide's issuer table, set those rows by hand, then re-run."
        )

    # Compared as strings, not as stored. better-auth's Mongo adapter coerces
    # id-referencing fields to ObjectId, so `userId` is normally an ObjectId — but
    # a row holding the hex string instead (a custom id generator, an import, a
    # hand-repaired document) would otherwise match no user, be filed as an orphan
    # and skipped, leaving a real person locked out while the run reported success.
    user_ids = {
        str(u["_id"])
        for u in await db[USER_COLLECTION].find({}, {"_id": 1}).to_list(length=None)
    }

    updates = []
    for account in needs_issuer:
        if str(account.get("userId")) not in user_ids:
            stats["orphans"].append(str(account["_id"]))
            continue
        target_account_id = str(account["userId"])
        changes = {"issuer": LOCAL_CREDENTIAL_ISSUER}
        if account.get("accountId") != target_account_id:
            changes["accountId"] = target_account_id
            stats["account_id_repaired"] += 1
        updates.append((account["_id"], changes))

    stats["issuer_backfilled"] = len(updates)

    _reject_collisions(accounts, updates)

    if dry_run:
        return stats

    for account_id, changes in updates:
        await db[ACCOUNT_COLLECTION].update_one({"_id": account_id}, {"$set": changes})
    return stats


def _reject_collisions(accounts, updates) -> None:
    """Fail if the post-backfill state would violate 1.7's unique (issuer, accountId).

    Checked against the whole collection, not just the rows being changed: a
    backfilled row can just as easily collide with one that is already migrated.
    """
    changes_by_id = dict(updates)
    keys = defaultdict(list)
    for account in accounts:
        merged = {**account, **changes_by_id.get(account["_id"], {})}
        if not merged.get("issuer"):
            continue  # skipped orphan — it keeps no identity to collide with
        keys[(merged["issuer"], merged.get("accountId"))].append(str(account["_id"]))

    collisions = {key: ids for key, ids in keys.items() if len(ids) > 1}
    if collisions:
        detail = "; ".join(
            f"{issuer}/{account_id} -> {', '.join(ids)}"
            for (issuer, account_id), ids in sorted(collisions.items())
        )
        raise AccountIssuerBackfillError(
            f"identity collision: {len(collisions)} (issuer, accountId) key(s) map to "
            f"more than one account row, which 1.7's unique index rejects. Nothing "
            f"was written. Reconcile these by hand and re-run: {detail}"
        )


def _resolve_connection(uri, database, env):
    """Take the connection from the flags, else from the process environment.

    The runbook runs this inside the backend container, where compose has already
    put `MONGODB_URI` and `DATABASE_NAME`. Requiring the operator to pass them as
    `--mongodb-uri "$MONGODB_URI"` under `docker compose exec` would expand them
    on the *host*, where they are unset — so the gate would run against an empty
    URI. Default to the environment and keep the flags for the case where the
    better-auth database is somewhere the backend's own settings do not point.

    `DATABASE_URL` is the same connection string under the name the frontend
    container sees; the backend's settings prefer `MONGODB_URI` over it, so match
    that order rather than inventing a new one.
    """
    uri = uri or env.get("MONGODB_URI") or env.get("DATABASE_URL")
    database = database or env.get("DATABASE_NAME")
    if not uri:
        raise AccountIssuerBackfillError(
            "no MongoDB connection string: pass --mongodb-uri, or run where "
            "MONGODB_URI (or DATABASE_URL) is set. If you are using `docker compose "
            "exec`, note that $MONGODB_URI in that command line is expanded by your "
            "shell, not the container's."
        )
    if not database:
        raise AccountIssuerBackfillError(
            "no database name: pass --database, or run where DATABASE_NAME is set."
        )
    return uri, database


async def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill better-auth 1.7 account identity fields (#556).",
    )
    parser.add_argument(
        "--mongodb-uri",
        help="better-auth's MongoDB connection string (default: $MONGODB_URI, else $DATABASE_URL)",
    )
    parser.add_argument(
        "--database",
        help="database better-auth writes to (default: $DATABASE_NAME)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the changes; without it the run is a dry run and touches nothing",
    )
    args = parser.parse_args(argv)

    try:
        uri, database = _resolve_connection(args.mongodb_uri, args.database, os.environ)
    except AccountIssuerBackfillError as exc:
        logger.error("%s", exc)
        return 2

    client = AsyncIOMotorClient(uri)
    try:
        stats = await backfill_account_issuer(client[database], dry_run=not args.apply)
    except AccountIssuerBackfillError as exc:
        logger.error("Refused: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001 - operator-facing CLI
        # Deliberately broad: a bad URI, rejected Atlas credentials or a wrong
        # database name all surface here, and an operator mid-maintenance-window
        # wants one clear line and an exit code, not a traceback.
        logger.error("Backfill failed: %s", exc)
        return 2
    finally:
        client.close()

    logger.info(
        "%s: scanned=%d already_migrated=%d issuer_backfilled=%d account_id_repaired=%d",
        "DRY RUN (nothing written)" if stats["dry_run"] else "APPLIED",
        stats["scanned"],
        stats["already_migrated"],
        stats["issuer_backfilled"],
        stats["account_id_repaired"],
    )
    if stats["orphans"]:
        logger.warning(
            "Skipped %d account(s) whose userId matches no user — they cannot sign in "
            "either way, but they are unexpected: %s",
            len(stats["orphans"]),
            ", ".join(stats["orphans"]),
        )
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    sys.exit(asyncio.run(_main()))
