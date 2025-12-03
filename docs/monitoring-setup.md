# Monitoring System Setup Guide

Complete guide for setting up the Auto-Author monitoring and observability system in production.

## Quick Start

### 1. Enable Structured Logging

Add to `backend/app/main.py`:

```python
from app.core.logging import configure_production_logging

# At application startup
@app.on_event("startup")
async def startup_event():
    # Configure production logging
    configure_production_logging()
    logger.info("Application starting up")
```

### 2. Access Health Checks

Health check endpoints are automatically available:

```bash
# Basic health check (no auth required)
curl http://your-domain.com/health

# Readiness check (no auth required)
curl http://your-domain.com/health/ready

# Liveness check (no auth required)
curl http://your-domain.com/health/live

# Detailed health check (auth required)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://your-domain.com/health/detailed
```

### 3. Access Metrics

Metrics endpoints require authentication:

```bash
# JSON format
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://your-domain.com/api/v1/metrics

# Prometheus format
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://your-domain.com/api/v1/metrics/prometheus
```

## Complete Production Setup

### Step 1: Install Required Dependencies

```bash
cd backend

# Install psutil for system metrics
uv add psutil

# Verify installation
uv run python -c "import psutil; print(psutil.__version__)"
```

### Step 2: Configure Logging

#### Production Environment

Edit `backend/app/main.py` or create `backend/app/monitoring/setup.py`:

```python
import os
import logging
from app.core.logging import setup_logging

# Determine environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    # Production: JSON logging, INFO level, file logging enabled
    setup_logging(
        level="INFO",
        use_json=True,
        enable_file_logging=True,
        log_dir="/var/log/auto-author"
    )
elif ENVIRONMENT == "staging":
    # Staging: JSON logging, DEBUG level, file logging enabled
    setup_logging(
        level="DEBUG",
        use_json=True,
        enable_file_logging=True,
        log_dir="/var/log/auto-author"
    )
else:
    # Development: Human-readable, DEBUG level, local logs
    setup_logging(
        level="DEBUG",
        use_json=False,
        enable_file_logging=True,
        log_dir="./logs"
    )

logger = logging.getLogger(__name__)
logger.info(f"Logging configured for {ENVIRONMENT} environment")
```

#### Log Directory Setup

```bash
# Create production log directory
sudo mkdir -p /var/log/auto-author

# Set permissions
sudo chown -R $USER:$USER /var/log/auto-author
sudo chmod -R 755 /var/log/auto-author

# Set up log rotation
sudo tee /etc/logrotate.d/auto-author <<EOF
/var/log/auto-author/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $USER $USER
}
EOF
```

### Step 3: Integrate Request Tracking Middleware

The request tracking middleware is automatically added in `main.py`. Verify it's configured:

```python
from app.api.middleware.request_tracking import add_request_tracking_middleware

# Add after CORS middleware
add_request_tracking_middleware(app)
```

If not present, add it to `backend/app/main.py`.

### Step 4: Add Health and Metrics Routes

Update `backend/app/api/endpoints/router.py`:

```python
from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router

router = APIRouter()

# Include health checks (no prefix, at root level)
router.include_router(health_router)

# Include metrics (under /api/v1)
router.include_router(metrics_router)

# ... other routers ...
```

Or add directly in `main.py`:

```python
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router

# Add health checks at root level (no auth required)
app.include_router(health_router)

# Add metrics under API prefix (auth required)
app.include_router(metrics_router, prefix=settings.API_V1_PREFIX)
```

### Step 5: Instrument Database Operations (Optional)

Add query monitoring to critical database operations:

```python
from app.db.monitoring import track_query, query_tracker

# Example: Decorate a function
@track_query("get_user_by_id", slow_query_threshold_ms=500)
async def get_user_by_id(user_id: str):
    return await users_collection.find_one({"_id": ObjectId(user_id)})

# Example: Context manager for complex operations
async def get_user_books_with_chapters(user_id: str):
    async with query_tracker("get_user_books_with_chapters", user_id=user_id):
        books = await books_collection.find({"user_id": user_id}).to_list(length=None)
        for book in books:
            book["chapters"] = await chapters_collection.find(
                {"book_id": str(book["_id"])}
            ).to_list(length=None)
        return books
```

### Step 6: Configure Environment Variables

Add to `.env` or environment:

```bash
# Environment
ENVIRONMENT=production

# Logging
LOG_LEVEL=INFO
LOG_DIR=/var/log/auto-author

# Monitoring
ENABLE_METRICS=true
SLOW_REQUEST_THRESHOLD_MS=1000
SLOW_QUERY_THRESHOLD_MS=500
```

### Step 7: Set Up Load Balancer Health Checks

If using a load balancer (nginx, AWS ALB, etc.), configure health checks:

#### Nginx Example

```nginx
upstream auto_author_backend {
    server localhost:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.autoauthor.app;

    # Health check endpoint
    location /health {
        proxy_pass http://auto_author_backend/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;

        # Health check specific settings
        proxy_connect_timeout 5s;
        proxy_read_timeout 5s;
    }

    # Application endpoints
    location / {
        proxy_pass http://auto_author_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Add request ID if not present
        proxy_set_header X-Request-ID $request_id;
    }
}
```

#### AWS Application Load Balancer

