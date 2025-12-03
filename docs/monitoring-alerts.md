# Monitoring Alerts Configuration

This document defines alerting thresholds and integration options for the Auto-Author production monitoring system.

## Alert Thresholds

### Health Check Alerts

**Critical Priority**

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| Health Check Failure | `/health/ready` returns 503 | 3 consecutive failures | Investigate immediately, check MongoDB connection |
| Liveness Check Failure | `/health/live` returns 503 | 1 failure | Restart application, investigate deadlock |
| MongoDB Connection Lost | MongoDB connection fails | Immediate | Check MongoDB service, network connectivity |

### Performance Alerts

**High Priority**

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| High Error Rate | 4xx/5xx errors | >5% of requests | Check application logs, investigate error patterns |
| Slow Requests | Request duration | >10% of requests >3s | Review slow endpoints, optimize queries |
| Very Slow Requests | Request duration | Any request >10s | Investigate specific endpoint, check for blocking operations |

**Medium Priority**

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| Elevated Error Rate | 4xx/5xx errors | >2% of requests | Monitor trends, investigate if increasing |
| Moderate Slow Requests | Request duration | >20% of requests >1s | Review performance, consider optimization |

### Database Alerts

**Critical Priority**

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| Database Connection Failure | MongoDB connection lost | Immediate | Check MongoDB service, restart if needed |
| Connection Pool Exhaustion | All connections in use | >95% utilization | Increase pool size or investigate connection leaks |

**High Priority**

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| Slow Queries | Query duration | >10% of queries >500ms | Identify slow queries, add indexes, optimize |
| High Query Rate | Queries per second | >1000 qps | Monitor load, consider read replicas or caching |

**Medium Priority**

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| Elevated Slow Queries | Query duration | >5% of queries >500ms | Review query patterns, consider optimization |

### System Resource Alerts

**Critical Priority**

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| Disk Space Critical | Free disk space | <5% free | Clean up logs, increase disk size |
| Memory Critical | Memory usage | >95% used | Restart application, investigate memory leaks |

**High Priority**

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| Disk Space Low | Free disk space | <10% free | Plan disk cleanup or expansion |
| Memory High | Memory usage | >90% used | Monitor memory trends, investigate if increasing |
| CPU High | CPU usage | >80% for >5 minutes | Check for CPU-intensive operations, scale horizontally |

### Session Alerts

**Medium Priority**

| Alert | Condition | Threshold | Action |
|-------|-----------|-----------|--------|
| High Session Count | Active sessions | >1000 concurrent | Monitor user activity, consider session limits |
| Suspicious Sessions | Flagged sessions | >5 flagged/hour | Investigate potential security issues |

## Alert Integration Options

### Option 1: Email Notifications

**Best for:** Small teams, low-traffic applications

**Setup:**
```python
# backend/app/monitoring/alerting.py
import smtplib
from email.mime.text import MIMEText

def send_email_alert(subject: str, body: str):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'alerts@autoauthor.app'
    msg['To'] = 'team@autoauthor.app'

    with smtplib.SMTP('localhost') as server:
        server.send_message(msg)
```

**Pros:**
- Simple to set up
- No additional services required
- Good for non-urgent alerts

**Cons:**
- Can be noisy
- No on-call rotation
- May get missed

### Option 2: Slack Integration

**Best for:** Team collaboration, real-time alerts

**Setup:**
```python
# backend/app/monitoring/alerting.py
import requests

def send_slack_alert(message: str, severity: str):
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

    color_map = {
        "critical": "danger",
        "high": "warning",
        "medium": "warning",
        "low": "good",
    }

    payload = {
        "attachments": [{
            "color": color_map.get(severity, "warning"),
            "title": f"[{severity.upper()}] Auto-Author Alert",
            "text": message,
            "ts": int(time.time()),
        }]
    }

    requests.post(webhook_url, json=payload)
```

