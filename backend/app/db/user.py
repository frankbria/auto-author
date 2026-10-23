# backend/app/db/user.py

import logging

from .base import users_collection, get_collection
from bson.objectid import ObjectId
from pymongo import ReturnDocument
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from .audit_log import audit_after_write
from app.core.reporting import report_failure

logger = logging.getLogger(__name__)

# How long a deactivated account's record is kept for complaints and
# chargebacks before it is erased (#954): 18 months.
RETENTION = timedelta(days=548)

# The account and billing record a deactivated account keeps. An allowlist, so
# a field added to users later is erased by default.
RETAINED_FIELDS = (
    "email", "first_name", "last_name", "display_name", "created_at",
    "plan", "stripe_customer_id", "cancelled_subscription",
    # Owner decision 2026-10-11 (#960): answers "I never agreed to the Terms".
    "terms_version", "terms_accepted_at",
)

# What an erased account is replaced with (#784), as a $replaceWith expression.
_TOMBSTONE = {"_id": "$_id", "auth_id": "$auth_id", "deleted_at": "$deleted_at"}


async def ensure_user_indexes() -> None:
    """Create the users collection's unique indexes (issue #178).

    Without a unique index on auth_id, the check-then-insert in the auth
    auto-create path lets parallel first-load requests each insert a doc for the
    same user. The index makes create_user's DuplicateKeyError guard effective.

    Idempotent (MongoDB skips existing indexes). Per-index try/except so a
    startup can't be bricked by one index.

    ponytail: if the collection ALREADY holds duplicate auth_id/email docs, the
    unique build fails here and is logged — an operator must dedupe first
    (one-time cleanup), the app keeps running with the race still open until then.
    """
    try:
        await users_collection.create_index(
            "auth_id", name="auth_id_unique_idx", unique=True
        )
    except Exception:
        logger.error("Failed to create unique index on users.auth_id", exc_info=True)

    try:
        # sparse: legacy/partial docs without an email don't all collide on null.
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
        # Every signed-in request, here and in the frontend, finds its session
        # by token, and better-auth's adapter creates no index: it was a scan
        # of every session (#826). The default name, so that an index someone
        # has already made by hand on a deployed database is this one.
        await (await get_collection("session")).create_index("token")
    except Exception:
        logger.error("Failed to create index on session.token", exc_info=True)


# User-related database operations
async def get_user_by_auth_id(auth_id: str) -> Optional[Dict]:
    """Get a user by their better-auth ID, without ``book_ids``.

    Every signed-in request reads this. That list grows with every book the
    user creates, and nothing reads it from here (#826).
    """
    user = await users_collection.find_one({"auth_id": auth_id}, {"book_ids": 0})
    return user


