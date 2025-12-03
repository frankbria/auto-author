# FastAPI Application - Auto Author Backend

This project is a FastAPI application designed to provide a robust backend for the Auto Author application. It is structured to facilitate easy development and maintenance.

## Prerequisites

- Python 3.13+
- uv (Python package manager) - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- MongoDB
- Redis (for distributed rate limiting) - Install with: `sudo apt-get install redis-server` or `brew install redis`

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   └── router.py
│   │   └── dependencies.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── database.py
│   ├── models/
│   │   └── __init__.py
│   └── schemas/
│       └── __init__.py
├── requirements.txt
└── README.md
```

## Installation

To get started with this project, clone the repository and set up the virtual environment:

1. Create and activate virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
uv pip install -r requirements.txt
```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in required values (MongoDB URI, API keys, etc.)
   - Configure Redis connection (see Redis Configuration section below)

## Usage

To run the FastAPI application, execute the following command:

```bash
uv run uvicorn app.main:app --reload
```

This will start the server at `http://127.0.0.1:8000`. You can access the interactive API documentation at `http://127.0.0.1:8000/docs`.

## Development

### Running Tests
```bash
uv run pytest                          # Run all tests
uv run pytest -v                       # Verbose output
uv run pytest -k "test_name"           # Run specific test
uv run pytest --cov=app               # Run with coverage
uv run pytest tests/test_file.py      # Run specific test file
```

### Code Formatting
```bash
uv run black .                         # Format all Python files
uv run ruff check .                    # Run linting
uv run ruff format .                   # Format with ruff
```

### Package Management

This project uses `uv` as the package manager. Always use `uv` commands within the virtual environment:

- Install new package: `uv pip install package-name`
- Update requirements: `uv pip freeze > requirements.txt`
- Run any command: `uv run command-name`

### Quick Validation Scripts
```bash
uv run python quick_validate.py        # Validate implementation
uv run python test_toc_transactions.py # Test TOC transactions
```

## Redis Configuration

Redis is used for distributed rate limiting across multiple application instances (e.g., PM2 processes). This ensures that rate limits are enforced correctly even when running multiple backend servers.

### Setup Redis

**Local Development:**
```bash
# Linux/Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis-server

# macOS
brew install redis
brew services start redis

# Verify Redis is running
redis-cli ping
# Expected output: PONG
```

**Production/Staging:**
```bash
# Check if Redis is running
redis-cli ping

# Start Redis if not running
sudo systemctl start redis-server
```

### Environment Variables

Add these to your `.env` file:

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0         # Redis connection URL
REDIS_MAX_CONNECTIONS=10                   # Maximum connections in the pool
REDIS_SOCKET_TIMEOUT=5                     # Socket timeout in seconds
REDIS_ENABLED=true                         # Set to false to disable Redis (fallback to in-memory)
```

### Graceful Degradation

If Redis is unavailable, the rate limiter automatically falls back to in-memory rate limiting. However, this means rate limits will NOT be shared across multiple PM2 instances. For production deployments with multiple instances, Redis must be running.

### Testing Redis Rate Limiting

```bash
# Run Redis rate limiting tests
uv run pytest tests/test_api/test_redis_rate_limiting.py -v

# Check Redis keys being used
redis-cli KEYS "ratelimit:*"

# Monitor Redis in real-time
redis-cli MONITOR
```

### Troubleshooting

**Problem: Tests failing with Redis connection errors**
```bash
# Check if Redis is running
redis-cli ping

