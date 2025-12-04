"""
Tests for metrics endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.api.metrics import MetricsStore, get_metrics_store


def test_get_metrics_authenticated(client: TestClient, auth_headers: dict):
    """Test metrics endpoint with authentication."""
    # Reset metrics first
    client.post("/api/v1/metrics/reset", headers=auth_headers)

    # Generate some traffic
    for _ in range(10):
        client.get("/health")

    # Get metrics
    response = client.get("/api/v1/metrics", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "metrics" in data
    assert "requests" in data["metrics"]
    assert "database" in data["metrics"]
    assert "sessions" in data["metrics"]


def test_get_metrics_unauthenticated(client: TestClient):
    """Test metrics endpoint without authentication."""
    response = client.get("/api/v1/metrics")

    assert response.status_code == 401
    data = response.json()
    assert "Missing authentication credentials" in data["detail"]


def test_get_prometheus_metrics_authenticated(client: TestClient, auth_headers: dict):
    """Test Prometheus metrics endpoint with authentication."""
    # Reset metrics first
    client.post("/api/v1/metrics/reset", headers=auth_headers)

    # Generate some traffic
    for _ in range(5):
        client.get("/health")

    # Get Prometheus metrics
    response = client.get("/api/v1/metrics/prometheus", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"

    content = response.text
    assert "# HELP http_requests_total" in content
    assert "# TYPE http_requests_total counter" in content
    assert "http_requests_total" in content


def test_get_prometheus_metrics_unauthenticated(client: TestClient):
    """Test Prometheus metrics endpoint without authentication."""
    response = client.get("/api/v1/metrics/prometheus")

    assert response.status_code == 401


def test_reset_metrics_authenticated(client: TestClient, auth_headers: dict):
    """Test metrics reset with authentication."""
    # Generate some traffic
    for _ in range(5):
        client.get("/health")

    # Reset metrics
    response = client.post("/api/v1/metrics/reset", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Metrics have been reset" in data["message"]

    # Verify metrics are cleared
    metrics_response = client.get("/api/v1/metrics", headers=auth_headers)
    metrics_data = metrics_response.json()
    # The /health endpoints from before reset should be cleared
    # (the reset and get metrics calls themselves will be tracked)
    assert "/health" not in metrics_data["metrics"]["requests"] or \
           metrics_data["metrics"]["requests"]["/health"]["count"] == 0


def test_reset_metrics_unauthenticated(client: TestClient):
    """Test metrics reset without authentication."""
    response = client.post("/api/v1/metrics/reset")

    assert response.status_code == 401


def test_metrics_store_record_request():
    """Test recording requests in metrics store."""
    store = MetricsStore()

    # Record some requests
    store.record_request("/api/v1/books", 150.5, 200)
    store.record_request("/api/v1/books", 200.3, 200)
    store.record_request("/api/v1/books", 100.1, 404)

    metrics = store.get_metrics()

    # Check request counts
    assert "/api/v1/books" in metrics["requests"]
    assert metrics["requests"]["/api/v1/books"]["count"] == 3
    assert metrics["requests"]["/api/v1/books"]["error_count"] == 1
    assert metrics["requests"]["/api/v1/books"]["error_rate"] == pytest.approx(33.33, 0.1)

    # Check duration metrics
    durations = metrics["requests"]["/api/v1/books"]["duration_ms"]
    assert durations["min"] == pytest.approx(100.1, 0.1)
    assert durations["max"] == pytest.approx(200.3, 0.1)
    assert durations["mean"] == pytest.approx(150.3, 0.1)


def test_metrics_store_record_db_query():
    """Test recording database queries in metrics store."""
    store = MetricsStore()

    # Record some queries
    store.record_db_query(50.5)  # Fast query
    store.record_db_query(200.3)  # Medium query
    store.record_db_query(600.1)  # Slow query (>500ms)

    metrics = store.get_metrics()

    # Check query counts
    assert metrics["database"]["query_count"] == 3
    assert metrics["database"]["slow_query_count"] == 1

    # Check duration metrics
    durations = metrics["database"]["duration_ms"]
    assert durations["min"] == pytest.approx(50.5, 0.1)
    assert durations["max"] == pytest.approx(600.1, 0.1)


def test_metrics_store_record_sessions():
    """Test recording session events in metrics store."""
    store = MetricsStore()

    # Record session events
    store.record_session_create()
    store.record_session_create()
    store.record_session_expire()

    metrics = store.get_metrics()

    # Check session metrics
    assert metrics["sessions"]["active_sessions"] == 1  # 2 created - 1 expired
    assert metrics["sessions"]["total_creates"] == 2
    assert metrics["sessions"]["total_expires"] == 1


def test_metrics_store_percentiles():
    """Test percentile calculations in metrics store."""
    store = MetricsStore()

    # Record requests with known durations
    durations = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    for duration in durations:
        store.record_request("/test", duration, 200)

    metrics = store.get_metrics()
    duration_metrics = metrics["requests"]["/test"]["duration_ms"]

    # Check percentiles (using linear interpolation)
    assert duration_metrics["p50"] == 55.0  # Median (50 + 0.5 * (60 - 50))
    assert duration_metrics["p95"] == 95.5  # 95th percentile (90 + 0.5 * (100 - 90))
    assert duration_metrics["p99"] == 99.1  # 99th percentile (90 + 0.9 * (100 - 90))


def test_metrics_store_thread_safety():
    """Test that metrics store is thread-safe."""
    import threading
    store = MetricsStore()

    def record_requests():
        for i in range(100):
            store.record_request("/test", 100.0, 200)

    # Create multiple threads
    threads = [threading.Thread(target=record_requests) for _ in range(10)]

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join()

    metrics = store.get_metrics()

    # Should have exactly 1000 requests (10 threads * 100 requests)
    assert metrics["requests"]["/test"]["count"] == 1000


def test_metrics_store_reset():
    """Test resetting metrics store."""
    store = MetricsStore()

    # Record some data
    store.record_request("/test", 100.0, 200)
    store.record_db_query(50.0)
    store.record_session_create()

    # Reset
    store.reset_metrics()

    metrics = store.get_metrics()

    # Check all counters are reset
    assert len(metrics["requests"]) == 0
    assert metrics["database"]["query_count"] == 0
    assert metrics["database"]["slow_query_count"] == 0
    # Active sessions is a gauge, not reset
    assert metrics["sessions"]["active_sessions"] == 1


def test_metrics_store_max_capacity():
    """Test that metrics store has limited capacity."""
    store = MetricsStore()

    # Record more than maxlen (1000) durations
    for i in range(1500):
        store.record_request("/test", float(i), 200)

    metrics = store.get_metrics()

    # Should only have last 1000 durations
    duration_metrics = metrics["requests"]["/test"]["duration_ms"]
    assert duration_metrics["min"] >= 500.0  # First 500 should be dropped


def test_prometheus_format_structure(client: TestClient, auth_headers: dict):
    """Test Prometheus metrics format structure."""
    # Reset and generate traffic
    client.post("/api/v1/metrics/reset", headers=auth_headers)
    client.get("/health")

    response = client.get("/api/v1/metrics/prometheus", headers=auth_headers)
    content = response.text

    # Check metric types
    assert "# TYPE http_requests_total counter" in content
    assert "# TYPE http_request_errors_total counter" in content
    assert "# TYPE http_request_duration_ms summary" in content
    assert "# TYPE db_queries_total counter" in content
    assert "# TYPE db_slow_queries_total counter" in content
    assert "# TYPE sessions_active gauge" in content

    # Check quantile labels
    assert 'quantile="0.5"' in content or "quantile=\"0.5\"" in content
    assert 'quantile="0.95"' in content or "quantile=\"0.95\"" in content
    assert 'quantile="0.99"' in content or "quantile=\"0.99\"" in content


def test_metrics_with_error_requests(client: TestClient, auth_headers: dict):
    """Test metrics correctly track error requests."""
    # Reset metrics
    client.post("/api/v1/metrics/reset", headers=auth_headers)

    # Generate successful requests
    for _ in range(7):
        client.get("/health")

    # Generate error requests (invalid endpoint)
    for _ in range(3):
        client.get("/api/v1/nonexistent")

    # Get metrics
    response = client.get("/api/v1/metrics", headers=auth_headers)
    data = response.json()

    # Check error tracking
    if "/api/v1/nonexistent" in data["metrics"]["requests"]:
        endpoint_metrics = data["metrics"]["requests"]["/api/v1/nonexistent"]
        assert endpoint_metrics["count"] == 3
        assert endpoint_metrics["error_count"] == 3
        assert endpoint_metrics["error_rate"] == 100.0


def test_metrics_no_data():
    """Test metrics with no data recorded."""
    store = MetricsStore()
    metrics = store.get_metrics()

    assert metrics["requests"] == {}
    assert metrics["database"]["query_count"] == 0
    assert metrics["database"]["slow_query_count"] == 0
    assert "duration_ms" not in metrics["database"]
    assert metrics["sessions"]["active_sessions"] == 0
