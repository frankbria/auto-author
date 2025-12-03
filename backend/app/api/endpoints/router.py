from fastapi import APIRouter
from app.api.endpoints import users, webhooks, export, sessions, transcription
from app.api.endpoints.books import router as books_router
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router

# Main router
router = APIRouter()

# Include sub-routers
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
router.include_router(books_router, prefix="/books", tags=["books"])
router.include_router(export.router, tags=["export"])
router.include_router(sessions.router, tags=["sessions"])
router.include_router(transcription.router, prefix="/transcribe", tags=["transcription"])
router.include_router(metrics_router, tags=["metrics"])


@router.get("/")
async def read_root():
    return {"message": "Welcome to the Auto Author API!"}
