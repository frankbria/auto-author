# Monitoring Dashboard Guide

This document outlines monitoring dashboard options and panel configurations for the Auto-Author production system.

## Dashboard Options

### Option A: Prometheus + Grafana (Recommended for Production)

**Best for:** Production systems with moderate to high traffic

**Components:**
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Node Exporter**: System metrics (CPU, memory, disk)

**Advantages:**
- Industry standard
- Rich visualization options
- Powerful querying (PromQL)
- Alerting built-in
- Free and open source

**Resource Requirements:**
- Prometheus: ~500MB RAM, 10GB disk
- Grafana: ~200MB RAM, 1GB disk
- Combined: ~700MB RAM, 11GB disk

**Setup Steps:**

1. **Install Prometheus:**
```bash
# Download Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-2.45.0.linux-amd64.tar.gz
cd prometheus-2.45.0.linux-amd64

# Create configuration
cat > prometheus.yml <<EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'auto-author'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/metrics/prometheus'
    bearer_token: 'YOUR_AUTH_TOKEN'

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
EOF

# Start Prometheus
./prometheus --config.file=prometheus.yml
```

2. **Install Grafana:**
```bash
# Add Grafana repository
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -

# Install Grafana
sudo apt-get update
sudo apt-get install grafana

# Start Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server

# Access at http://localhost:3000 (default: admin/admin)
```

3. **Configure Grafana:**
- Add Prometheus data source: Configuration > Data Sources > Add > Prometheus
- URL: `http://localhost:9090`
- Import dashboard (see Dashboard Panels section below)

### Option B: Simple Monitoring Script + Logs

**Best for:** Small deployments, limited resources, quick setup

**Components:**
- Python monitoring script
- Log aggregation
- Simple web dashboard

**Advantages:**
- Minimal resource usage (<50MB RAM)
- No additional services
- Easy to customize
- Good for development/staging

**Setup:**

```python
# backend/monitoring/simple_dashboard.py
import asyncio
import httpx
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# Store recent metrics
metrics_history = []

async def collect_metrics():
    """Collect metrics periodically."""
    while True:
        try:
            async with httpx.AsyncClient() as client:
                # Get health
                health = await client.get("http://localhost:8000/health/ready")
                health_data = health.json()

                # Get metrics (requires auth)
                metrics = await client.get(
                    "http://localhost:8000/api/v1/metrics",
                    headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
                )
                metrics_data = metrics.json()

                # Store
                metrics_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "health": health_data,
                    "metrics": metrics_data,
                })

                # Keep last 1000 data points
                if len(metrics_history) > 1000:
                    metrics_history.pop(0)

        except Exception as e:
            print(f"Error collecting metrics: {e}")

        await asyncio.sleep(60)  # Collect every minute

@app.get("/")
async def dashboard():
    """Simple HTML dashboard."""
    if not metrics_history:
        return HTMLResponse("<h1>No data yet...</h1>")

    latest = metrics_history[-1]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Auto-Author Monitoring</title>
        <meta http-equiv="refresh" content="60">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .metric {{ padding: 10px; margin: 10px; border: 1px solid #ccc; }}
            .healthy {{ background-color: #d4edda; }}
            .warning {{ background-color: #fff3cd; }}
            .error {{ background-color: #f8d7da; }}
        </style>
    </head>
    <body>
        <h1>Auto-Author Monitoring Dashboard</h1>
        <p>Last updated: {latest['timestamp']}</p>

        <h2>Health Status</h2>
        <div class="metric healthy">
            <strong>Status:</strong> {latest['health'].get('status', 'unknown')}
        </div>

        <h2>Request Metrics</h2>
        <!-- Add metrics visualization here -->

        <h2>Database Metrics</h2>
        <!-- Add database metrics here -->
    </body>
    </html>
    """

    return HTMLResponse(html)

@app.on_event("startup")
async def startup():
    asyncio.create_task(collect_metrics())
```

Run the dashboard:
```bash
cd backend/monitoring
uvicorn simple_dashboard:app --port 9090
# Access at http://localhost:9090
```

### Option C: Cloud Monitoring Services

**Best for:** Teams preferring managed services, multi-region deployments

#### DataDog

**Advantages:**
- Full-featured APM
- Log aggregation
- Infrastructure monitoring
- Pre-built dashboards

**Cost:** ~$15-31/host/month

**Setup:**
```bash
# Install DataDog agent
DD_API_KEY=YOUR_KEY bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"

# Configure Python integration
cat > /etc/datadog-agent/conf.d/python.d/conf.yaml <<EOF
init_config:

instances:
  - host: localhost
    port: 8000
    tags:
      - env:production
      - app:auto-author
EOF

sudo systemctl restart datadog-agent
```

#### New Relic

**Advantages:**
- Application performance monitoring
- Error tracking
- Transaction tracing
- Custom dashboards

**Cost:** Free tier available, paid plans from $99/month

**Setup:**
```bash
# Install New Relic Python agent
pip install newrelic

# Configure
newrelic-admin generate-config YOUR_LICENSE_KEY newrelic.ini

# Run application with New Relic
NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program uvicorn app.main:app
```

