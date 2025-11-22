# Clerk Webhook 401 Error - Nginx Header Fix

**Date**: 2025-11-22
**Issue**: Clerk webhooks failing with 401 Unauthorized
**Root Cause**: Nginx proxy not passing Svix authentication headers to backend

## Problem Analysis

Clerk sends webhooks with custom Svix headers for signature verification:
- `svix-id`
- `svix-timestamp`
- `svix-signature`

The nginx proxy configuration for `api.dev.autoauthor.app` was not passing these custom headers to the FastAPI backend, causing the webhook endpoint's signature verification to fail with "Missing required Svix headers".

## Evidence

From backend logs:
```
2025-11-22 22:26:00,186 - Request started: POST /api/v1/webhooks/clerk from 54.216.8.72
2025-11-22 22:26:00,187 - Request completed: POST /api/v1/webhooks/clerk - Status: 401, Took: 0.81ms
```

Test without Svix headers returns:
```json
{"detail":"Missing required Svix headers"}
```

## Solution

Update nginx configuration to pass all headers through to the backend. Add to the `api.dev.autoauthor.app` server block:

```nginx
server {
    server_name api.dev.autoauthor.app;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;

        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CRITICAL: Pass all headers through (including Svix headers for webhooks)
        proxy_pass_request_headers on;
        underscores_in_headers on;  # Allow headers with underscores if needed
    }
}
```

## Implementation Steps

1. **Backup current nginx config**:
   ```bash
   sudo cp /etc/nginx/sites-enabled/api.dev.autoauthor.app /etc/nginx/sites-enabled/api.dev.autoauthor.app.backup
   ```

2. **Edit nginx config**:
   ```bash
   sudo nano /etc/nginx/sites-enabled/api.dev.autoauthor.app
   ```

3. **Add header passing directives** to the `location /` block

4. **Test nginx configuration**:
   ```bash
   sudo nginx -t
   ```

5. **Reload nginx**:
   ```bash
   sudo systemctl reload nginx
   ```

6. **Test webhook from Clerk dashboard**:
   - Go to Clerk Dashboard → Webhooks
   - Resend a test webhook
   - Verify 200 response

## Verification

After fix:
- Clerk webhook requests should return 200 OK
- Backend logs should show successful webhook processing
- User sync should work automatically

## Related Files

- nginx config: `/etc/nginx/sites-enabled/api.dev.autoauthor.app`
- Webhook endpoint: `backend/app/api/endpoints/webhooks.py`
- Signature verification: `backend/app/api/endpoints/webhooks.py:14-57`
