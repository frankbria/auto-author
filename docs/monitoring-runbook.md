# Monitoring Runbook - Incident Response Guide

This runbook provides step-by-step procedures for responding to monitoring alerts and investigating incidents.

## General Incident Response Process

1. **Acknowledge** - Acknowledge the alert to prevent duplicate responses
2. **Assess** - Check health status and determine severity
3. **Investigate** - Use monitoring tools to identify root cause
4. **Mitigate** - Take action to restore service
5. **Document** - Record findings and actions taken
6. **Follow-up** - Create tasks for permanent fixes if needed

## Alert Response Procedures

### 1. Health Check Failure

**Alert:** "Auto-Author health check failing: 3 consecutive failures"

**Severity:** Critical

**Immediate Actions:**

```bash
# 1. Check if application is running
sudo systemctl status auto-author
# or
pm2 status

# 2. Check health endpoint directly
curl -v http://localhost:8000/health/ready

# 3. Check application logs
tail -n 100 /var/log/auto-author/app.log
# or
pm2 logs auto-author --lines 100

# 4. Check MongoDB status
sudo systemctl status mongod
mongosh --eval "db.adminCommand('ping')"

# 5. Check network connectivity
telnet localhost 27017
```

**Resolution Steps:**

If MongoDB is down:
```bash
# Restart MongoDB
sudo systemctl restart mongod
sudo systemctl status mongod

# Verify health check recovers
watch -n 5 'curl -s http://localhost:8000/health/ready'
```

If application is down:
```bash
# Restart application
sudo systemctl restart auto-author
# or
pm2 restart auto-author

# Check logs for errors
tail -f /var/log/auto-author/app.log
```

If network issues:
```bash
# Check firewall
sudo ufw status
sudo firewall-cmd --list-all

# Check listening ports
sudo netstat -tlnp | grep 8000
sudo netstat -tlnp | grep 27017

# Check DNS resolution
nslookup your-mongodb-host
```

**Follow-up:**
- Document root cause
- Create task if configuration changes needed
- Review monitoring alerts to prevent recurrence

### 2. High Error Rate

**Alert:** "High error rate on /api/v1/books: 8.5% (42/500 requests)"

**Severity:** High

**Immediate Actions:**

```bash
# 1. Check current error rate
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/metrics | jq '.metrics.requests'

# 2. Check recent errors in logs
tail -n 200 /var/log/auto-author/error.log

# 3. Check specific endpoint errors
tail -n 500 /var/log/auto-author/app.log | grep '/api/v1/books' | grep ERROR

# 4. Check for patterns (same user, same error type, etc.)
tail -n 500 /var/log/auto-author/app.log | grep '/api/v1/books' | grep ERROR | jq -s 'group_by(.error_type) | map({error: .[0].error_type, count: length})'
```

**Investigation Questions:**

1. **What type of errors?**
   - 4xx (client errors): User input validation, authentication issues
   - 5xx (server errors): Application bugs, database issues

2. **Is it affecting all users or specific users?**
   ```bash
   # Group errors by user_id
   grep '/api/v1/books' /var/log/auto-author/app.log | grep ERROR | jq -s 'group_by(.user_id) | map({user: .[0].user_id, count: length}) | sort_by(.count) | reverse'
   ```

3. **Recent code deployments?**
   ```bash
   # Check recent commits
   git log --oneline -10

   # Check deployment time
   sudo systemctl status auto-author | grep Active
   ```

4. **Database issues?**
   ```bash
   # Check MongoDB logs
   tail -n 100 /var/log/mongodb/mongod.log

   # Check database performance
   mongosh --eval "db.serverStatus()" | grep connections
   ```

**Resolution Steps:**

For validation errors (4xx):
```bash
# Review recent code changes
git diff HEAD~1 -- backend/app/api/endpoints/books.py

# Check validation schemas
cat backend/app/schemas/book.py
```

