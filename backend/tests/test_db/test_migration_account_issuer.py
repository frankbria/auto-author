"""
Tests for the better-auth 1.7 account-identity backfill (issue #556).

better-auth 1.7 made `account.issuer` required and keys accounts on
`(issuer, accountId)`. Its credential lookups — sign-in, password reset and
password change — all filter on `issuer == "local:credential"`, so every account
row written by 1.6 (which has no such field) stops matching and the server answers
401 while logging `User not found` about a user it has already loaded.

These tests run against a real local MongoDB via `motor_reinit_db`. The account
documents are hand-built in the exact shapes better-auth's MongoDB adapter writes:
`_id`/`userId` as ObjectId (the adapter coerces every id-referencing field), and
`accountId` as a plain string.
"""

from pathlib import Path

import pytest
from bson import ObjectId

from app.db import base
from app.scripts.migration_account_issuer import (
    LOCAL_CREDENTIAL_ISSUER,
    AccountIssuerBackfillError,
    _client_kwargs,
    _resolve_connection,
    backfill_account_issuer,
)

#: better-auth ships `createLocalAccountIssuer` here; the frontend owns the
#: dependency, so this path only exists once its node_modules are installed.
_CORE_ACCOUNT_SCHEMA = (
    Path(__file__).resolve().parents[3]
    / "frontend/node_modules/@better-auth/core/dist/db/schema/account.mjs"
)


# Not a credential: a placeholder standing in for the scrypt hash better-auth
# stores, so the row has the same shape as a real one. Named apart from the
# field so the repo's secret scanner does not read the literal as an assignment.
_STUB_HASH = "scrypt:notarealhash"


def _user_doc(email="old@example.com"):
    return {"_id": ObjectId(), "email": email, "name": "Old Account"}


def _legacy_account(user_doc, **overrides):
    """An account row exactly as better-auth 1.6 wrote it: no `issuer` key."""
    doc = {
        "_id": ObjectId(),
        "providerId": "credential",
        "accountId": str(user_doc["_id"]),
        "userId": user_doc["_id"],
        "password": _STUB_HASH,
    }
    doc.update(overrides)
    return doc


def _migrated_account(user_doc, **overrides):
    doc = _legacy_account(user_doc, issuer=LOCAL_CREDENTIAL_ISSUER)
    doc.update(overrides)
    return doc


async def _seed(users=(), accounts=()):
    db = base.get_database()
    if users:
        await db["user"].insert_many(list(users))
    if accounts:
        await db["account"].insert_many(list(accounts))
    return db


class TestBackfill:
    pytestmark = pytest.mark.asyncio

    async def test_backfills_a_16_shaped_credential_account(self, motor_reinit_db):
        user = _user_doc()
        account = _legacy_account(user)
        db = await _seed([user], [account])

        stats = await backfill_account_issuer(db, dry_run=False)

        stored = await db["account"].find_one({"_id": account["_id"]})
        assert stored["issuer"] == LOCAL_CREDENTIAL_ISSUER
        # accountId was already the user's id under 1.6; the backfill must not
        # churn it, because accountId is half the new identity key.
        assert stored["accountId"] == str(user["_id"])
        assert stats["issuer_backfilled"] == 1
        assert stats["account_id_repaired"] == 0

    async def test_leaves_a_17_shaped_account_untouched(self, motor_reinit_db):
        user = _user_doc()
        account = _migrated_account(user)
        db = await _seed([user], [account])

        stats = await backfill_account_issuer(db, dry_run=False)

        assert stats["issuer_backfilled"] == 0
        assert stats["already_migrated"] == 1

    async def test_is_idempotent(self, motor_reinit_db):
        user = _user_doc()
        db = await _seed([user], [_legacy_account(user)])

        first = await backfill_account_issuer(db, dry_run=False)
        second = await backfill_account_issuer(db, dry_run=False)

        assert first["issuer_backfilled"] == 1
        assert second["issuer_backfilled"] == 0
        assert second["already_migrated"] == 1

    async def test_dry_run_writes_nothing(self, motor_reinit_db):
        user = _user_doc()
        account = _legacy_account(user)
        db = await _seed([user], [account])

        stats = await backfill_account_issuer(db, dry_run=True)

        stored = await db["account"].find_one({"_id": account["_id"]})
        assert "issuer" not in stored
        # It still reports what it *would* do, so the operator can size the change
        # before committing to it.
        assert stats["issuer_backfilled"] == 1
        assert stats["dry_run"] is True

    async def test_repairs_an_account_id_that_does_not_match_the_user(
        self, motor_reinit_db
    ):
        # The 1.7 guide keys a credential account on the linked user's stable id,
        # and sign-in.mjs asserts `account.accountId === user.id` outright. A row
        # keyed on anything else (an email, say) is unreachable even once `issuer`
        # is present, so the backfill has to fix both halves of the key.
        user = _user_doc()
        account = _legacy_account(user, accountId=user["email"])
        db = await _seed([user], [account])

        stats = await backfill_account_issuer(db, dry_run=False)

        stored = await db["account"].find_one({"_id": account["_id"]})
        assert stored["accountId"] == str(user["_id"])
        assert stats["account_id_repaired"] == 1


