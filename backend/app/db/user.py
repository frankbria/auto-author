# backend/app/db/user.py
"""The users collection: one document per person (#1263).

better-auth creates the document at sign-up and owns its login fields (email,
name, emailVerified, createdAt, updatedAt, the #789 terms fields); the backend
keeps its profile, plan and billing fields on the same document. The document's
``_id`` is the user id. The app passes it around as the string ``auth_id``,
which is not stored: ``as_app_user`` derives it on every read.
"""

import logging
import re

from .base import users_collection, get_collection
from bson.objectid import ObjectId
from pymongo import ReturnDocument
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from .audit_log import audit_after_write
from .usage import delete_usage
from app.core.reporting import report_failure

logger = logging.getLogger(__name__)

# How long a deleted account's record is kept for complaints and chargebacks
# before it is erased (#954): 18 months.
RETENTION = timedelta(days=548)

# The account and billing record a deleted account keeps. An allowlist, so a
# field added to users later is erased by default.
RETAINED_FIELDS = (
    "email", "first_name", "last_name", "display_name", "created_at",
    "plan", "stripe_customer_id", "cancelled_subscription",
    # Owner decision 2026-10-11 (#960): answers "I never agreed to the Terms".
    "terms_version", "terms_accepted_at",
)

# better-auth's names for the fields the app reads under its own.
_BETTER_AUTH_NAMES = {
    "createdAt": "created_at",
    "updatedAt": "updated_at",
    "termsVersion": "terms_version",
    "termsAcceptedAt": "terms_accepted_at",
}


def user_key(auth_id: str) -> Dict:
    """The users filter for ``auth_id``. better-auth's MongoDB adapter keys a
    user by an ObjectId; an id that is not one is looked for as it is."""
    return {"_id": ObjectId(auth_id) if ObjectId.is_valid(auth_id) else auth_id}


def as_app_user(doc: Optional[Dict]) -> Optional[Dict]:
    """A users document as the app reads it: with ``auth_id``, the app's names
    for better-auth's fields, and the defaults a document better-auth created
    has not been given yet."""
    if doc is None:
        return None
    user = {"role": "user", "plan": "free", "is_active": True, "metadata": {}, **doc}
    user["auth_id"] = str(doc["_id"])
    for theirs, ours in _BETTER_AUTH_NAMES.items():
        if theirs in doc:
            user[ours] = doc[theirs]
    if "first_name" not in user and (doc.get("name") or doc.get("email")):
        # "Ada Lovelace" -> Ada / Lovelace; no name -> the email's local part.
        first, _, last = (doc.get("name") or doc["email"].split("@")[0]).partition(" ")
        user["first_name"] = first
        user.setdefault("last_name", last)
    return user


async def ensure_user_indexes() -> None:
    """Create the users collection's indexes, and the deleted_users one.

    Idempotent (MongoDB skips existing indexes). Per-index try/except so a
    startup can't be bricked by one index.
    """
    try:
        # auth_id is no longer stored (#1263): a unique index on it makes every
        # sign-up after the first collide on null.
        if "auth_id_unique_idx" in await users_collection.index_information():
            await users_collection.drop_index("auth_id_unique_idx")
    except Exception:
        logger.error("Failed to drop the users.auth_id index", exc_info=True)

    try:
        # sparse: a document without an email doesn't collide on null.
        await users_collection.create_index(
            "email", name="email_unique_idx", unique=True, sparse=True
        )
    except Exception:
        logger.error("Failed to create unique index on users.email", exc_info=True)

    try:
        # Stripe webhook lookups (issue #220); sparse — most users have no
        # Stripe customer, unique — one Stripe customer maps to one user.
        await users_collection.create_index(
            "stripe_customer_id",
            name="stripe_customer_id_unique_idx",
            unique=True,
            sparse=True,
        )
    except Exception:
        logger.error(
            "Failed to create unique index on users.stripe_customer_id", exc_info=True
        )

    try:
        # One kept record per deleted account.
        await (await get_collection("deleted_users")).create_index(
            "auth_id", name="auth_id_unique_idx", unique=True
        )
    except Exception:
        logger.error("Failed to create unique index on deleted_users.auth_id", exc_info=True)

    try:
        # Every signed-in request, here and in the frontend, finds its session
        # by token, and better-auth's adapter creates no index: it was a scan
        # of every session (#826). The default name, so that an index someone
        # has already made by hand on a deployed database is this one.
        await (await get_collection("session")).create_index("token")
    except Exception:
        logger.error("Failed to create index on session.token", exc_info=True)

    await _ensure_better_auth_indexes()


async def _ensure_better_auth_indexes() -> None:
    """The filters better-auth's own lookups use (#1034), as a profiled sign-up,
    sign-in, password reset and session list issued them. Its adapter makes no
    index, so each was a collection scan. Default names, like session.token.
    """
    for name, field in (
        ("account", "userId"),  # sign-in, password reset
        ("session", "userId"),  # session list, revoke, account deletion
        ("verification", "identifier"),  # email/reset links, trust-device sweep (prefix regex)
    ):
        try:
            await (await get_collection(name)).create_index(field)
        except Exception:
            logger.error("Failed to create index on %s.%s", name, field, exc_info=True)