For server errors (5xx):
```bash
# Check for exceptions
grep -A 10 "Traceback" /var/log/auto-author/error.log | tail -50

# Check database connectivity
mongosh $DATABASE_URI --eval "db.books.findOne()"

# Roll back if recent deployment
git revert HEAD
sudo systemctl restart auto-author
```

**Follow-up:**
- Create bug report if application issue
- Update validation if client error
- Add monitoring for specific error patterns

### 3. Slow Requests

**Alert:** "Slow requests on /api/v1/toc/generate: p95=4250ms (>3s threshold)"

**Severity:** High

**Immediate Actions:**

```bash
# 1. Check current performance metrics
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/metrics | jq '.metrics.requests."/api/v1/toc/generate"'

# 2. Check for slow query logs
grep "Slow query detected" /var/log/auto-author/app.log | tail -20

# 3. Check database performance
mongosh --eval "db.currentOp({'secs_running': {'\$gt': 1}})"

# 4. Check system resources
top -b -n 1 | head -20
free -h
df -h
```

**Investigation Questions:**

1. **Is it a database issue?**
   ```bash
   # Check slow queries
   mongosh --eval "db.setProfilingLevel(1, 500); db.system.profile.find().sort({ts:-1}).limit(10).pretty()"

   # Check indexes
   mongosh $DATABASE_URI --eval "db.books.getIndexes()"
   ```

2. **Is it a network issue?**
   ```bash
   # Check latency to MongoDB
   ping -c 5 your-mongodb-host

   # Check network I/O
   iftop -i eth0
   ```

3. **Is it a resource issue?**
   ```bash
   # Check CPU usage
   mpstat 1 10

   # Check memory usage
   vmstat 1 10

   # Check disk I/O
   iostat -x 1 10
   ```

4. **Is it an OpenAI API issue?**
   ```bash
   # Check OpenAI API calls in logs
   grep "OpenAI API" /var/log/auto-author/app.log | tail -20

   # Check if OpenAI API is down
   curl -s https://status.openai.com/api/v2/status.json | jq
   ```

**Resolution Steps:**

For database performance:
```bash
# Add missing indexes
mongosh $DATABASE_URI <<EOF
use auto_author;
db.books.createIndex({"user_id": 1, "created_at": -1});
db.chapters.createIndex({"book_id": 1, "order": 1});
EOF

# Optimize queries (see slow query logs for specific queries)
```

For API latency:
```python
# Add caching (example)
from functools import lru_cache
import asyncio

@lru_cache(maxsize=100)
async def cached_openai_call(prompt: str):
    # ... OpenAI API call ...
    pass
```

For resource constraints:
```bash
# Scale vertically (more resources)
# or
# Scale horizontally (more instances)

# Temporary: Restart to clear memory
sudo systemctl restart auto-author
```

**Follow-up:**
- Create performance optimization task
- Review query optimization opportunities
- Consider caching strategy
- Review API rate limits

### 4. Database Connection Failure

**Alert:** "MongoDB connection lost"

**Severity:** Critical

**Immediate Actions:**

```bash
# 1. Check MongoDB status
sudo systemctl status mongod

# 2. Try to connect
mongosh $DATABASE_URI --eval "db.adminCommand('ping')"

# 3. Check MongoDB logs
tail -n 100 /var/log/mongodb/mongod.log

# 4. Check connection pool
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/health/detailed | jq '.checks.mongodb'

# 5. Check network
telnet localhost 27017
```

**Resolution Steps:**

If MongoDB is down:
```bash
# Start MongoDB
sudo systemctl start mongod
sudo systemctl status mongod

# Check if it stays up
sleep 30
sudo systemctl status mongod

# If it crashes again, check logs for root cause
tail -n 200 /var/log/mongodb/mongod.log
```

If connection pool exhausted:
```bash
# Check current connections
mongosh --eval "db.serverStatus().connections"

# Check application connection pool config
grep -r "maxPoolSize" backend/app/db/

# Restart application to reset connections
sudo systemctl restart auto-author
```