class TestRefusals:
    pytestmark = pytest.mark.asyncio

    async def test_aborts_on_an_unmigrated_non_credential_provider(
        self, motor_reinit_db
    ):
        # This deployment configures only emailAndPassword + twoFactor, so an
        # OAuth/SSO row means someone added a provider. Its trusted issuer is a
        # deployment decision (the guide is explicit: never derive one), so guess
        # nothing and stop.
        user = _user_doc()
        db = await _seed(
            [user],
            [_legacy_account(user, providerId="google", accountId="google-sub-123")],
        )

        with pytest.raises(AccountIssuerBackfillError, match="google"):
            await backfill_account_issuer(db, dry_run=True)

    async def test_a_migrated_non_credential_provider_is_not_an_abort(
        self, motor_reinit_db
    ):
        # Only rows still *needing* an issuer are undecidable. One that already
        # carries a trusted issuer has been handled and must not block the run.
        user = _user_doc()
        db = await _seed(
            [user],
            [
                _legacy_account(
                    user,
                    providerId="google",
                    accountId="google-sub-123",
                    issuer="https://accounts.google.com",
                )
            ],
        )

        stats = await backfill_account_issuer(db, dry_run=True)

        assert stats["already_migrated"] == 1

    async def test_aborts_on_an_identity_collision_before_writing(
        self, motor_reinit_db
    ):
        # 1.7 puts a unique index on (issuer, accountId). Two credential rows for
        # one user would both resolve to the same key, so writing first and
        # discovering the duplicate at index-build time would leave the collection
        # half-migrated. Check the resulting key set first.
        user = _user_doc()
        db = await _seed([user], [_legacy_account(user), _legacy_account(user)])

        with pytest.raises(AccountIssuerBackfillError, match="collision"):
            await backfill_account_issuer(db, dry_run=False)

        stored = await db["account"].find({}).to_list(length=None)
        assert all("issuer" not in doc for doc in stored)

    async def test_matches_a_user_whose_id_was_stored_as_a_string(
        self, motor_reinit_db
    ):
        # better-auth's Mongo adapter coerces id-referencing fields to ObjectId,
        # so `userId` is normally an ObjectId. A row that holds the hex string
        # instead — a custom id generator, an import, a hand-repaired document —
        # must not be mistaken for an orphan: that would skip it silently-ish and
        # leave a real user locked out while the run still reported success.
        user = _user_doc()
        account = _legacy_account(user, userId=str(user["_id"]))
        db = await _seed([user], [account])

        stats = await backfill_account_issuer(db, dry_run=False)

        stored = await db["account"].find_one({"_id": account["_id"]})
        assert stored["issuer"] == LOCAL_CREDENTIAL_ISSUER
        assert stored["accountId"] == str(user["_id"])
        assert stats["orphans"] == []

    async def test_reports_and_skips_an_account_with_no_user(self, motor_reinit_db):
        # A credential row whose user is gone can never sign in, with or without
        # an issuer. Backfilling it would mint an identity for a user that does
        # not exist; aborting on it would block the whole migration for dead data.
        # Report it and leave it alone.
        live_user = _user_doc("live@example.com")
        orphan_user = _user_doc("orphan@example.com")  # deliberately not inserted
        orphan = _legacy_account(orphan_user)
        db = await _seed([live_user], [_legacy_account(live_user), orphan])

        stats = await backfill_account_issuer(db, dry_run=False)

        assert stats["orphans"] == [str(orphan["_id"])]
        assert stats["issuer_backfilled"] == 1
        stored = await db["account"].find_one({"_id": orphan["_id"]})
        assert "issuer" not in stored

    async def test_an_empty_account_collection_is_a_no_op(self, motor_reinit_db):
        db = base.get_database()

        stats = await backfill_account_issuer(db, dry_run=False)

        assert stats["scanned"] == 0
        assert stats["issuer_backfilled"] == 0