# User-related database operations
async def get_user_by_auth_id(auth_id: str) -> Optional[Dict]:
    """Get a user by their id, without ``book_ids``.

    That list grows with every book the user creates, and nothing reads it
    from here (#826).
    """
    return as_app_user(await users_collection.find_one(user_key(auth_id), {"book_ids": 0}))


async def get_user_by_email(email: str) -> Optional[Dict]:
    """Get a user by their email address"""
    return as_app_user(await users_collection.find_one({"email": email}))


async def get_user_by_stripe_customer_id(stripe_customer_id: str) -> Optional[Dict]:
    """Get a user by their Stripe customer id (issue #220)."""
    return as_app_user(
        await users_collection.find_one({"stripe_customer_id": stripe_customer_id})
    )


async def update_user(
    auth_id: str, user_data: Dict, actor_id: str = None,
    extra_filter: Optional[Dict] = None, return_document=True,
) -> Optional[Dict]:
    """Update an existing user. ``return_document`` is pymongo's: pass
    ``ReturnDocument.BEFORE`` for the document the update replaced.

    ``extra_filter`` is merged into the query so a caller can make the write
    conditional on server-side state — the condition is then evaluated by Mongo
    as part of the same atomic operation instead of by the caller beforehand.
    Returns None when the filter does not match, which a caller must treat as
    "someone else got there first" rather than "user not found" (#352).
    """
    # The timestamp is better-auth's field; the app reads it as updated_at.
    user_data.pop("updated_at", None)
    user_data["updatedAt"] = datetime.now(timezone.utc)

    # Preferences are set key by key (#848): written whole, a partial object
    # dropped the keys it left out, and null wiped them all.
    preferences = user_data.pop("preferences", None) or {}
    user_data.update({f"preferences.{key}": value for key, value in preferences.items()})
    if preferences:
        # A null stored before #848 has no key to set into, so Mongo refuses the write.
        await users_collection.update_one(
            {**user_key(auth_id), "preferences": {"$type": "null"}}, {"$set": {"preferences": {}}}
        )

    # A deleted account never matches, so a late Stripe event or an admin
    # edit can't write personal data back onto it.
    query: Dict = {**user_key(auth_id), "deleted_at": {"$exists": False}}
    if extra_filter:
        query.update(extra_filter)

    # Update the user
    updated_user = await users_collection.find_one_and_update(
        query, {"$set": user_data}, return_document=return_document
    )

    # Log the change if user was found and updated
    if updated_user and actor_id:
        await audit_after_write(
            action="user_update",
            actor_id=actor_id,
            target_id=auth_id,
            resource_type="user",
            details={"updated_fields": list(user_data.keys())},
        )

    return as_app_user(updated_user)


async def swap_checkout_session(auth_id: str, session_id: str) -> Optional[str]:
    """Store the user's newest Stripe Checkout session and return the one it
    replaces (#912). One atomic write, so two tabs at once each see the other's."""
    before = await users_collection.find_one_and_update(
        user_key(auth_id),
        {"$set": {"stripe_checkout_session_id": session_id}},
        projection={"stripe_checkout_session_id": 1},
        return_document=ReturnDocument.BEFORE,
    )
    return (before or {}).get("stripe_checkout_session_id")


