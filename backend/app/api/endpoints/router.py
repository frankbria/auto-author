from fastapi import APIRouter
from app.api.endpoints import users, webhooks, books

# Main router
router = APIRouter()

# Include sub-routers
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
router.include_router(books.router, prefix="/books", tags=["books"])


@router.get("/")
async def read_root():
    return {"message": "Welcome to the Auto Author API!"}


@router.get("/health")
async def health_check():
    return {"status": "healthy"}