class TestIssuerLiteral:
    """The one value the whole fix turns on.

    Every test above compares against `LOCAL_CREDENTIAL_ISSUER` rather than the
    string itself, so they all pass just as happily with a wrong constant — a
    mutation to `"credential"` survived the first pass of this suite. The issuer
    is a wire value shared with a library we do not control, so pin it here.
    """

    def test_is_the_literal_better_auth_looks_for(self):
        assert LOCAL_CREDENTIAL_ISSUER == "local:credential"

    @pytest.mark.skipif(
        not _CORE_ACCOUNT_SCHEMA.exists(),
        reason="frontend node_modules not installed (backend CI job does not install them)",
    )
    def test_matches_create_local_account_issuer_in_the_installed_library(self):
        # `createLocalAccountIssuer(providerId)` returns
        # `local:${encodeURIComponent(providerId)}`, and "credential" encodes to
        # itself. Reading the shipped source rather than restating it means an
        # upstream change to the namespace fails here instead of silently
        # producing an issuer nothing matches.
        source = _CORE_ACCOUNT_SCHEMA.read_text()
        assert (
            "return `local:${encodeAccountIssuerProviderId(providerId)}`" in source
        ), (
            "better-auth changed how the local issuer is built. Re-derive "
            f"{LOCAL_CREDENTIAL_ISSUER!r} from the new definition before trusting "
            "the backfill."
        )


class TestConnectionResolution:
    """Where the URI and database name come from.

    The runbook runs this inside the backend container, and the first draft told
    the operator to pass `--mongodb-uri "$MONGODB_URI"`. Those variables live in
    the container, not the operator's shell, so `docker compose exec` would expand
    them to empty strings on the host and the pre-deploy gate would fail — or
    worse, connect somewhere stale. Read the container's own environment instead,
    and keep the flags as overrides.
    """

    def test_reads_the_backend_container_environment(self):
        uri, database = _resolve_connection(
            None,
            None,
            {"MONGODB_URI": "mongodb://in-container", "DATABASE_NAME": "auto_author"},
        )
        assert (uri, database) == ("mongodb://in-container", "auto_author")

    def test_falls_back_to_database_url(self):
        # The frontend container gets the same connection string under
        # DATABASE_URL; the backend's own settings prefer MONGODB_URI over it, so
        # accept either and in that order.
        uri, _ = _resolve_connection(
            None, "db", {"DATABASE_URL": "mongodb://from-database-url"}
        )
        assert uri == "mongodb://from-database-url"

    def test_mongodb_uri_wins_over_database_url(self):
        uri, _ = _resolve_connection(
            None,
            "db",
            {"MONGODB_URI": "mongodb://wins", "DATABASE_URL": "mongodb://loses"},
        )
        assert uri == "mongodb://wins"

    def test_explicit_flags_override_the_environment(self):
        uri, database = _resolve_connection(
            "mongodb://explicit",
            "explicit_db",
            {"MONGODB_URI": "mongodb://env", "DATABASE_NAME": "env_db"},
        )
        assert (uri, database) == ("mongodb://explicit", "explicit_db")

    def test_says_which_variable_is_missing_rather_than_connecting_to_nothing(self):
        # An empty string is what host-side expansion of an unset variable
        # produces, and it is the failure this whole class exists to prevent.
        with pytest.raises(AccountIssuerBackfillError, match="MONGODB_URI"):
            _resolve_connection("", "db", {})
        with pytest.raises(AccountIssuerBackfillError, match="DATABASE_NAME"):
            _resolve_connection("mongodb://x", None, {})


class TestAtlasConnection:
    """Connect the way the app already connects.

    The whole point of this script is to repair the staging/production Atlas
    cluster, and it had only ever been exercised against a local
    `mongodb://127.0.0.1` — where the TLS branch never runs, so neither the demo
    nor CI (whose MongoDB fixture is also local) would notice a difference.
    `app/db/base.py:14-33` already establishes what works against this cluster;
    match it rather than hand a one-shot P0 migration a connection nothing has
    tried.
    """

    def test_atlas_uris_get_explicit_tls_with_a_ca_bundle(self):
        # `.invalid` (RFC 2606), not a `*.mongodb.net` placeholder: the #544 guard
        # rejects any managed-cluster hostname in a tracked file of a public repo,
        # and rightly does not care that this one is made up. Only the scheme
        # prefix matters here — nothing connects.
        kwargs = _client_kwargs("mongodb+srv://cluster.invalid/")
        assert kwargs["tls"] is True
        assert kwargs["tlsAllowInvalidCertificates"] is False
        assert kwargs["tlsCAFile"].endswith(".pem")

    def test_plain_uris_get_no_tls_options(self):
        # A local mongodb:// has no certificate to verify, and forcing tls on
        # would break the very fixture these tests run against.
        assert _client_kwargs("mongodb://127.0.0.1:27017") == {}