async def grandfather_unverified_accounts() -> int:
    """Mark better-auth users that predate the email-verification requirement
    (#792) as verified. They never had a way to verify, so requiring it would
    lock every one of them out at the next sign-in.

    "Predate" means created before this backend first started with the
    requirement. That moment is written once to ``app_meta`` and reused, so a
    later restart never verifies an account created under the requirement.
    Idempotent, and safe from two workers at once.
    """
    marker = await (await get_collection("app_meta")).find_one_and_update(
        {"_id": "email_verification_required_from"},
        {"$setOnInsert": {"at": datetime.now(timezone.utc)}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    result = await users_collection.update_many(
        {"emailVerified": {"$ne": True}, "createdAt": {"$lt": marker["at"]}},
        {"$set": {"emailVerified": True}},
    )
    return result.modified_count


async def delete_better_auth_identity(auth_id: str) -> int:
    """Remove everything that authenticates as the user, then the user:
    sessions (every device), credential/OAuth accounts (the old password), the
    twoFactor secret (#763), verification rows (#957) and the users document.

    better-auth's MongoDB adapter stores ``_id`` and ``userId`` as ObjectIds;
    the string form is matched too so a legacy string-keyed row can't survive.
    Returns how many documents it removed.
    """
    ids: List = [auth_id]
    if ObjectId.is_valid(auth_id):
        ids.append(ObjectId(auth_id))
    removed = 0
    for name in ("session", "account", "twoFactor"):
        collection = await get_collection(name)
        removed += (await collection.delete_many({"userId": {"$in": ids}})).deleted_count
    # Verification rows (#957), in the shapes better-auth 1.7 writes: the user
    # id is the value of trust-device, pending 2FA sign-in, password-reset and
    # delete-account rows; a pending sign-in's attempts and OTP are keyed by
    # that row's identifier, a signed-in OTP by "<user id>!<session id>".
    verification = await get_collection("verification")
    pending = [
        row["identifier"]
        async for row in verification.find({"value": {"$in": ids}}, {"identifier": 1})
    ]
    removed += (await verification.delete_many({"$or": [
        {"value": {"$in": ids}},
        {"identifier": {"$in": [f"2fa-{kind}-{p}" for p in pending for kind in ("attempts", "otp")]}},
        {"identifier": {"$regex": f"^2fa-otp-{re.escape(auth_id)}!"}},
    ]})).deleted_count
    result = await users_collection.delete_many({"_id": {"$in": ids}})
    return removed + result.deleted_count


async def _finish_deletion(doc: Dict) -> None:
    """Everything after a users document is marked deleted: the kept record,
    the books, avatar and usage counters, and the identity, the document last.
    Each step is safe to repeat."""
    user = as_app_user(doc)
    auth_id = user["auth_id"]

    # The account and billing record kept for 18 months (#954). Inserted once,
    # so finishing a deletion again keeps its dates.
    await (await get_collection("deleted_users")).update_one(
        {"auth_id": auth_id},
        {"$setOnInsert": {
            "deleted_at": doc["deleted_at"],
            "purge_at": doc["deleted_at"] + RETENTION,
            "retained": {f: user[f] for f in RETAINED_FIELDS if user.get(f) is not None},
        }},
        upsert=True,
    )

    # A book created after the caller's cascade read its id list is not in it
    # (#945); past the deletion create_book removes its own, so a second pass
    # here catches the rest. Empty, it costs one find.
    from app.db.book import delete_all_user_books

    await delete_all_user_books(auth_id)

    avatar_url = doc.get("avatar_url")
    if avatar_url:
        try:
            from app.services.file_upload_service import FileUploadService

            await FileUploadService().delete_profile_picture(auth_id, avatar_url)
        except Exception as error:
            # Reached only when the upload service cannot be set up at all: its
            # own delete never raises, and reports from where it catches.
            logger.error("Failed to delete avatar for user %s", auth_id, exc_info=True)
            report_failure("delete-files", error)

    await delete_usage(auth_id)  # usage counters are the account's too (#957)
    await delete_better_auth_identity(auth_id)


async def delete_user(auth_id: str, actor_id: str = None) -> bool:
    """Delete a user's account (#1263).

    The document is marked ``deleted_at`` first, so the session check refuses
    every device at once, then the kept record is written to deleted_users and
    everything else goes, the users document last. A crash in between leaves
    the mark, which ``erase_stranded_identities`` (or a second call here)
    finishes. Returns False when there is no such user.
    """
    now = datetime.now(timezone.utc)
    doc = await users_collection.find_one_and_update(
        user_key(auth_id),
        # An earlier deletion that stopped part way keeps its date.
        [{"$set": {"deleted_at": {"$ifNull": ["$deleted_at", now]}}}],
        projection={"book_ids": 0},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        return False
    await _finish_deletion(doc)

    await audit_after_write(
        action="user_delete",
        actor_id=actor_id or auth_id,  # If no actor specified, user deleted themselves
        target_id=auth_id,
        resource_type="user",
    )
    return True


# What an erased record keeps: the privacy page promises the account identifier
# and the date of deletion (#954).
_ERASED = {"_id": "$_id", "auth_id": "$auth_id", "deleted_at": "$deleted_at"}


async def erase_deactivated_user(auth_id: str, actor_id: str) -> bool:
    """Erase a deleted account's kept record before its purge date, for a user
    who asks support to (#954), down to _ERASED. False when there is no record
    left to erase."""
    result = await (await get_collection("deleted_users")).update_one(
        {"auth_id": auth_id, "purge_at": {"$exists": True}}, [{"$replaceWith": _ERASED}]
    )
    if not result.modified_count:
        return False
    await audit_after_write(
        action="user_erase",
        actor_id=actor_id,
        target_id=auth_id,
        resource_type="user",
    )
    return True


async def purge_expired_users() -> int:
    """Erase every deleted account's kept record whose purge date has passed
    (#954), down to _ERASED. Run daily by the housekeeping task."""
    result = await (await get_collection("deleted_users")).update_many(
        {"purge_at": {"$lte": datetime.now(timezone.utc)}}, [{"$replaceWith": _ERASED}]
    )
    return result.modified_count


async def erase_stranded_identities() -> int:
    """Finish deletions that stopped after the users document was marked
    (#935): a crash or failover there left the email, name and password hash,
    and the user cannot retry because the mark refuses their session.
    Idempotent; run by the housekeeping task, at start-up and then daily.
    """
    finished = 0
    async for doc in users_collection.find({"deleted_at": {"$exists": True}}, {"book_ids": 0}):
        await _finish_deletion(doc)
        finished += 1
    return finished
