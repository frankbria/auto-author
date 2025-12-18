#!/usr/bin/env python3
import os
os.environ['OPENAI_AUTOAUTHOR_API_KEY'] = 'test-key'
os.environ['BETTER_AUTH_SECRET'] = 'test-secret-key-for-better-auth'
os.environ['BETTER_AUTH_URL'] = 'http://localhost:3000'
os.environ['BETTER_AUTH_ISSUER'] = 'better-auth'

try:
    from app.core.config import settings
    print("Settings loaded successfully!")
    print(f"BACKEND_CORS_ORIGINS: {settings.BACKEND_CORS_ORIGINS}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
