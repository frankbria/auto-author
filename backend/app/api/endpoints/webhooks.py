from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from typing import Dict, Any, Optional
import hmac
import hashlib
import json

from app.core.config import settings
from app.schemas.user import UserCreate
from app.db.database import get_user_by_clerk_id, create_user, update_user, delete_user

router = APIRouter()


async def verify_webhook_signature(
    request: Request,
    svix_id: str = Header(None),
    svix_timestamp: str = Header(None),
    svix_signature: str = Header(None),
):
    """Verify the webhook signature from Clerk"""
    # Debug logging - print all headers
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Webhook headers received: {dict(request.headers)}")
    logger.info(f"svix-id: {svix_id}, svix-timestamp: {svix_timestamp}, svix-signature: {svix_signature}")

    if not settings.CLERK_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    if not svix_id or not svix_timestamp or not svix_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required Svix headers",
        )

    # Get the raw body
    body = await request.body()
    payload = body.decode("utf-8")

    # Create the signature
    timestamp = svix_timestamp
    secret = settings.CLERK_WEBHOOK_SECRET

    # Get the signatures provided in the header
    signature_header = svix_signature
    signatures = signature_header.split(" ")

    # Create a new hmac with the secret and timestamp
    hmac_message = f"{svix_id}.{timestamp}.{payload}"
    h = hmac.new(secret.encode("utf-8"), hmac_message.encode("utf-8"), hashlib.sha256)
    expected_signature = h.hexdigest()

    # Compare the computed signature with the provided signatures
    for signature in signatures:
        if hmac.compare_digest(signature, expected_signature):
            return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
    )


@router.post("/clerk", status_code=status.HTTP_200_OK)
async def clerk_webhook(
    request: Request, verified: bool = Depends(verify_webhook_signature)
):
    """Handle webhook events from Clerk"""
    # Parse the event data
    body = await request.body()
    event_data = json.loads(body.decode("utf-8"))

    event_type = event_data.get("type")
    data = event_data.get("data", {})

    # Handle different event types
    if event_type == "user.created":
        # Create a new user in our database
        clerk_user = data

        # Extract relevant user data
        user_data = UserCreate(
            clerk_id=clerk_user["id"],
            email=clerk_user["email_addresses"][0]["email_address"],
            first_name=clerk_user.get("first_name"),
            last_name=clerk_user.get("last_name"),
            avatar_url=clerk_user.get("image_url"),
            metadata=clerk_user.get("metadata", {}),
        )

        # Check if user already exists (idempotency)
        existing_user = await get_user_by_clerk_id(user_data.clerk_id)
        if not existing_user:
            await create_user(user_data.model_dump())

    elif event_type == "user.updated":
        # Update an existing user in our database
        clerk_user = data
        clerk_id = clerk_user["id"]

        # Only update if user exists
        existing_user = await get_user_by_clerk_id(clerk_id)
        if existing_user:
            # Extract updated fields
            update_data = {
                "email": clerk_user["email_addresses"][0]["email_address"],
                "first_name": clerk_user.get("first_name"),
                "last_name": clerk_user.get("last_name"),
                "avatar_url": clerk_user.get("image_url"),
                "metadata": clerk_user.get("metadata", {}),
            }

            await update_user(clerk_id, update_data)

    elif event_type == "user.deleted":
        # Delete a user from our database
        clerk_id = data["id"]
        await delete_user(clerk_id)

    # Return a success response
    return {"message": f"Processed {event_type} event successfully"}
