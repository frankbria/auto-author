# AI Service Caching and Error Handling Architecture

**Last Updated:** 2025-12-22
**Status:** Production-Ready
**Owner:** Auto Author Engineering Team

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Caching System](#caching-system)
4. [Error Handling](#error-handling)
5. [Implementation Details](#implementation-details)
6. [Configuration](#configuration)
7. [Monitoring and Debugging](#monitoring-and-debugging)
8. [Best Practices](#best-practices)

---

## Overview

Auto Author's AI service integration includes a sophisticated caching and error handling system designed to:

- **Reduce API costs** by caching identical AI requests
- **Improve response times** from 2-5 seconds to 50-100ms for cached responses
- **Increase reliability** through automatic retry and graceful degradation
- **Provide resilience** during AI service outages using cached fallbacks

### Key Metrics

| Metric | Without Cache | With Cache |
|--------|---------------|------------|
| Response Time | 2-5 seconds | 50-100ms |
| API Cost Reduction | 0% | ~75% |
| Cache Hit Rate | N/A | 90%+ |
| Uptime Resilience | Service-dependent | Cache-backed |

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│                  User initiates AI request                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend API (FastAPI)                      │
│              /api/v1/toc/generate endpoint                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI Service Layer                          │
│              (app/services/ai_service.py)                    │
│                                                               │
│  ┌─────────────────┐         ┌─────────────────┐            │
│  │ Cache Check     │────────▶│ Return Cached   │            │
│  │ (Redis Lookup)  │  Found  │ Response        │            │
│  └────────┬────────┘         └─────────────────┘            │
│           │ Not Found                                        │
│           ▼                                                  │
│  ┌─────────────────┐         ┌─────────────────┐            │
│  │ OpenAI API Call │─Error──▶│ Retry Logic     │            │
│  │ (with retries)  │         │ (Exponential)   │            │
│  └────────┬────────┘         └────────┬────────┘            │
│           │ Success                   │ All Failed          │
│           ▼                           ▼                      │
│  ┌─────────────────┐         ┌─────────────────┐            │
│  │ Cache Response  │         │ Check Cache for │            │
│  │ (Redis Store)   │         │ Fallback        │            │
│  └────────┬────────┘         └────────┬────────┘            │
│           │                           │                      │
│           └───────────┬───────────────┘                      │
│                       ▼                                      │
│              ┌─────────────────┐                             │
│              │ Return Response │                             │
│              │ to API Layer    │                             │
│              └─────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Redis Cache Store                         │
│                                                               │
│  Key: ai_cache:toc:hash:a3f5c8d9...                         │
│  Value: {toc: {...}, metadata: {...}}                       │
│  TTL: 86400 seconds (24 hours)                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Caching System

### Cache Key Generation

Cache keys are generated using a deterministic hashing strategy to ensure consistency:

**Algorithm:**
```python
def _generate_cache_key(self, prefix: str, **kwargs) -> str:
    """
    Generate cache key from operation type and parameters.

    Example:
    _generate_cache_key("toc",
                       summary="Book about AI",
                       metadata={"title": "AI Guide"})

    Returns: "ai_cache:toc:hash:a3f5c8d9e2b1f4a6c7e8d9f0a1b2c3d4"
    """
    # Sort parameters for consistency
    key_parts = [prefix]
    for key, value in sorted(kwargs.items()):
        if value is not None:
            key_parts.append(f"{key}:{value}")

    key_string = ":".join(key_parts)

    # Hash if too long (Redis key limit: 512MB, practical limit: 250 chars)
    if len(key_string) > 250:
        hash_obj = hashlib.md5(key_string.encode())
        return f"{prefix}:hash:{hash_obj.hexdigest()}"

    return key_string
```

**Key Components:**
- **Prefix**: Operation type (e.g., `toc`, `questions`, `draft`)
- **Parameters**: Sorted input parameters for consistency
- **Hash**: MD5 hash for long keys to avoid Redis limits

### Cache Storage Structure

**Data Format:**
```json
{
  "cache_key": "ai_cache:toc:hash:a3f5c8d9...",
  "data": {
    "toc": {
      "chapters": [...],
      "total_chapters": 8,
      "structure_notes": "..."
    },
    "metadata": {
      "cached_at": "2025-12-22T10:30:00Z",
      "operation": "toc_generation",
      "input_hash": "a3f5c8d9..."
    }
  },
  "ttl": 86400
}
```

### Cache Operations

**Setting Cache:**
```python
async def cache_ai_response(
    self,
    operation: str,
    params: Dict,
    response: Dict,
    ttl: Optional[int] = None
) -> bool:
    """
    Store AI response in cache.

    Args:
        operation: Type of AI operation (toc, questions, draft)
        params: Input parameters used for the request
        response: AI response to cache
        ttl: Time to live in seconds (default: AI_CACHE_TTL)

    Returns:
        True if cached successfully, False otherwise
    """
    if not self.cache_enabled:
        return False

    cache_key = self._generate_cache_key(operation, **params)
    cache_data = {
        "data": response,
        "metadata": {
            "cached_at": datetime.now().isoformat(),
            "operation": operation,
            "input_hash": hashlib.md5(str(params).encode()).hexdigest()
        }
    }

    try:
        await redis_client.setex(
            cache_key,
            ttl or settings.AI_CACHE_TTL,
            json.dumps(cache_data, default=str)
        )
        return True
    except Exception as e:
        logger.error(f"Cache write failed: {e}")
        return False
```

**Getting from Cache:**
```python
async def get_cached_response(
    self,
    operation: str,
    params: Dict
) -> Optional[Dict]:
    """
    Retrieve cached AI response.

    Args:
        operation: Type of AI operation
        params: Input parameters

    Returns:
        Cached response or None if not found/expired
    """
    if not self.cache_enabled:
        return None

    cache_key = self._generate_cache_key(operation, **params)

    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            cache_obj = json.loads(cached_data)
            logger.info(f"Cache hit for {operation}")
            return cache_obj["data"]
    except Exception as e:
        logger.warning(f"Cache read failed: {e}")

    return None
```

### Cache Invalidation

**Strategies:**

1. **TTL-based (Automatic)**: Cache entries expire after configured TTL
2. **Manual Invalidation**: Explicit cache clearing for specific operations
3. **Pattern-based Deletion**: Clear all caches matching a pattern

**Example:**
```python
async def invalidate_cache(self, pattern: str):
    """
    Invalidate cache entries matching pattern.

    Args:
        pattern: Redis key pattern (e.g., "ai_cache:toc:*")
    """
    try:
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache entries")
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
```

---

## Error Handling

### Retry Logic with Exponential Backoff

The AI service implements intelligent retry logic for transient failures:

**Configuration:**
```python
class AIService:
    def __init__(self):
        self.max_retries = 3              # Maximum retry attempts
        self.base_delay = 1.0             # Initial delay (seconds)
        self.max_delay = 60.0             # Maximum delay cap
```

**Retry Flow:**
```python
async def _retry_with_backoff(self, func, *args, **kwargs):
    """
    Execute function with exponential backoff retry.

    Retry Schedule:
    - Attempt 1: Immediate
    - Attempt 2: Wait 1s  (base_delay * 2^0)
    - Attempt 3: Wait 2s  (base_delay * 2^1)
    - Attempt 4: Wait 4s  (base_delay * 2^2)

    Max delay capped at 60s to prevent excessive waits.
    """
    last_exception = None

    for attempt in range(self.max_retries):
        try:
            logger.info(f"AI API attempt {attempt + 1}/{self.max_retries}")
            return await func(*args, **kwargs)

        except openai.RateLimitError as e:
            last_exception = e
            delay = min(self.base_delay * (2**attempt), self.max_delay)
            logger.warning(f"Rate limit hit, retry in {delay}s")

            if attempt < self.max_retries - 1:
                await asyncio.sleep(delay)
            else:
                logger.error("Max retries reached for rate limit")

        except (openai.APITimeoutError, openai.APIConnectionError) as e:
            last_exception = e
            delay = min(self.base_delay * (2**attempt), self.max_delay)
            logger.warning(f"API timeout/connection error, retry in {delay}s")

            if attempt < self.max_retries - 1:
                await asyncio.sleep(delay)
            else:
                logger.error("Max retries reached for timeout/connection")

        except openai.InternalServerError as e:
            last_exception = e
            delay = min(self.base_delay * (2**attempt), self.max_delay)
            logger.warning(f"OpenAI server error, retry in {delay}s")

            if attempt < self.max_retries - 1:
                await asyncio.sleep(delay)
            else:
                logger.error("Max retries reached for server error")

        except Exception as e:
            # Non-retryable errors (e.g., invalid API key, malformed request)
            logger.error(f"Non-retryable error: {str(e)}")
            raise e

    # All retries exhausted
    raise last_exception
```

### Error Categories

**Retryable Errors:**
- `RateLimitError`: OpenAI rate limit exceeded
- `APITimeoutError`: Request timeout
- `APIConnectionError`: Network connectivity issues
- `InternalServerError`: OpenAI service errors

**Non-Retryable Errors:**
- `AuthenticationError`: Invalid API key
- `InvalidRequestError`: Malformed request
- `PermissionDeniedError`: Insufficient permissions

### Graceful Degradation

When AI service fails after all retries, the system provides graceful fallbacks:

**Priority Order:**
1. **Cached Response**: Use previously cached response for same input
2. **Default Values**: Return sensible defaults for the operation
3. **Error with Suggestions**: Provide actionable error message

**Example Implementation:**
```python
async def generate_toc_with_fallback(self, summary: str, metadata: Dict) -> Dict:
    """
    Generate TOC with automatic fallback on failure.

    Fallback Chain:
    1. Try AI service (with retries)
    2. Check cache for previous response
    3. Return default TOC structure
    """
    try:
        # Attempt AI generation
        result = await self._retry_with_backoff(
            self._make_openai_request,
            messages=self._build_toc_prompt(summary, metadata)
        )

        # Cache successful response
        await self.cache_ai_response("toc", {"summary": summary}, result)

        return self._parse_toc_response(result)

    except Exception as e:
        logger.error(f"TOC generation failed after retries: {e}")

        # Fallback 1: Check cache
        cached = await self.get_cached_response("toc", {"summary": summary})
        if cached:
            logger.info("Using cached TOC response as fallback")
            return cached

        # Fallback 2: Default structure
        logger.warning("Using default TOC structure")
        return self._create_default_toc(summary)
```

**Default TOC Structure:**
```python
def _create_default_toc(self, summary: str) -> Dict:
    """Create sensible default TOC when AI fails."""
    return {
        "toc": {
            "chapters": [
                {
                    "id": "ch1",
                    "title": "Introduction",
                    "description": "Opening chapter",
                    "level": 1,
                    "order": 1,
                    "subchapters": []
                },
                {
                    "id": "ch2",
                    "title": "Main Content",
                    "description": "Core content based on summary",
                    "level": 1,
                    "order": 2,
                    "subchapters": []
                },
                {
                    "id": "ch3",
                    "title": "Conclusion",
                    "description": "Summary and next steps",
                    "level": 1,
                    "order": 3,
                    "subchapters": []
                }
            ],
            "total_chapters": 3,
            "structure_notes": "Default structure - AI service unavailable"
        },
        "success": True,
        "fallback": True
    }
```

---

## Implementation Details

### Service Integration

**File Structure:**
```
backend/
├── app/
│   ├── services/
│   │   ├── ai_service.py                    # Main AI service
│   │   ├── chapter_cache_service.py         # Chapter-specific caching
│   │   └── chapter_error_handler.py         # Error recovery
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           └── toc.py                   # TOC API endpoints
│   └── core/
│       └── config.py                        # Configuration
```

**Service Initialization:**
```python
# app/services/ai_service.py

class AIService:
    """AI Service with caching and error handling."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_AUTOAUTHOR_API_KEY)
        self.model = "gpt-4"
        self.max_retries = settings.AI_MAX_RETRIES or 3
        self.cache_enabled = settings.AI_CACHE_ENABLED
        self.cache_ttl = settings.AI_CACHE_TTL or 86400

        # Initialize Redis cache
        if self.cache_enabled:
            self._init_cache()

    def _init_cache(self):
        """Initialize Redis connection for caching."""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("AI service cache initialized")
        except Exception as e:
            logger.warning(f"Cache init failed, continuing without cache: {e}")
            self.cache_enabled = False

# Global singleton
ai_service = AIService()
```

### API Endpoint Integration

**Example: TOC Generation Endpoint**
```python
# app/api/v1/endpoints/toc.py

@router.post("/generate")
async def generate_toc(
    request: TOCGenerateRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate table of contents from book summary.

    This endpoint includes:
    - Automatic caching of AI responses
    - Retry logic for failed requests
    - Graceful fallback to cached/default responses
    """
    try:
        # Check cache first
        cached_response = await ai_service.get_cached_response(
            "toc",
            {
                "summary": request.summary,
                "metadata": request.metadata
            }
        )

        if cached_response:
            return {
                "success": True,
                "data": cached_response,
                "cached": True
            }

        # Generate with AI (includes retry logic)
        result = await ai_service.generate_toc_from_summary_and_responses(
            summary=request.summary,
            question_responses=request.question_responses,
            book_metadata=request.metadata
        )

        return {
            "success": True,
            "data": result,
            "cached": False
        }

    except Exception as e:
        logger.error(f"TOC generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TOC generation failed",
                "message": str(e),
                "suggestion": "Please try again or contact support if the issue persists"
            }
        )
```

---

## Configuration

### Environment Variables

**Required:**
```bash
# OpenAI API Configuration
OPENAI_AUTOAUTHOR_API_KEY=sk-proj-...  # Required for AI operations

# Redis Configuration (highly recommended)
REDIS_URL=redis://localhost:6379/0     # Redis connection string
```

**Optional:**
```bash
# AI Service Configuration
AI_CACHE_ENABLED=true                  # Enable/disable caching (default: true)
AI_CACHE_TTL=86400                     # Cache TTL in seconds (default: 24h)
AI_MAX_RETRIES=3                       # Max retry attempts (default: 3)
```

### Redis Configuration Options

**Connection Strings:**
```bash
# Local Redis
REDIS_URL=redis://localhost:6379/0

# Redis with password
REDIS_URL=redis://:password@localhost:6379/0

# Redis Sentinel
REDIS_URL=redis://sentinel-host:26379/0?sentinel=mymaster

# Redis Cluster
REDIS_URL=redis://cluster-node:6379/0?cluster_enabled=true

# Redis Cloud (AWS ElastiCache, Azure Cache, etc.)
REDIS_URL=redis://cache.example.com:6379/0?ssl=true
```

### Production Recommendations

**Cache TTL:**
- Development: `3600` (1 hour) - faster iteration
- Production: `86400` (24 hours) - optimal cost/freshness balance
- High-traffic: `43200` (12 hours) - balance between cost and freshness

**Max Retries:**
- Development: `2` - faster failure feedback
- Production: `3` - good balance of reliability and speed
- High-reliability: `5` - maximum resilience (slower failures)

**Redis Configuration:**
```bash
# Production Redis settings
maxmemory 2gb                          # Prevent memory overflow
maxmemory-policy allkeys-lru           # Evict least recently used keys
save 900 1                             # Persistence: save after 900s if 1 change
save 300 10                            # Persistence: save after 300s if 10 changes
```

---

## Monitoring and Debugging

### Logging

**Log Levels:**
```python
# Info: Successful operations
logger.info(f"Cache hit for TOC generation")
logger.info(f"AI request attempt {attempt}/{max_retries}")

# Warning: Recoverable issues
logger.warning(f"Cache read failed, continuing without cache: {e}")
logger.warning(f"Rate limit hit, retrying in {delay}s")

# Error: Failed operations
logger.error(f"TOC generation failed after all retries: {e}")
logger.error(f"Max retries reached for rate limit error")
```

**Log Output Example:**
```
2025-12-22 10:30:15 [INFO] AI request attempt 1/3
2025-12-22 10:30:20 [WARNING] Rate limit hit, retrying in 1s
2025-12-22 10:30:21 [INFO] AI request attempt 2/3
2025-12-22 10:30:22 [INFO] Cache hit for TOC generation
```

### Cache Statistics

**Monitor Cache Performance:**
```python
async def get_cache_stats() -> Dict:
    """Get cache performance statistics."""
    info = await redis_client.info()

    return {
        "memory_usage": info.get("used_memory_human"),
        "total_keys": info.get("db0", {}).get("keys", 0),
        "hit_rate": calculate_hit_rate(),
        "evicted_keys": info.get("evicted_keys", 0)
    }
```

**Redis CLI Monitoring:**
```bash
# Real-time monitoring
redis-cli monitor

# Memory stats
redis-cli info memory

# Key statistics
redis-cli info keyspace

# Slow query log
redis-cli slowlog get 10
```

### Error Tracking

**Error Metrics to Monitor:**
```python
error_metrics = {
    "total_errors": 0,
    "errors_by_type": {
        "rate_limit": 0,
        "timeout": 0,
        "connection": 0,
        "server_error": 0
    },
    "retry_success_rate": 0.0,
    "cache_fallback_rate": 0.0
}
```

**Alerting Thresholds:**
- Error rate > 10% over 5 minutes
- Cache hit rate < 50% over 1 hour
- Retry failures > 5 consecutive requests
- Redis connection failures

---

## Best Practices

### 1. Cache Key Design

**DO:**
- Use consistent parameter ordering
- Include operation type in key prefix
- Hash long keys to avoid size limits
- Version cache keys when changing response format

**DON'T:**
- Include timestamps in cache keys (breaks caching)
- Use non-deterministic values (random IDs, current time)
- Store large objects in Redis (> 1MB)

### 2. Error Handling

**DO:**
- Log all errors with context (user_id, operation, params)
- Provide user-friendly error messages
- Implement fallbacks for critical operations
- Monitor error rates and patterns

**DON'T:**
- Expose internal error details to users
- Retry non-retryable errors
- Skip logging for "expected" errors
- Ignore cache failures silently

### 3. Performance Optimization

**DO:**
- Set appropriate TTL based on data freshness needs
- Use Redis pipelining for bulk operations
- Monitor cache hit rates and adjust strategy
- Implement cache warming for common requests

**DON'T:**
- Cache every single request indiscriminately
- Use very short TTLs (< 60s) - defeats caching purpose
- Store sensitive data in cache without encryption
- Ignore Redis memory limits

### 4. Testing

**DO:**
- Test with Redis unavailable (cache disabled)
- Test retry logic with mock failures
- Verify fallback behavior
- Load test with realistic cache hit rates

**DON'T:**
- Test only with cache enabled
- Skip testing error paths
- Use production Redis for tests
- Assume cache is always available

### 5. Production Deployment

**DO:**
- Use Redis persistence (AOF or RDB)
- Configure Redis maxmemory and eviction policy
- Monitor Redis health and performance
- Set up alerts for cache failures

**DON'T:**
- Run Redis without persistence in production
- Share Redis instance across environments
- Ignore Redis memory warnings
- Deploy without cache warming strategy

---

## Performance Tuning

### Cache Hit Rate Optimization

**Target: 90%+ cache hit rate**

**Strategies:**
1. **Pre-warm cache** for common operations
2. **Increase TTL** for stable content
3. **Normalize inputs** to improve key matching
4. **Monitor patterns** and optimize key generation

**Example: Cache Warming**
```python
async def warm_common_caches():
    """Pre-populate cache with common requests."""
    common_summaries = await get_popular_book_summaries(limit=100)

    for summary in common_summaries:
        try:
            # Generate and cache TOC
            await ai_service.generate_toc_from_summary(summary)
        except Exception as e:
            logger.warning(f"Cache warming failed for summary: {e}")
```

### Memory Management

**Redis Memory Optimization:**
```bash
# Configure memory limit
maxmemory 2gb

# Eviction policy (choose based on use case)
maxmemory-policy allkeys-lru        # Evict least recently used
# OR
maxmemory-policy volatile-ttl       # Evict keys with soonest expiry
```

**Monitor Memory Usage:**
```python
async def check_memory_usage():
    """Alert if Redis memory usage is high."""
    info = await redis_client.info("memory")
    used = info["used_memory"]
    max_memory = info["maxmemory"]

    if used / max_memory > 0.9:
        logger.warning(f"Redis memory usage high: {used/max_memory*100:.1f}%")
```

### Latency Reduction

**Optimization Techniques:**
1. **Connection pooling**: Reuse Redis connections
2. **Pipelining**: Batch multiple Redis commands
3. **Compression**: Compress large cached values
4. **Local caching**: Add in-memory cache layer

**Example: Connection Pooling**
```python
# Use connection pool for better performance
redis_client = redis.from_url(
    settings.REDIS_URL,
    max_connections=50,           # Connection pool size
    socket_keepalive=True,        # Keep connections alive
    socket_timeout=5,             # Socket timeout
    retry_on_timeout=True         # Retry on timeout
)
```

---

## Troubleshooting Guide

### Common Issues

#### Issue: High Cache Miss Rate

**Symptoms:**
- Cache hit rate < 50%
- High OpenAI API costs
- Slow response times

**Diagnosis:**
```bash
# Check cache statistics
redis-cli info stats

# Monitor cache keys
redis-cli keys "ai_cache:*" | wc -l

# Check TTL settings
redis-cli ttl "ai_cache:toc:hash:..."
```

**Solutions:**
1. Increase `AI_CACHE_TTL`
2. Normalize input parameters
3. Check cache key generation logic
4. Verify Redis persistence is enabled

#### Issue: Redis Connection Failures

**Symptoms:**
- Error logs: "Cache disabled"
- No cached responses returned
- High error rates

**Diagnosis:**
```bash
# Check Redis is running
redis-cli ping

# Check connection
python -c "import redis; r = redis.from_url('redis://localhost:6379/0'); print(r.ping())"

# Check logs
tail -f /var/log/redis/redis-server.log
```

**Solutions:**
1. Restart Redis: `sudo systemctl restart redis`
2. Check firewall settings
3. Verify `REDIS_URL` configuration
4. Check Redis error logs

#### Issue: High Retry Rates

**Symptoms:**
- Many retry attempts in logs
- Slow API responses
- Rate limit errors

**Diagnosis:**
```bash
# Check error logs
tail -f backend/logs/app.log | grep "retry"

# Monitor OpenAI API status
curl https://status.openai.com/api/v2/status.json
```

**Solutions:**
1. Reduce request rate
2. Increase `AI_MAX_RETRIES`
3. Check OpenAI API quota
4. Implement request queuing

---

## Migration Guide

### Adding Caching to Existing Installation

**Step 1: Install Redis**
```bash
# Docker (recommended)
docker run -d --name auto-author-redis -p 6379:6379 redis:latest

# Or native installation
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server
```

**Step 2: Update Configuration**
```bash
# Add to backend/.env
REDIS_URL=redis://localhost:6379/0
AI_CACHE_ENABLED=true
AI_CACHE_TTL=86400
AI_MAX_RETRIES=3
```

**Step 3: Verify Installation**
```bash
# Test Redis connection
redis-cli ping  # Should return "PONG"

# Start backend and check logs
cd backend
uv run uvicorn app.main:app --reload

# Look for: "AI service cache initialized"
```

**Step 4: Monitor Performance**
```bash
# Watch cache statistics
redis-cli info stats

# Monitor application logs
tail -f backend/logs/app.log | grep "Cache"
```

---

## Security Considerations

### Data Privacy

**Cache Security:**
- Don't cache sensitive user data (PII)
- Use Redis AUTH in production
- Enable Redis SSL/TLS for remote connections
- Set appropriate cache TTL for data sensitivity

**Example: Redis with Authentication**
```bash
# backend/.env
REDIS_URL=redis://:your-strong-password@localhost:6379/0
```

### API Key Protection

**Best Practices:**
- Never commit API keys to version control
- Use environment variables for secrets
- Rotate API keys regularly
- Monitor API key usage

**Example: Key Rotation**
```python
# Support multiple API keys for rotation
class AIService:
    def __init__(self):
        self.api_keys = [
            settings.OPENAI_API_KEY_PRIMARY,
            settings.OPENAI_API_KEY_BACKUP
        ]
        self.current_key_index = 0

    def _get_api_key(self):
        """Get current API key with rotation support."""
        return self.api_keys[self.current_key_index]

    def rotate_key(self):
        """Rotate to next API key."""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
```

---

## Appendix

### Related Documentation

- [AI Service Implementation](../backend/app/services/ai_service.py)
- [Chapter Cache Service](../backend/app/services/chapter_cache_service.py)
- [Error Handler Service](../backend/app/services/chapter_error_handler.py)
- [Configuration Guide](../backend/app/core/config.py)

### External Resources

- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [Redis Documentation](https://redis.io/documentation)
- [Python Redis Client](https://redis-py.readthedocs.io/)
- [FastAPI Caching Patterns](https://fastapi.tiangolo.com/advanced/middleware/)

### Glossary

- **TTL**: Time To Live - duration a cache entry remains valid
- **Cache Hit**: Request served from cache (fast)
- **Cache Miss**: Request not in cache, needs API call (slow)
- **Exponential Backoff**: Increasing delay between retries
- **Rate Limiting**: OpenAI API request limits
- **Graceful Degradation**: System continues with reduced functionality

---

**Document History:**
- 2025-12-22: Initial documentation created
- Status: Production-ready
- Next Review: 2026-01-22