If authentication failure:
```bash
# Verify credentials
echo $DATABASE_URI

# Test connection with explicit credentials
mongosh --host localhost --port 27017 --username user --password pass --authenticationDatabase admin

# Update environment variables if needed
sudo vim /etc/environment
# or
sudo vim /etc/systemd/system/auto-author.service
```

**Follow-up:**
- Investigate why MongoDB stopped
- Review connection pool configuration
- Set up MongoDB monitoring
- Create backup/failover plan

### 5. Disk Space Low

**Alert:** "Low disk space: 8% free"

**Severity:** High

**Immediate Actions:**

```bash
# 1. Check disk usage
df -h

# 2. Find largest directories
du -sh /* 2>/dev/null | sort -h

# 3. Check log files
du -sh /var/log/auto-author/*
ls -lh /var/log/auto-author/

# 4. Check MongoDB data
du -sh /var/lib/mongodb
```

**Resolution Steps:**

Clean up logs:
```bash
# Compress old logs
cd /var/log/auto-author
gzip *.log.1 *.log.2

# Remove old compressed logs
find /var/log/auto-author -name "*.gz" -mtime +7 -delete

# Truncate current logs (if extremely large)
# CAUTION: This loses log data
truncate -s 0 /var/log/auto-author/app.log
```

Clean up MongoDB:
```bash
# Check database size
mongosh --eval "db.stats(1024*1024)"  # Size in MB

# Compact collections (requires downtime)
mongosh --eval "db.books.compact()"
mongosh --eval "db.audit_logs.compact()"

# Or drop old audit logs
mongosh <<EOF
use auto_author;
db.audit_logs.deleteMany({
  created_at: { \$lt: new Date(Date.now() - 90*24*60*60*1000) }  // 90 days old
});
EOF
```

Clean up application data:
```bash
# Remove temporary files
find /tmp -name "auto-author-*" -mtime +7 -delete

# Remove old uploads (if applicable)
find /var/lib/auto-author/uploads -mtime +30 -delete
```

**Long-term solution:**
```bash
# Increase disk size
# or
# Set up automated cleanup
cat > /etc/cron.daily/auto-author-cleanup <<'EOF'
#!/bin/bash
# Clean up logs older than 7 days
find /var/log/auto-author -name "*.gz" -mtime +7 -delete
# Clean up old audit logs
mongosh auto_author --eval "db.audit_logs.deleteMany({created_at: {\$lt: new Date(Date.now() - 90*24*60*60*1000)}})"
EOF

chmod +x /etc/cron.daily/auto-author-cleanup
```

**Follow-up:**
- Monitor disk usage trends
- Set up disk space alerts
- Review log retention policy
- Consider log aggregation service

### 6. Memory High

**Alert:** "High memory usage: 92%"

**Severity:** High

**Immediate Actions:**

```bash
# 1. Check memory usage
free -h
ps aux --sort=-%mem | head -10

# 2. Check for memory leaks
top -b -n 1 | grep auto-author

# 3. Check application metrics
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/health/detailed | jq '.checks.system_resources.memory_percent'

# 4. Check swap usage
swapon --show
```

**Investigation Questions:**

1. **Is it a gradual increase?**
   ```bash
   # Check memory trends
   sar -r 1 10
   ```

2. **Recent increase in traffic?**
   ```bash
   # Check request rate
   curl -H "Authorization: Bearer $TOKEN" \
        http://localhost:8000/api/v1/metrics | jq '.metrics.requests'
   ```

3. **Memory leak in application?**
   ```bash
   # Check application uptime vs memory growth
   systemctl status auto-author | grep Active
   ps aux | grep auto-author
   ```

**Resolution Steps:**

Immediate (restart):
```bash
# Restart application
sudo systemctl restart auto-author

# Monitor memory after restart
watch -n 5 'free -h'
```