## Dashboard Panels

### Panel 1: Request Rate

**Visualization:** Time series graph

**Metrics:**
- Total requests per minute
- Requests by endpoint
- Success rate (2xx/3xx responses)

**Grafana Query (PromQL):**
```promql
# Requests per minute
rate(http_requests_total[1m])

# By endpoint
sum by(endpoint) (rate(http_requests_total[1m]))
```

### Panel 2: Error Rate

**Visualization:** Time series graph + gauge

**Metrics:**
- 4xx error rate (%)
- 5xx error rate (%)
- Errors by endpoint

**Grafana Query (PromQL):**
```promql
# Error rate percentage
(sum(rate(http_request_errors_total[1m])) / sum(rate(http_requests_total[1m]))) * 100

# Errors by endpoint
sum by(endpoint) (rate(http_request_errors_total[1m]))
```

### Panel 3: Response Time

**Visualization:** Heatmap + time series

**Metrics:**
- p50, p95, p99 response times
- Response time by endpoint
- Slow request count (>3s)

**Grafana Query (PromQL):**
```promql
# P95 response time
http_request_duration_ms{quantile="0.95"}

# By endpoint
http_request_duration_ms{quantile="0.95"} by (endpoint)
```

### Panel 4: Database Performance

**Visualization:** Time series + stat

**Metrics:**
- Queries per second
- Slow query count (>500ms)
- Query duration (p50, p95, p99)
- Connection pool usage

**Grafana Query (PromQL):**
```promql
# Queries per second
rate(db_queries_total[1m])

# Slow query rate
rate(db_slow_queries_total[1m])

# Query duration p95
db_query_duration_ms{quantile="0.95"}
```

### Panel 5: System Resources

**Visualization:** Gauge + time series

**Metrics:**
- CPU usage (%)
- Memory usage (%)
- Disk usage (%)
- Network I/O

**Grafana Query (PromQL - requires Node Exporter):**
```promql
# CPU usage
100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Disk usage
(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100
```

### Panel 6: Active Sessions

**Visualization:** Stat + time series

**Metrics:**
- Current active sessions
- Sessions created (rate)
- Sessions expired (rate)
- Suspicious sessions flagged

**Grafana Query (PromQL):**
```promql
# Active sessions
sessions_active

# Session creation rate
rate(sessions_created_total[1m])

# Session expiration rate
rate(sessions_expired_total[1m])
```

### Panel 7: Application Uptime

**Visualization:** Stat + timeline

**Metrics:**
- Uptime (seconds/human-readable)
- Health check status
- Deployment events

**Grafana Query (PromQL):**
```promql
# Uptime in seconds
(time() - process_start_time_seconds)
```

### Panel 8: Business Metrics

**Visualization:** Stat + time series

**Metrics:**
- Books created (rate)
- Chapters generated (rate)
- TOC generations (rate)
- Exports (rate)

**Note:** Requires instrumenting business logic with custom metrics

## Complete Grafana Dashboard JSON

Save this as `auto-author-dashboard.json` and import in Grafana:

```json
{
  "dashboard": {
    "title": "Auto-Author Production Monitoring",
    "tags": ["auto-author", "production"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[1m])",
            "legendFormat": "Total Requests/min"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "(sum(rate(http_request_errors_total[1m])) / sum(rate(http_requests_total[1m]))) * 100",
            "legendFormat": "Error Rate %"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Response Time (P95)",
        "type": "graph",
        "targets": [
          {
            "expr": "http_request_duration_ms{quantile=\"0.95\"}",
            "legendFormat": "{{endpoint}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "Database Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(db_queries_total[1m])",
            "legendFormat": "Queries/sec"
          },
          {
            "expr": "rate(db_slow_queries_total[1m])",
            "legendFormat": "Slow Queries/sec"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      },
      {
        "id": 5,
        "title": "System Resources",
        "type": "graph",
        "targets": [
          {
            "expr": "100 - (avg by(instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "legendFormat": "CPU %"
          },
          {
            "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
            "legendFormat": "Memory %"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
      },
      {
        "id": 6,
        "title": "Active Sessions",
        "type": "stat",
        "targets": [
          {
            "expr": "sessions_active",
            "legendFormat": "Active Sessions"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
      }
    ]
  }
}
```

## Accessing Metrics

### Via Health Endpoints

```bash
# Basic health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/ready

# Detailed health (requires auth)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/health/detailed
```

### Via Metrics Endpoints

```bash
# JSON metrics (requires auth)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/metrics

# Prometheus format (requires auth)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/metrics/prometheus
```

## Next Steps

1. Choose monitoring option based on your requirements and resources
2. Set up dashboard following the setup steps above
3. Configure alerts (see [monitoring-alerts.md](./monitoring-alerts.md))
4. Review monitoring runbook (see [monitoring-runbook.md](./monitoring-runbook.md))
5. Test monitoring system with simulated failures

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [DataDog Python Integration](https://docs.datadoghq.com/integrations/python/)
- [New Relic Python Agent](https://docs.newrelic.com/docs/apm/agents/python-agent/)
