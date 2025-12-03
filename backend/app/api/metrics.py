"""
Metrics endpoint for monitoring and observability.

Provides application metrics in a format compatible with monitoring systems.
Tracks request counts, durations, errors, and database operations.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@dataclass
class MetricsStore:
    """Thread-safe metrics storage."""

    # Request metrics
    request_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    request_durations: Dict[str, deque] = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=1000)))
    error_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Database metrics
    db_query_count: int = 0
    db_query_durations: deque = field(default_factory=lambda: deque(maxlen=1000))
    db_slow_query_count: int = 0

    # Session metrics
    active_sessions: int = 0
    session_creates: int = 0
    session_expires: int = 0

    # Lock for thread safety
    _lock: Lock = field(default_factory=Lock)

    def record_request(self, endpoint: str, duration_ms: float, status_code: int):
        """Record a request with its duration and status code."""
        with self._lock:
            self.request_count[endpoint] += 1
            self.request_durations[endpoint].append(duration_ms)
            if status_code >= 400:
                self.error_count[endpoint] += 1

    def record_db_query(self, duration_ms: float):
        """Record a database query with its duration."""
        with self._lock:
            self.db_query_count += 1
            self.db_query_durations.append(duration_ms)
            if duration_ms > 500:  # Slow query threshold
                self.db_slow_query_count += 1

    def record_session_create(self):
        """Record a session creation."""
        with self._lock:
            self.session_creates += 1
            self.active_sessions += 1

    def record_session_expire(self):
        """Record a session expiration."""
        with self._lock:
            self.session_expires += 1
            self.active_sessions = max(0, self.active_sessions - 1)

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics in a thread-safe manner."""
        with self._lock:
            # Calculate request metrics
            request_metrics = {}
            for endpoint, count in self.request_count.items():
                durations = list(self.request_durations[endpoint])
                errors = self.error_count.get(endpoint, 0)

                if durations:
                    durations_sorted = sorted(durations)
                    p50_idx = len(durations_sorted) // 2
                    p95_idx = int(len(durations_sorted) * 0.95)
                    p99_idx = int(len(durations_sorted) * 0.99)

                    request_metrics[endpoint] = {
                        "count": count,
                        "error_count": errors,
                        "error_rate": round(errors / count * 100, 2) if count > 0 else 0,
                        "duration_ms": {
                            "min": round(min(durations), 2),
                            "max": round(max(durations), 2),
                            "mean": round(sum(durations) / len(durations), 2),
                            "p50": round(durations_sorted[p50_idx], 2),
                            "p95": round(durations_sorted[p95_idx], 2),
                            "p99": round(durations_sorted[p99_idx], 2),
                        },
                    }
                else:
                    request_metrics[endpoint] = {
                        "count": count,
                        "error_count": errors,
                        "error_rate": round(errors / count * 100, 2) if count > 0 else 0,
                        "duration_ms": None,
                    }

            # Calculate database metrics
            db_durations = list(self.db_query_durations)
            db_metrics = {
                "query_count": self.db_query_count,
                "slow_query_count": self.db_slow_query_count,
            }

            if db_durations:
                db_durations_sorted = sorted(db_durations)
                p50_idx = len(db_durations_sorted) // 2
                p95_idx = int(len(db_durations_sorted) * 0.95)
                p99_idx = int(len(db_durations_sorted) * 0.99)

                db_metrics["duration_ms"] = {
                    "min": round(min(db_durations), 2),
                    "max": round(max(db_durations), 2),
                    "mean": round(sum(db_durations) / len(db_durations), 2),
                    "p50": round(db_durations_sorted[p50_idx], 2),
                    "p95": round(db_durations_sorted[p95_idx], 2),
                    "p99": round(db_durations_sorted[p99_idx], 2),
                }

            # Session metrics
            session_metrics = {
                "active_sessions": self.active_sessions,
                "total_creates": self.session_creates,
                "total_expires": self.session_expires,
            }

            return {
                "requests": request_metrics,
                "database": db_metrics,
                "sessions": session_metrics,
            }

    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self.request_count.clear()
            self.request_durations.clear()
            self.error_count.clear()
            self.db_query_count = 0
            self.db_query_durations.clear()
            self.db_slow_query_count = 0
            # Don't reset active_sessions as it's a gauge, not a counter


# Global metrics store
_metrics_store = MetricsStore()


def get_metrics_store() -> MetricsStore:
    """Get the global metrics store."""
    return _metrics_store