```json
{
  "HealthCheck": {
    "HealthCheckPath": "/health/ready",
    "HealthCheckIntervalSeconds": 30,
    "HealthCheckTimeoutSeconds": 5,
    "HealthyThresholdCount": 2,
    "UnhealthyThresholdCount": 3,
    "Matcher": {
      "HttpCode": "200"
    }
  }
}
```

### Step 8: Configure Monitoring Dashboard

Choose one of the options in [monitoring-dashboard.md](./monitoring-dashboard.md):

- **Option A**: Prometheus + Grafana (recommended for production)
- **Option B**: Simple monitoring script (good for staging)
- **Option C**: Cloud service (DataDog, New Relic)

### Step 9: Set Up Alerts

Configure alerts based on [monitoring-alerts.md](./monitoring-alerts.md):

1. Choose alerting method (Email, Slack, Discord, PagerDuty)
2. Implement alert integration
3. Configure alert thresholds
4. Test alerts

### Step 10: Verify Setup

```bash
# 1. Check health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/live

# 2. Get auth token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","password":"your-password-here"}' | jq -r '.access_token')

# 3. Check detailed health
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/health/detailed

# 4. Check metrics
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/metrics

# 5. Check logs
tail -f /var/log/auto-author/app.log

# 6. Generate some load
for i in {1..100}; do
    curl http://localhost:8000/health &
done
wait

# 7. Check metrics again to see recorded requests
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/metrics
```

## Troubleshooting

### Issue: Health Checks Return 503

**Symptoms:**
- `/health/ready` returns 503 status
- Error: "MongoDB connection not ready"

**Solutions:**

1. Check MongoDB is running:
```bash
sudo systemctl status mongod
```

2. Verify MongoDB connection string:
```bash
# Check environment variable
echo $DATABASE_URI

# Test connection
mongosh $DATABASE_URI --eval "db.adminCommand('ping')"
```

3. Check network connectivity:
```bash
telnet localhost 27017
```

### Issue: Metrics Not Updating

**Symptoms:**
- `/api/v1/metrics` returns empty or stale data
- Request counts not increasing

**Solutions:**

1. Verify middleware is installed:
```python
# In main.py, check for:
from app.api.middleware.request_tracking import add_request_tracking_middleware
add_request_tracking_middleware(app)
```

2. Check logs for errors:
```bash
tail -f /var/log/auto-author/app.log | grep -i "metrics"
```

3. Reset metrics and test:
```bash
# Reset metrics
curl -X POST -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/metrics/reset

# Generate test traffic
for i in {1..10}; do curl http://localhost:8000/health; done

# Check metrics
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/metrics
```

### Issue: Logs Not Being Written

**Symptoms:**
- Log directory empty
- No log files created

**Solutions:**

1. Check log directory permissions:
```bash
ls -la /var/log/auto-author
sudo chown -R $USER:$USER /var/log/auto-author
```

2. Verify logging configuration:
```python
# In main.py or monitoring/setup.py
import logging
logger = logging.getLogger(__name__)
logger.info("Test log message")
```

3. Check log configuration:
```bash
# Verify environment
echo $LOG_LEVEL
echo $LOG_DIR
```

### Issue: Slow Queries Not Being Logged

**Symptoms:**
- No slow query warnings in logs
- Queries are actually slow (verified with MongoDB profiler)

**Solutions:**

1. Verify query monitoring is enabled:
```python
# Check if decorators are applied
from app.db.monitoring import track_query

@track_query("operation_name", slow_query_threshold_ms=500)
async def your_function():
    pass
```

2. Lower threshold temporarily for testing:
```python
@track_query("operation_name", slow_query_threshold_ms=100)  # 100ms for testing
```

3. Check MongoDB slow query log:
```bash
mongosh --eval "db.setProfilingLevel(1, 500)"  # Profile queries >500ms
mongosh --eval "db.system.profile.find().limit(10).pretty()"
```

## Performance Impact

The monitoring system has minimal performance impact:

- **Health checks**: <1ms overhead
- **Request tracking middleware**: ~0.5ms per request
- **Metrics collection**: ~0.1ms per request
- **Database query tracking**: ~0.1ms per query
- **Structured logging**: ~0.2ms per log entry

Total overhead: **~1ms per request** (<0.1% for typical requests)

## Security Considerations

1. **Metrics require authentication**: `/api/v1/metrics/*` endpoints require valid JWT token
2. **Detailed health requires authentication**: `/health/detailed` requires valid JWT token
3. **Basic health checks are public**: `/health`, `/health/ready`, `/health/live` are public (needed for load balancers)
4. **Logs may contain sensitive data**: Ensure log files have proper permissions (644) and log rotation is configured
5. **Prometheus scraping**: If using Prometheus, ensure scrape endpoint uses authentication or is on internal network only

## Next Steps

1. Review [monitoring-alerts.md](./monitoring-alerts.md) for alert configuration
2. Review [monitoring-dashboard.md](./monitoring-dashboard.md) for dashboard options
3. Review [monitoring-runbook.md](./monitoring-runbook.md) for incident response procedures
4. Schedule regular reviews of monitoring data
5. Set up automated alert testing

## Resources

- [FastAPI Monitoring Best Practices](https://fastapi.tiangolo.com/advanced/advanced-middleware/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Python Logging Documentation](https://docs.python.org/3/howto/logging.html)
- [psutil Documentation](https://psutil.readthedocs.io/)
