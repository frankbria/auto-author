#!/usr/bin/env python3
import os
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['CLERK_API_KEY'] = 'test-key'
os.environ['CLERK_JWT_PUBLIC_KEY'] = 'test-key'
os.environ['CLERK_FRONTEND_API'] = 'test.clerk.com'
os.environ['CLERK_BACKEND_API'] = 'api.clerk.com'

try:
    from app.core.config import settings
    print("Settings loaded successfully!")
    print(f"BACKEND_CORS_ORIGINS: {settings.BACKEND_CORS_ORIGINS}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()