@router.get("")
async def get_metrics(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get application metrics.

    Returns metrics about:
    - Request counts, durations (p50, p95, p99), and error rates by endpoint
    - Database query counts, durations, and slow query counts
    - Active session counts

    Requires authentication for security.

    Returns:
        200 OK with metrics data
        401 Unauthorized if not authenticated
    """
    if not current_user:
        logger.warning("Unauthenticated request to /metrics")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for metrics",
        )

    metrics = _metrics_store.get_metrics()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }


@router.get("/prometheus")
async def get_prometheus_metrics(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> str:
    """
    Get metrics in Prometheus text format.

    Returns metrics in Prometheus exposition format for scraping.
    Requires authentication for security.

    Returns:
        200 OK with Prometheus-formatted metrics
        401 Unauthorized if not authenticated
    """
    if not current_user:
        logger.warning("Unauthenticated request to /metrics/prometheus")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for metrics",
        )

    metrics = _metrics_store.get_metrics()
    lines = []

    # Request metrics
    lines.append("# HELP http_requests_total Total HTTP requests by endpoint")
    lines.append("# TYPE http_requests_total counter")
    for endpoint, data in metrics["requests"].items():
        safe_endpoint = endpoint.replace("/", "_").replace("{", "").replace("}", "")
        lines.append(f'http_requests_total{{endpoint="{safe_endpoint}"}} {data["count"]}')

    lines.append("")
    lines.append("# HELP http_request_errors_total Total HTTP request errors by endpoint")
    lines.append("# TYPE http_request_errors_total counter")
    for endpoint, data in metrics["requests"].items():
        safe_endpoint = endpoint.replace("/", "_").replace("{", "").replace("}", "")
        lines.append(f'http_request_errors_total{{endpoint="{safe_endpoint}"}} {data["error_count"]}')

    lines.append("")
    lines.append("# HELP http_request_duration_ms HTTP request duration in milliseconds")
    lines.append("# TYPE http_request_duration_ms summary")
    for endpoint, data in metrics["requests"].items():
        if data["duration_ms"]:
            safe_endpoint = endpoint.replace("/", "_").replace("{", "").replace("}", "")
            lines.append(f'http_request_duration_ms{{endpoint="{safe_endpoint}",quantile="0.5"}} {data["duration_ms"]["p50"]}')
            lines.append(f'http_request_duration_ms{{endpoint="{safe_endpoint}",quantile="0.95"}} {data["duration_ms"]["p95"]}')
            lines.append(f'http_request_duration_ms{{endpoint="{safe_endpoint}",quantile="0.99"}} {data["duration_ms"]["p99"]}')

    # Database metrics
    lines.append("")
    lines.append("# HELP db_queries_total Total database queries")
    lines.append("# TYPE db_queries_total counter")
    lines.append(f'db_queries_total {metrics["database"]["query_count"]}')

    lines.append("")
    lines.append("# HELP db_slow_queries_total Total slow database queries (>500ms)")
    lines.append("# TYPE db_slow_queries_total counter")
    lines.append(f'db_slow_queries_total {metrics["database"]["slow_query_count"]}')

    if "duration_ms" in metrics["database"]:
        lines.append("")
        lines.append("# HELP db_query_duration_ms Database query duration in milliseconds")
        lines.append("# TYPE db_query_duration_ms summary")
        lines.append(f'db_query_duration_ms{{quantile="0.5"}} {metrics["database"]["duration_ms"]["p50"]}')
        lines.append(f'db_query_duration_ms{{quantile="0.95"}} {metrics["database"]["duration_ms"]["p95"]}')
        lines.append(f'db_query_duration_ms{{quantile="0.99"}} {metrics["database"]["duration_ms"]["p99"]}')

    # Session metrics
    lines.append("")
    lines.append("# HELP sessions_active Current active sessions")
    lines.append("# TYPE sessions_active gauge")
    lines.append(f'sessions_active {metrics["sessions"]["active_sessions"]}')

    lines.append("")
    lines.append("# HELP sessions_created_total Total sessions created")
    lines.append("# TYPE sessions_created_total counter")
    lines.append(f'sessions_created_total {metrics["sessions"]["total_creates"]}')

    lines.append("")
    lines.append("# HELP sessions_expired_total Total sessions expired")
    lines.append("# TYPE sessions_expired_total counter")
    lines.append(f'sessions_expired_total {metrics["sessions"]["total_expires"]}')

    return "\n".join(lines)


@router.post("/reset")
async def reset_metrics(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Reset all metrics.

    Useful for testing or clearing metrics after an incident.
    Requires authentication for security.

    Returns:
        200 OK if metrics were reset
        401 Unauthorized if not authenticated
    """
    if not current_user:
        logger.warning("Unauthenticated request to /metrics/reset")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to reset metrics",
        )

    _metrics_store.reset_metrics()
    logger.info("Metrics reset by user")

    return {
        "status": "success",
        "message": "Metrics have been reset",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
