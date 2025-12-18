from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Clerk webhooks are deprecated - users are now created automatically on better-auth signup
# This module is kept for reference but all webhook functionality has been removed

@router.post("/better-auth", status_code=200)
async def better_auth_webhook():
    """
    Better-auth webhook handler.

    Note: better-auth typically handles user creation/updates automatically,
    so explicit webhook handlers may not be necessary. This endpoint is a placeholder
    for future webhook implementations if needed.
    """
    logger.info("better-auth webhook received (no-op)")
    return {"message": "better-auth webhook processed"}