**Pros:**
- Real-time notifications
- Team visibility
- Easy to acknowledge

**Cons:**
- Can be noisy in busy channels
- Requires Slack workspace

### Option 3: Discord Integration

**Best for:** Community projects, developer teams

**Setup:**
```python
# backend/app/monitoring/alerting.py
import requests

def send_discord_alert(message: str, severity: str):
    webhook_url = "https://discord.com/api/webhooks/YOUR/WEBHOOK"

    color_map = {
        "critical": 0xFF0000,  # Red
        "high": 0xFFA500,      # Orange
        "medium": 0xFFFF00,    # Yellow
        "low": 0x00FF00,       # Green
    }

    payload = {
        "embeds": [{
            "title": f"[{severity.upper()}] Auto-Author Alert",
            "description": message,
            "color": color_map.get(severity, 0xFFA500),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
    }

    requests.post(webhook_url, json=payload)
```

**Pros:**
- Free and easy to set up
- Good for small teams
- Mobile notifications

**Cons:**
- Not enterprise-grade
- Limited on-call features

### Option 4: PagerDuty Integration

**Best for:** Production systems, on-call teams

**Setup:**
```python
# backend/app/monitoring/alerting.py
import requests

def send_pagerduty_alert(message: str, severity: str):
    api_key = "YOUR_PAGERDUTY_API_KEY"

    severity_map = {
        "critical": "critical",
        "high": "error",
        "medium": "warning",
        "low": "info",
    }

    payload = {
        "routing_key": api_key,
        "event_action": "trigger",
        "payload": {
            "summary": message,
            "severity": severity_map.get(severity, "error"),
            "source": "auto-author-api",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }

    requests.post(
        "https://events.pagerduty.com/v2/enqueue",
        json=payload
    )
```

**Pros:**
- Enterprise-grade
- On-call rotation
- Incident management

**Cons:**
- Paid service
- May be overkill for small projects

## Alert Rules Implementation

### Example: Health Check Monitor

```python
# backend/app/monitoring/health_monitor.py
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
import httpx
from app.monitoring.alerting import send_alert

logger = logging.getLogger(__name__)

class HealthCheckMonitor:
    """Monitor health check endpoints and send alerts on failures."""

    def __init__(
        self,
        health_url: str = "http://localhost:8000/health/ready",
        check_interval: int = 60,  # seconds
        failure_threshold: int = 3,
    ):
        self.health_url = health_url
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self.consecutive_failures = 0
        self.last_alert_time: Optional[datetime] = None
        self.alert_cooldown = 300  # 5 minutes between alerts

    async def run(self):
        """Run continuous health check monitoring."""
        logger.info(f"Starting health check monitor: {self.health_url}")

        while True:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        self.health_url,
                        timeout=10.0
                    )

                if response.status_code == 200:
                    # Health check passed
                    if self.consecutive_failures > 0:
                        logger.info("Health check recovered")
                        send_alert(
                            "Auto-Author health check recovered",
                            severity="low",
                        )
                    self.consecutive_failures = 0
                else:
                    # Health check failed
                    self.consecutive_failures += 1
                    logger.warning(
                        f"Health check failed: {response.status_code} "
                        f"({self.consecutive_failures}/{self.failure_threshold})"
                    )

                    if self.consecutive_failures >= self.failure_threshold:
                        self._send_alert_if_needed(response.status_code)

            except Exception as e:
                self.consecutive_failures += 1
                logger.error(
                    f"Health check error: {e} "
                    f"({self.consecutive_failures}/{self.failure_threshold})"
                )

                if self.consecutive_failures >= self.failure_threshold:
                    self._send_alert_if_needed(error=str(e))

            await asyncio.sleep(self.check_interval)

    def _send_alert_if_needed(
        self,
        status_code: Optional[int] = None,
        error: Optional[str] = None
    ):
        """Send alert if cooldown period has passed."""
        now = datetime.now(timezone.utc)

        # Check cooldown
        if self.last_alert_time:
            time_since_last = (now - self.last_alert_time).total_seconds()
            if time_since_last < self.alert_cooldown:
                return

        # Send alert
        if status_code:
            message = (
                f"Auto-Author health check failing: "
                f"{self.consecutive_failures} consecutive failures "
                f"(status code: {status_code})"
            )
        else:
            message = (
                f"Auto-Author health check failing: "
                f"{self.consecutive_failures} consecutive failures "
                f"(error: {error})"
            )

        send_alert(message, severity="critical")
        self.last_alert_time = now
```