async def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get a user by their database ID"""
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    return user


async def get_user_by_email(email: str) -> Optional[Dict]:
    """Get a user by their email address"""
    user = await users_collection.find_one({"email": email})
    return user


async def get_user_by_stripe_customer_id(stripe_customer_id: str) -> Optional[Dict]:
    """Get a user by their Stripe customer id (issue #220)."""
    return await users_collection.find_one({"stripe_customer_id": stripe_customer_id})


async def create_user(user_data: Dict) -> Dict:
    """Insert a new user.

    Pure insert primitive: raises DuplicateKeyError when a unique index
    (auth_id/email, issue #178) rejects the insert. Callers apply their own
    policy — the auth auto-create path treats a duplicate auth_id as a
    concurrent-first-load race and re-fetches the winner. (The legacy
    unauthenticated POST /users/ endpoint was removed in issue #186.)
    """
    result = await users_collection.insert_one(user_data)
    return await get_user_by_id(str(result.inserted_id))


async def release_email(email: str, auth_id: str) -> int:
    """Unset ``email`` on every users doc except ``auth_id``'s (#765).

    better-auth keeps emails unique and owns their verification, so when
    ``auth_id``'s better-auth user holds ``email``, any other backend doc holding
    it is stale (squatted through the old PATCH /users/me, or left over from a
    deleted account). Returns how many docs were released.
    """
    result = await users_collection.update_many(
        {"email": email, "auth_id": {"$ne": auth_id}}, {"$unset": {"email": ""}}
    )
    return result.modified_count


async def update_user(
    auth_id: str, user_data: Dict, actor_id: str = None,
    extra_filter: Optional[Dict] = None,
) -> Optional[Dict]:
    """Update an existing user.

    ``extra_filter`` is merged into the query so a caller can make the write
    conditional on server-side state — the condition is then evaluated by Mongo
    as part of the same atomic operation instead of by the caller beforehand.
    Returns None when the filter does not match, which a caller must treat as
    "someone else got there first" rather than "user not found" (#352).
    """
    # Add updated_at timestamp
    user_data["updated_at"] = datetime.now(timezone.utc)

    # Preferences are set key by key (#848): written whole, a partial object
    # dropped the keys it left out, and null wiped them all.
    preferences = user_data.pop("preferences", None) or {}
    user_data.update({f"preferences.{key}": value for key, value in preferences.items()})
    if preferences:
        # A null stored before #848 has no key to set into, so Mongo refuses the write.
        await users_collection.update_one(
            {"auth_id": auth_id, "preferences": {"$type": "null"}}, {"$set": {"preferences": {}}}
        )

    # A tombstone (deleted account, #784) never matches, so a late Stripe event
    # or an admin edit can't write personal data back onto it.
    query: Dict = {"auth_id": auth_id, "deleted_at": {"$exists": False}}
    if extra_filter:
        query.update(extra_filter)

    # Update the user
    updated_user = await users_collection.find_one_and_update(
        query, {"$set": user_data}, return_document=True
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

    return updated_user


async def swap_checkout_session(auth_id: str, session_id: str) -> Optional[str]:
    """Store the user's newest Stripe Checkout session and return the one it
    replaces (#912). One atomic write, so two tabs at once each see the other's."""
    before = await users_collection.find_one_and_update(
        {"auth_id": auth_id},
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
    result = await (await get_collection("user")).update_many(
        {"emailVerified": {"$ne": True}, "createdAt": {"$lt": marker["at"]}},
        {"$set": {"emailVerified": True}},
    )
    return result.modified_count


async def delete_better_auth_identity(auth_id: str) -> int:
    """Remove the better-auth user and everything that authenticates as it:
    sessions (every device), credential/OAuth accounts (the old password) and
    the twoFactor secret (#763).

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
    better_auth_users = await get_collection("user")
    result = await better_auth_users.delete_many({"$or": [{"_id": {"$in": ids}}, {"id": auth_id}]})
    return removed + result.deleted_count


async def delete_user(auth_id: str, actor_id: str = None) -> bool:
    """Deactivate a user and revoke their better-auth identity.

    Deactivating replaces the record with auth_id, deleted_at, purge_at and the
    RETAINED_FIELDS under ``retained`` (#954): replacing, not unsetting, erases
    every other field, including ones added later. deleted_at keeps the session
    resolver rejecting that id and stops the auto-create path, update_user and
    the Stripe webhook from reviving it. The retained email is nested, off the
    unique index, so the same address can sign up again (#763) without the new
    account colliding with this record or release_email stripping it.
    """
    now = datetime.now(timezone.utc)
    previous = await users_collection.find_one_and_update(
        {"auth_id": auth_id, "deleted_at": {"$exists": False}},
        [
            {
                "$replaceWith": {
                    "_id": "$_id",
                    "auth_id": "$auth_id",
                    "deleted_at": now,
                    "purge_at": now + RETENTION,
                    # A field the record lacks, or holds as null (an
                    # account with no Terms record), is left out.
                    "retained": {
                        field: {"$ifNull": [f"${field}", "$$REMOVE"]}
                        for field in RETAINED_FIELDS
                    },
                }
            }
        ],
    )
    success = previous is not None

    # A book created after the caller's cascade read its id list is not in it
    # (#945); past the tombstone create_book removes its own, so a second pass
    # here catches the rest. Empty, it costs one find.
    from app.db.book import delete_all_user_books

    await delete_all_user_books(auth_id)

    # The returned pre-image is the last place the avatar URL exists (#785).
    avatar_url = (previous or {}).get("avatar_url")
    if avatar_url:
        try:
            from app.services.file_upload_service import FileUploadService

            await FileUploadService().delete_profile_picture(auth_id, avatar_url)
        except Exception as error:
            # Reached only when the upload service cannot be set up at all: its
            # own delete never raises, and reports from where it catches.
            logger.error("Failed to delete avatar for user %s", auth_id, exc_info=True)
            report_failure("delete-files", error)

    # Unconditional: a better-auth user who never reached the backend has no
    # app record, but their sessions and credentials must still go.
    removed = await delete_better_auth_identity(auth_id)
    if not success and removed:
        # An earlier deactivation whose identity removal failed (#956):
        # finishing it is this deletion, so an admin's repair is not taken as
        # a request to erase the retained record.
        success = bool(
            await users_collection.count_documents(
                {"auth_id": auth_id, "purge_at": {"$exists": True}}, limit=1
            )
        )

    # Log the deletion
    if success:
        await audit_after_write(
            action="user_delete",
            actor_id=actor_id
            or auth_id,  # If no actor specified, user deleted themselves
            target_id=auth_id,
            resource_type="user",
        )
        return True
    return False


async def erase_deactivated_user(auth_id: str, actor_id: str) -> bool:
    """Erase a deactivated account's retained record before its purge date, for
    a user who asks support to (#954). Matches nothing else: not an active
    account, and not an account that is already erased."""
    result = await users_collection.update_one(
        {"auth_id": auth_id, "purge_at": {"$exists": True}},
        [{"$replaceWith": _TOMBSTONE}],
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
    """Erase every deactivated account whose purge date has passed (#954).

    Not a TTL index: that would delete the document, and the tombstone is what
    stops a surviving session from re-creating the account.
    """
    result = await users_collection.update_many(
        {"purge_at": {"$lte": datetime.now(timezone.utc)}},
        [{"$replaceWith": _TOMBSTONE}],
    )
    return result.modified_count


async def erase_stranded_identities() -> int:
    """Finish deletions that stopped between the tombstone and the identity
    erasure (#935): a crash or failover there left the better-auth user and
    account (email, name, password hash), and the user cannot retry because the
    tombstone refuses their session. Idempotent; run by the housekeeping task,
    at start-up and then daily.

    shortcut: one lookup per tombstone on every run; keep a "fully erased" flag
    on the tombstone if the number of deleted accounts grows large.
    """
    ba_users = await get_collection("user")
    accounts = await get_collection("account")
    finished = 0
    async for doc in users_collection.find({"deleted_at": {"$exists": True}}, {"auth_id": 1}):
        auth_id = doc.get("auth_id")
        if not auth_id:
            continue
        ids: List = [auth_id] + ([ObjectId(auth_id)] if ObjectId.is_valid(auth_id) else [])
        left = await ba_users.find_one(
            {"$or": [{"_id": {"$in": ids}}, {"id": auth_id}]}, {"_id": 1}
        ) or await accounts.find_one({"userId": {"$in": ids}}, {"_id": 1})
        if left:
            await delete_better_auth_identity(auth_id)
            finished += 1
    return finished