# If not running, start it
sudo systemctl start redis-server
```

**Problem: Rate limiting not working across PM2 instances**
- Verify `REDIS_ENABLED=true` in `.env`
- Check Redis connection URL is correct
- Verify Redis is accessible from all PM2 instances
- Check logs for Redis connection errors

**Problem: Redis memory usage growing**
- Rate limit keys automatically expire after the time window
- Check key expiration: `redis-cli TTL ratelimit:endpoint:ip`
- Manual cleanup (TEST ONLY): `redis-cli FLUSHDB`

## API Documentation

For detailed API documentation, please refer to:

- [API Authentication Endpoints](../docs/api-auth-endpoints.md) - Authentication API documentation
- [API Profile Endpoints](../docs/api-profile-endpoints.md) - Profile management API documentation
- [API Book Endpoints](../docs/api-book-endpoints.md) - Book management API documentation
- [API Chapter Tabs](../docs/api-chapter-tabs.md) - Chapter tabs API documentation
- [API Question Endpoints](../docs/api-question-endpoints.md) - Question system API documentation

These documents provide comprehensive information about available endpoints, request/response formats, and authentication requirements.

## MongoDB Connection Pooling

This application uses production-ready MongoDB connection pooling configured for high availability and performance. The configuration in `app/db/base.py` includes:

### Pool Configuration

```python
maxPoolSize=50              # Maximum connections in the pool
minPoolSize=10              # Minimum connections kept warm
serverSelectionTimeoutMS=5000   # Fast failure detection (5 seconds)
waitQueueTimeoutMS=5000     # Prevents connection starvation (5 seconds)
maxIdleTimeMS=60000         # Clean up idle connections (60 seconds)
```

### Rationale

- **maxPoolSize=50**: Handles production load with 500+ concurrent operations
  - Tested with 500 concurrent operations (see load tests)
  - Prevents connection exhaustion under heavy traffic
  - For MongoDB Atlas sharded clusters, each shard gets its own pool

- **minPoolSize=10**: Maintains warm connections to reduce latency
  - Eliminates connection handshake overhead for common operations
  - Balances resource usage with performance

- **serverSelectionTimeoutMS=5000**: Fast failure detection
  - Quickly detects unreachable MongoDB servers
  - Fails fast instead of hanging indefinitely
  - Improves user experience with timely error responses

- **waitQueueTimeoutMS=5000**: Prevents connection starvation
  - Under heavy load, requests fail fast rather than queuing indefinitely
  - Allows load balancers and retry logic to redistribute requests
  - Prevents cascading failures

- **maxIdleTimeMS=60000**: Resource optimization
  - Closes connections idle for more than 60 seconds
  - Frees server resources during low-traffic periods
  - Automatically scales down during off-peak hours

### Connection Pool Monitoring

The application includes comprehensive connection pool monitoring:

- **INFO level**: Connection creation, closure, and pool lifecycle events
- **DEBUG level**: Connection checkout/checkin events for debugging
- **WARNING level**: Checkout failures and pool clearing events

To enable detailed monitoring, set log level to DEBUG in your environment:

```bash
LOG_LEVEL=DEBUG uv run uvicorn app.main:app --reload
```

### Load Testing

Run connection pool load tests to verify behavior:

```bash
# Run all load tests
uv run pytest tests/load_tests/test_mongodb_connection_pool.py -v

# Run with detailed output
uv run pytest tests/load_tests/test_mongodb_connection_pool.py -v -s

# Run specific test
uv run pytest tests/load_tests/test_mongodb_connection_pool.py::test_connection_pool_under_load -v
```

**Load test validation:**
- 500 concurrent operations complete successfully
- No connection exhaustion under load
- Timeouts trigger within 5 seconds as configured
- Pool respects maxPoolSize limits
- Minimal checkout failures (<5% for cloud MongoDB)

### Troubleshooting Connection Issues

**Problem: "Connection timeout" errors**
- Check MongoDB server is accessible
- Verify `DATABASE_URI` in `.env` file
- Ensure firewall allows connections
- Check MongoDB Atlas IP whitelist (if using Atlas)

**Problem: "Too many connections" errors**
- Current maxPoolSize is 50 per shard
- For sharded clusters, multiply by number of shards
- Consider increasing maxPoolSize if consistently hitting limit
- Review application for connection leaks (use monitoring)

**Problem: Slow queries**
- Check connection pool utilization in logs
- If pool is exhausted, may need to increase maxPoolSize
- Review query performance and indexing
- Consider connection pooling at load balancer level

**Problem: Connection checkout failures**
- Small number (<5%) is normal for cloud MongoDB
- If >10%, investigate network latency
- Check MongoDB server health and load
- Consider increasing waitQueueTimeoutMS for slow networks

### MongoDB Atlas Sharded Clusters

When using MongoDB Atlas sharded clusters (replica sets):
- Each shard maintains its own connection pool
- Total connections = maxPoolSize × number of shards
- Example: 3 shards × 50 connections = 150 total connections
- Monitor connections per shard in MongoDB Atlas dashboard

## Key Features

- **Transaction-based TOC Updates**: Atomic operations for Table of Contents modifications
- **Optimistic Locking**: Version control to prevent concurrent modification conflicts
- **Audit Logging**: Comprehensive activity tracking for all operations
- **Chapter Tab Management**: Advanced chapter organization with tab states
- **Question System**: Interview-style question generation and management
- **Production-Ready Connection Pooling**: Handles 500+ concurrent operations with monitoring

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.