### Example: Metrics-Based Alerts

```python
# backend/app/monitoring/metrics_monitor.py
import asyncio
import logging
from datetime import datetime, timezone
from app.api.metrics import get_metrics_store
from app.monitoring.alerting import send_alert

logger = logging.getLogger(__name__)

class MetricsMonitor:
    """Monitor application metrics and send alerts on threshold violations."""

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.metrics_store = get_metrics_store()

    async def run(self):
        """Run continuous metrics monitoring."""
        logger.info("Starting metrics monitor")

        while True:
            try:
                metrics = self.metrics_store.get_metrics()

                # Check error rate
                self._check_error_rate(metrics["requests"])

                # Check slow requests
                self._check_slow_requests(metrics["requests"])

                # Check database performance
                self._check_database_performance(metrics["database"])

            except Exception as e:
                logger.error(f"Metrics monitoring error: {e}", exc_info=True)

            await asyncio.sleep(self.check_interval)

    def _check_error_rate(self, request_metrics: dict):
        """Check for high error rates."""
        for endpoint, data in request_metrics.items():
            error_rate = data.get("error_rate", 0)

            if error_rate > 5:
                send_alert(
                    f"High error rate on {endpoint}: {error_rate}% "
                    f"({data['error_count']}/{data['count']} requests)",
                    severity="high",
                )
            elif error_rate > 2:
                send_alert(
                    f"Elevated error rate on {endpoint}: {error_rate}% "
                    f"({data['error_count']}/{data['count']} requests)",
                    severity="medium",
                )

    def _check_slow_requests(self, request_metrics: dict):
        """Check for slow requests."""
        for endpoint, data in request_metrics.items():
            if not data.get("duration_ms"):
                continue

            p95 = data["duration_ms"]["p95"]

            if p95 > 3000:
                send_alert(
                    f"Slow requests on {endpoint}: "
                    f"p95={p95:.0f}ms (>3s threshold)",
                    severity="high",
                )
            elif p95 > 1000:
                send_alert(
                    f"Moderate slow requests on {endpoint}: "
                    f"p95={p95:.0f}ms (>1s threshold)",
                    severity="medium",
                )

    def _check_database_performance(self, db_metrics: dict):
        """Check database performance metrics."""
        slow_query_count = db_metrics.get("slow_query_count", 0)
        query_count = db_metrics.get("query_count", 0)

        if query_count > 0:
            slow_query_rate = (slow_query_count / query_count) * 100

            if slow_query_rate > 10:
                send_alert(
                    f"High rate of slow queries: {slow_query_rate:.1f}% "
                    f"({slow_query_count}/{query_count} queries)",
                    severity="high",
                )
            elif slow_query_rate > 5:
                send_alert(
                    f"Elevated rate of slow queries: {slow_query_rate:.1f}% "
                    f"({slow_query_count}/{query_count} queries)",
                    severity="medium",
                )
```

## Testing Alerts

```bash
# Test health check alerts
curl http://localhost:8000/health/ready

# Test metrics alerts (requires authentication)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/metrics

# Simulate failures
# Stop MongoDB to trigger health check failures
sudo systemctl stop mongod
# Wait for alerts to fire
# Restart MongoDB
sudo systemctl start mongod
```

## Alert Response Procedures

See [monitoring-runbook.md](./monitoring-runbook.md) for detailed incident response procedures.