Investigate leak:
```python
# Add memory profiling (development/staging)
# backend/app/monitoring/memory_profiler.py
import tracemalloc
import logging

logger = logging.getLogger(__name__)

class MemoryMonitor:
    def __init__(self):
        tracemalloc.start()
        self.snapshot = None

    def take_snapshot(self):
        new_snapshot = tracemalloc.take_snapshot()
        if self.snapshot:
            top_stats = new_snapshot.compare_to(self.snapshot, 'lineno')
            logger.warning("Top 10 memory allocation differences:")
            for stat in top_stats[:10]:
                logger.warning(str(stat))
        self.snapshot = new_snapshot

# Use in application
monitor = MemoryMonitor()

@app.middleware("http")
async def memory_monitor_middleware(request, call_next):
    if request.url.path == "/debug/memory":
        monitor.take_snapshot()
    return await call_next(request)
```

**Follow-up:**
- Profile application for memory leaks
- Review caching strategy
- Consider increasing memory
- Set up memory monitoring alerts

## Common Investigation Commands

### Check Application Status
```bash
# Systemd service
sudo systemctl status auto-author

# PM2 process manager
pm2 status
pm2 logs auto-author --lines 100

# Docker container
docker ps | grep auto-author
docker logs auto-author --tail 100
```

### Check Logs
```bash
# Application logs
tail -f /var/log/auto-author/app.log

# Error logs only
tail -f /var/log/auto-author/error.log

# Search for errors
grep -i error /var/log/auto-author/app.log | tail -50

# JSON logs (if using structured logging)
tail -n 100 /var/log/auto-author/app.log | jq 'select(.level == "ERROR")'
```

### Check Database
```bash
# Connection test
mongosh $DATABASE_URI --eval "db.adminCommand('ping')"

# Check connections
mongosh --eval "db.serverStatus().connections"

# Check current operations
mongosh --eval "db.currentOp()"

# Check slow queries
mongosh --eval "db.system.profile.find().sort({ts:-1}).limit(5).pretty()"
```

### Check System Resources
```bash
# CPU
top -b -n 1 | head -20
mpstat 1 5

# Memory
free -h
vmstat 1 5

# Disk
df -h
iostat -x 1 5

# Network
netstat -an | grep ESTABLISHED | wc -l
ss -s
```

### Check Network
```bash
# Port listening
sudo netstat -tlnp | grep 8000

# Connection test
curl -v http://localhost:8000/health

# DNS resolution
nslookup your-domain.com

# Firewall
sudo ufw status
sudo iptables -L
```

## Escalation Procedures

### Severity Levels

**Critical (P0):**
- Service completely down
- Data loss occurring
- Security breach

**High (P1):**
- Significant degradation
- High error rates
- Performance severely impacted

**Medium (P2):**
- Moderate issues
- Some users affected
- Workaround available

**Low (P3):**
- Minor issues
- Few users affected
- No immediate impact

### Escalation Contacts

Update with your team's contact information:

```yaml
Primary On-Call:
  Name: [Your Name]
  Phone: [Your Phone]
  Email: [Your Email]

Secondary On-Call:
  Name: [Backup Name]
  Phone: [Backup Phone]
  Email: [Backup Email]

Database Admin:
  Name: [DBA Name]
  Phone: [DBA Phone]
  Email: [DBA Email]

Infrastructure Team:
  Email: infra@autoauthor.app
  Slack: #infrastructure
```

## Post-Incident Review

After resolving an incident, conduct a blameless post-mortem:

1. **Timeline** - Document what happened and when
2. **Root Cause** - Identify the underlying cause
3. **Impact** - Measure user impact and duration
4. **Resolution** - Document how it was fixed
5. **Prevention** - Identify ways to prevent recurrence
6. **Action Items** - Create tasks for improvements

Template: `docs/incident-template.md`

## Resources

- [Monitoring Setup Guide](./monitoring-setup.md)
- [Alert Configuration](./monitoring-alerts.md)
- [Dashboard Guide](./monitoring-dashboard.md)
- [MongoDB Operations Manual](https://www.mongodb.com/docs/manual/)
- [FastAPI Debugging](https://fastapi.tiangolo.com/tutorial/debugging/)
