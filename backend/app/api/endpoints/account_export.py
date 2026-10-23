"""Account data export (#790), streamed and downloaded with a token (#966).

The profile page POSTs for a token, so a refusal (rate limit, expired session)
comes back to the page as JSON it can show, then navigates to the GET with that
token and the browser streams the file to disk.
"""

import json
import logging
from datetime import datetime, timezone
from typing import AsyncIterator, Dict

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from app.api.dependencies import audit_request, get_rate_limiter
from app.core.security import get_current_user_from_session
from app.db.base import get_collection
from app.db.export_tokens import issue_export_token, redeem_export_token

router = APIRouter()

logger = logging.getLogger(__name__)

# The users-doc fields an account export carries (#790). An allowlist, so a
# field added to users later is not exported until someone decides it should be.
EXPORTED_PROFILE_FIELDS = (
    "email", "first_name", "last_name", "display_name", "bio", "avatar_url",
    "preferences", "plan", "stripe_subscription_status", "created_at",
    "updated_at", "terms_version", "terms_accepted_at",
)

# The collections an export reads, and the field in each that holds the
# owner's auth_id. Chapter content is embedded in the book document.
EXPORTED_COLLECTIONS = {
    "books": "owner_id",
    "questions": "user_id",
    "question_responses": "user_id",
    "question_ratings": "user_id",
}

# Documents per cursor round trip: what the export holds at once is this many
# books, whatever the library's size, at one round trip per batch.
EXPORT_BATCH_SIZE = 10


def _encode(value) -> bytes:
    """One value as JSONResponse would render it, so the streamed file is the
    same bytes the in-memory one was."""
    return json.dumps(
        jsonable_encoder(
            value,
            custom_encoder={
                ObjectId: str,
                # Mongo returns naive UTC; say so, so every date in the file reads the same.
                datetime: lambda d: d.replace(tzinfo=d.tzinfo or timezone.utc).isoformat(),
            },
        ),
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
    ).encode("utf-8")


async def stream_account_export(user: Dict) -> AsyncIterator[bytes]:
    """The export document, one Mongo document per chunk. Every query is scoped
    to ``user``'s own auth_id."""
    auth_id = user["auth_id"]
    profile = {f: user[f] for f in EXPORTED_PROFILE_FIELDS if f in user}
    yield (
        b'{"exported_at":' + _encode(datetime.now(timezone.utc))
        + b',"profile":' + _encode(profile)
    )
    for name, owner_field in EXPORTED_COLLECTIONS.items():
        yield b"," + _encode(name) + b":["
        collection = await get_collection(name)
        # collaborators would name other accounts; no document here has another use for the key.
        cursor = collection.find(
            {owner_field: auth_id}, {"collaborators": 0}
        ).batch_size(EXPORT_BATCH_SIZE)
        separator = b""
        async for doc in cursor:
            yield separator + _encode(doc)
            separator = b","
        yield b"]"
    yield b"}"


@router.post("/me/export/token")
async def issue_account_export_token(
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=10, window=3600)),
):
    """A single-use token for GET /me/export, valid for a minute, for this account only."""
    return {"token": await issue_export_token(current_user["auth_id"])}


@router.get("/me/export")
async def export_my_data(
    request: Request,
    token: str = Query(..., max_length=128),
    current_user: Dict = Depends(get_current_user_from_session),
):
    """Download the caller's profile, books, questions, answers and ratings (#790).

    Needs a token from POST /me/export/token and the session it was issued to.
    Takes no id. Activity logs, uploaded files and anything better-auth or
    Stripe holds are not read.
    """
    owner = await redeem_export_token(token)
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This download link has expired. Start the download again from your profile.",
        )
    if owner != current_user["auth_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This download link belongs to another account.",
        )
    # Before any data leaves: an export that cannot be recorded does not start.
    await audit_request(
        request=request,
        current_user=current_user,
        action="account_export",
        resource_type="user",
        target_id=current_user["auth_id"],
    )
    return StreamingResponse(
        stream_account_export(current_user),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="auto-author-data.json"',
            "Cache-Control": "no-store",
        },
    )
