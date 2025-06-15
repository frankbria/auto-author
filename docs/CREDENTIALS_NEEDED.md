# Credentials Needed for Auto Author

## Backend .env File Configuration

Add these credentials to your `/backend/.env` file:

### 1. Clerk Authentication (REQUIRED)
```env
# From Clerk Dashboard → API Keys
CLERK_API_KEY=sk_test_... or sk_live_...
CLERK_FRONTEND_API=clerk.[your-domain].com
CLERK_BACKEND_API=api.clerk.com

# From Clerk Dashboard → JWT Templates → Default → Public Key
# IMPORTANT: Replace actual newlines with \n
CLERK_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkq...\n-----END PUBLIC KEY-----"

# Optional - only if using webhooks
CLERK_WEBHOOK_SECRET=whsec_...
```

### 2. OpenAI API (REQUIRED - Already Added ✓)
```env
OPENAI_API_KEY=sk-...
```

### 3. AWS Credentials (OPTIONAL - For Voice Transcription)
```env
# For AWS Transcribe speech-to-text
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_S3_BUCKET=auto-author-transcriptions  # Create this bucket first
```

### 4. Cloudinary (OPTIONAL - For Image Storage)
```env
# From Cloudinary Dashboard → Account Details
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

## What's Working Now

With just Clerk and OpenAI keys:
- ✅ User authentication
- ✅ Book creation and management
- ✅ AI-powered TOC generation
- ✅ Question generation for chapters
- ✅ AI draft generation from Q&A
- ✅ Rich text editing
- ✅ Chapter organization with tabs

## What Needs Additional Services

1. **Voice Input** → Needs AWS credentials (or alternatives like Google Cloud Speech)
2. **Cloud Image Storage** → Needs Cloudinary credentials (currently using local storage)
3. **Export (PDF/DOCX)** → No external service needed, just implementation

## Next Steps

1. **For Voice Features**: Add AWS credentials to enable speech-to-text
2. **For Cloud Storage**: Add either AWS S3 or Cloudinary credentials
3. **For Export**: No credentials needed, this is next implementation task

---

The app is functional for core features with just Clerk and OpenAI!
Voice and cloud storage are enhancements that can be added when you have those credentials.