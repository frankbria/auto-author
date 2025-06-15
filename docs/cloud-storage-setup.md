# Cloud Storage Setup Guide

## Overview

Auto Author supports multiple storage options for uploaded files (book covers, etc.):
1. **Cloudinary** (Recommended for images) - Automatic image optimization and CDN
2. **AWS S3** - General purpose cloud storage
3. **Local Storage** (Default) - For development only

The application automatically detects which service to use based on environment variables.

## Priority Order

The application checks for credentials in this order:
1. Cloudinary (best for images with automatic optimization)
2. AWS S3 (good general purpose storage)
3. Local filesystem (fallback for development)

## Option 1: Cloudinary Setup (Recommended)

### Step 1: Create Cloudinary Account
1. Sign up at [Cloudinary](https://cloudinary.com/)
2. Go to your Dashboard
3. Find your credentials in the "Account Details" section

### Step 2: Configure Environment Variables
Add to your backend `.env` file:
```env
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=your-api-secret
```

### Benefits:
- Automatic image optimization
- Built-in CDN for fast delivery
- On-the-fly transformations
- No need to manage storage infrastructure

## Option 2: AWS S3 Setup

### Step 1: Create S3 Bucket
1. Go to [AWS S3 Console](https://console.aws.amazon.com/s3/)
2. Create a new bucket (e.g., `auto-author-uploads`)
3. Configure public access settings if needed

### Step 2: Configure Environment Variables
Add to your backend `.env` file:
```env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
AWS_S3_BUCKET=auto-author-uploads
```

### Step 3: Configure Bucket Permissions
Ensure your IAM user has these permissions:
- `s3:PutObject`
- `s3:GetObject`
- `s3:DeleteObject`
- `s3:ListBucket`

## Option 3: Local Storage (Development Only)

If no cloud credentials are provided:
- Files are saved to `backend/uploads/` directory
- Served via FastAPI static files mount
- URLs will be like `/uploads/cover_images/filename.jpg`

**Note**: Local storage is not recommended for production as files will be lost if the server is recreated.

## Testing Your Configuration

1. Start the backend server:
   ```bash
   cd backend
   uv run uvicorn app.main:app --reload
   ```

2. Check the logs for storage configuration:
   - "Using Cloudinary for image storage" - Cloudinary active
   - "Using AWS S3 for image storage" - S3 active
   - "Using local file storage for uploads" - Local storage active

3. Test by uploading a book cover image through the frontend

## File Organization

### Cloudinary Structure:
```
cover_images/
├── {book_id}/
│   ├── {unique_id}.jpg
│   └── thumbnails/
│       └── {unique_id}_thumb.jpg
```

### S3 Structure:
```
bucket-name/
├── cover_images/
│   ├── {book_id}/
│   │   ├── {unique_id}.jpg
│   │   └── thumbnails/
│   │       └── {unique_id}_thumb.jpg
```

## Image Processing

Regardless of storage provider:
- Maximum file size: 5MB
- Supported formats: JPEG, PNG, WebP, GIF
- Main image: Max 1200x1800 pixels (auto-resized if larger)
- Thumbnail: 300x450 pixels (auto-generated)
- Quality: 85% JPEG compression

## Cost Considerations

### Cloudinary:
- Free tier: 25GB storage, 25GB bandwidth/month
- Generous for most small to medium applications

### AWS S3:
- Pay per GB stored (~$0.023/GB/month)
- Pay per request and bandwidth
- Generally very affordable for images

## Troubleshooting

### Images Not Uploading:
1. Check environment variables are set correctly
2. Verify credentials have proper permissions
3. Check server logs for specific error messages

### Images Not Displaying:
1. For local storage, ensure static files are mounted
2. For cloud storage, check if URLs are being generated correctly
3. Verify CORS settings if accessing from different domain

### Switching Providers:
- Old images remain at their original URLs
- New uploads will use the new provider
- Consider migrating old images if switching permanently

---

*Last Updated: January 2025*