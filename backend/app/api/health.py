"""
Health check endpoints for monitoring and observability.

Provides endpoints for basic health checks, readiness probes, liveness probes,
and detailed health information for production monitoring systems.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import psutil
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from app.db.base import _client, _db
from app.core.config import settings
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# Track application start time for uptime calculation
_app_start_time = time.time()


@router.get("")
async def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint.

    Returns:
        200 OK if the application is running

    Use this for:
        - Load balancer health checks
        - Simple uptime monitoring
        - Deployment verification
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check endpoint.

    Verifies that the application is ready to serve traffic by checking:
    - MongoDB connection
    - Database operations

    Returns:
        200 OK if all dependencies are ready
        503 Service Unavailable if any dependency is not ready

    Use this for:
        - Kubernetes readiness probes
        - Pre-traffic health checks
        - Deployment gates
    """
    checks = {}
    all_ready = True

    # Check MongoDB connection
    try:
        start_time = time.time()
        await _client.admin.command('ping')
        duration_ms = (time.time() - start_time) * 1000
        checks["mongodb"] = {
            "status": "ready",
            "response_time_ms": round(duration_ms, 2),
        }
        logger.debug(f"MongoDB readiness check passed in {duration_ms:.2f}ms")
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        all_ready = False
        checks["mongodb"] = {
            "status": "not_ready",
            "error": str(e),
        }
        logger.error(f"MongoDB readiness check failed: {e}")
    except Exception as e:
        all_ready = False
        checks["mongodb"] = {
            "status": "not_ready",
            "error": f"Unexpected error: {str(e)}",
        }
        logger.error(f"MongoDB readiness check failed with unexpected error: {e}", exc_info=True)

    # Check database operations
    try:
        start_time = time.time()
        # Simple query to verify database operations work
        await _db.command('dbStats')
        duration_ms = (time.time() - start_time) * 1000
        checks["database_operations"] = {
            "status": "ready",
            "response_time_ms": round(duration_ms, 2),
        }
        logger.debug(f"Database operations check passed in {duration_ms:.2f}ms")
    except Exception as e:
        all_ready = False
        checks["database_operations"] = {
            "status": "not_ready",
            "error": str(e),
        }
        logger.error(f"Database operations check failed: {e}")

    response = {
        "status": "ready" if all_ready else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }

    if not all_ready:
        logger.warning(f"Readiness check failed: {checks}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response,
        )

    return response


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint.

    Verifies that the application is alive and responsive.
    Does NOT check external dependencies (use /ready for that).

    Returns:
        200 OK if the application is responsive
        503 Service Unavailable if the application is deadlocked or unresponsive

    Use this for:
        - Kubernetes liveness probes
        - Deadlock detection
        - Container restart triggers
    """
    try:
        # Check if we can perform basic operations
        current_time = time.time()
        uptime_seconds = current_time - _app_start_time

        return {
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": round(uptime_seconds, 2),
        }
    except Exception as e:
        logger.error(f"Liveness check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_alive",
                "error": str(e),
            },
        )


@router.get("/detailed")
async def detailed_health_check(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Detailed health check endpoint with system metrics.

    Requires authentication. Returns comprehensive health information including:
    - MongoDB connection status and pool statistics
    - System resources (CPU, memory, disk)
    - Application uptime
    - Active connections

    Returns:
        200 OK with detailed health information
        401 Unauthorized if not authenticated
        503 Service Unavailable if critical checks fail

    Use this for:
        - Administrative monitoring dashboards
        - Detailed troubleshooting
        - Capacity planning
    """
    if not current_user:
        logger.warning("Unauthenticated request to /health/detailed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for detailed health information",
        )

    checks = {}
    warnings = []

    # MongoDB connection and pool statistics
    try:
        start_time = time.time()
        server_info = await _client.server_info()
        duration_ms = (time.time() - start_time) * 1000

        # Get pool statistics (if available)
        pool_stats = {}
        try:
            # Note: Pool stats may not be available in all MongoDB driver versions
            if hasattr(_client, '_topology'):
                topology = _client._topology
                if hasattr(topology, '_servers'):
                    for server_address, server in topology._servers.items():
                        if hasattr(server, '_pool'):
                            pool = server._pool
                            pool_stats[str(server_address)] = {
                                "max_pool_size": pool.opts.max_pool_size,
                                "min_pool_size": pool.opts.min_pool_size,
                            }
        except Exception as e:
            logger.debug(f"Could not retrieve pool statistics: {e}")

        checks["mongodb"] = {
            "status": "connected",
            "response_time_ms": round(duration_ms, 2),
            "version": server_info.get("version", "unknown"),
            "pool_config": {
                "max_pool_size": 50,
                "min_pool_size": 10,
            },
            "pool_stats": pool_stats if pool_stats else "unavailable",
        }

        # Warn if connection is slow
        if duration_ms > 100:
            warnings.append(f"MongoDB connection slow: {duration_ms:.2f}ms (>100ms threshold)")

    except Exception as e:
        checks["mongodb"] = {
            "status": "error",
            "error": str(e),
        }
        logger.error(f"MongoDB health check failed: {e}")

    # Database statistics
    try:
        db_stats = await _db.command('dbStats')
        checks["database"] = {
            "status": "operational",
            "name": settings.DATABASE_NAME,
            "collections": db_stats.get("collections", 0),
            "data_size_mb": round(db_stats.get("dataSize", 0) / (1024 * 1024), 2),
            "storage_size_mb": round(db_stats.get("storageSize", 0) / (1024 * 1024), 2),
        }
    except Exception as e:
        checks["database"] = {
            "status": "error",
            "error": str(e),
        }
        logger.error(f"Database statistics check failed: {e}")

    # System resources
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        checks["system_resources"] = {
            "cpu_percent": cpu_percent,
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_percent": disk.percent,
        }

        # Add warnings for resource constraints
        if memory.percent > 90:
            warnings.append(f"High memory usage: {memory.percent}%")
        if disk.percent > 90:
            warnings.append(f"Low disk space: {disk.percent}% used")
        if cpu_percent > 80:
            warnings.append(f"High CPU usage: {cpu_percent}%")

    except Exception as e:
        checks["system_resources"] = {
            "status": "error",
            "error": str(e),
        }
        logger.error(f"System resources check failed: {e}")

    # Application uptime
    uptime_seconds = time.time() - _app_start_time
    checks["application"] = {
        "status": "running",
        "uptime_seconds": round(uptime_seconds, 2),
        "uptime_human": _format_uptime(uptime_seconds),
        "start_time": datetime.fromtimestamp(_app_start_time, tz=timezone.utc).isoformat(),
    }

    # Determine overall health status
    overall_status = "healthy"
    if any(check.get("status") == "error" for check in checks.values() if isinstance(check, dict)):
        overall_status = "degraded"
    if warnings:
        overall_status = "healthy_with_warnings" if overall_status == "healthy" else "degraded_with_warnings"

    response = {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "warnings": warnings if warnings else None,
    }

    if overall_status.startswith("degraded"):
        logger.warning(f"Detailed health check shows degraded status: {checks}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response,
        )

    return response


def _format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)
