from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from contextlib import asynccontextmanager
from app.api.endpoints.router import router as api_router
from app.core.config import settings
import logging
import os
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def validate_production_security() -> None:
    """Validate critical security settings before application startup.

    This function provides fail-fast behavior for security-critical
    configuration errors that could expose user data.

    Raises:
        RuntimeError: If BYPASS_AUTH is enabled in production environment
    """
    node_env = os.getenv("NODE_ENV")

    if node_env == "production":
        if settings.BYPASS_AUTH:
            logger.critical(
                "FATAL SECURITY ERROR: BYPASS_AUTH is enabled in production. "
                "Application startup blocked to prevent unauthorized access."
            )
            raise RuntimeError(
                "Application startup blocked: BYPASS_AUTH is enabled in production environment. "
                "This would allow unauthorized access to all user data. "
                "Remove BYPASS_AUTH=true from your production configuration."
            )
        logger.info("Production security validation passed: BYPASS_AUTH is disabled")
    elif settings.BYPASS_AUTH:
        logger.warning(
            f"BYPASS_AUTH is enabled in {node_env or 'unset'} environment. "
            "Authentication will be bypassed - DO NOT use in production."
        )


# Validate security settings before creating the app
validate_production_security()


# Lifespan context manager for startup and shutdown tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events (startup and shutdown)."""
    # Startup tasks
    logger.info("Running startup tasks...")

    # Import here to avoid circular dependencies
    from app.db.questions import ensure_question_indexes

    # Create indexes for question collections
    await ensure_question_indexes()

    logger.info("Startup tasks completed")

    # Application runs here
    yield

    # Shutdown tasks (if needed)
    logger.info("Application shutdown")


# Create FastAPI app with lifespan handler
app = FastAPI(
    title="Auto Author API",
    description="API for the Auto Author application",
    version="0.1.0",
    lifespan=lifespan,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom request validation middleware
from app.api.request_validation import RequestValidationMiddleware
from app.api.middleware.session_middleware import add_session_middleware

app.add_middleware(RequestValidationMiddleware)

# Add session tracking middleware
add_session_middleware(app)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Mount static files for local uploads (only if not using cloud storage)
# This allows serving uploaded images when using local storage
uploads_path = Path("uploads")
if uploads_path.exists() and not any([
    os.getenv('CLOUDINARY_CLOUD_NAME'),
    os.getenv('AWS_S3_BUCKET')
]):
    logger.info("Mounting local uploads directory for static file serving")
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Enhanced validation error handler with more detailed error information"""
    errors = []
    for error in exc.errors():
        error_loc = " -> ".join([str(loc) for loc in error["loc"]])
        error_msg = f"{error_loc}: {error['msg']}"
        errors.append(error_msg)

    error_details = "; ".join(errors)
    logger.error(f"Validation error: {error_details}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": f"Validation error",
            "errors": exc.errors(),
            "error_summary": error_details,
        },
    )


# Pydantic validation error handler
@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    logger.error(f"Pydantic validation error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": f"Validation error: {str(exc.errors())}"},
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"An unexpected error occurred: {str(exc)}",
            "type": str(type(exc).__name__),
        },
    )


@app.get("/")
def read_root():
    return JSONResponse(
        content={"message": "Welcome to the Auto Author API!"},
        status_code=status.HTTP_200_OK,
    )
