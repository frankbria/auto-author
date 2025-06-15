# AWS Transcribe Setup Guide

## Overview

Auto Author uses AWS Transcribe for converting speech to text in the voice input feature. This guide will help you set up AWS Transcribe for your development environment.

## Prerequisites

1. AWS Account
2. AWS IAM user with appropriate permissions
3. S3 bucket for temporary audio storage

## Step 1: Create an S3 Bucket

AWS Transcribe requires audio files to be stored in S3. Create a bucket for temporary audio storage:

1. Go to [AWS S3 Console](https://console.aws.amazon.com/s3/)
2. Click "Create bucket"
3. Name it something like `auto-author-transcriptions`
4. Choose your preferred region (e.g., `us-east-1`)
5. Keep default settings for now
6. Create the bucket

## Step 2: Create IAM User and Permissions

1. Go to [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Click "Users" → "Add users"
3. Username: `auto-author-transcribe`
4. Select "Access key - Programmatic access"
5. Click "Next: Permissions"
6. Click "Attach existing policies directly"
7. Search and select these policies:
   - `AmazonTranscribeFullAccess`
   - `AmazonS3FullAccess` (or create a custom policy for just your bucket)

### Custom S3 Policy (Recommended)

For better security, create a custom policy that only allows access to your specific bucket:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::auto-author-transcriptions/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::auto-author-transcriptions"
        }
    ]
}
```

## Step 3: Configure Environment Variables

Add the following to your backend `.env` file:

```env
# AWS Settings for Transcription
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1  # or your preferred region
AWS_S3_BUCKET=auto-author-transcriptions  # your bucket name
```

## Step 4: Update the Transcription Service

In the file `/backend/app/services/transcription_service_aws.py`, update the bucket name:

```python
self.bucket_name = os.getenv('AWS_S3_BUCKET', 'auto-author-transcriptions')
```

## Step 5: Install Dependencies

```bash
cd backend
source .venv/bin/activate  # or use 'uv'
uv pip install boto3
```

## Step 6: Test the Integration

1. Start the backend server:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

2. The server logs should show:
   ```
   INFO: Using AWS Transcribe for speech-to-text
   ```

3. Test voice input in the frontend application

## Supported Audio Formats

AWS Transcribe supports:
- WebM (browser default)
- MP3
- MP4
- WAV
- FLAC

## Cost Considerations

AWS Transcribe pricing:
- First 60 minutes per month: Free
- After that: ~$0.024 per minute
- Additional costs for S3 storage (minimal)

## Troubleshooting

### "Access Denied" Errors
- Verify IAM permissions include both Transcribe and S3 access
- Check bucket name matches in code and environment variables
- Ensure region is correct

### "Invalid Audio Format" Errors
- AWS Transcribe has specific requirements for audio encoding
- The service automatically handles WebM from browsers
- For other formats, ensure proper encoding

### Slow Transcription
- AWS Transcribe is not real-time; expect 2-10 seconds for short clips
- For real-time needs, consider AWS Transcribe Streaming (requires WebSocket implementation)

## Alternative Services

If you prefer other providers:

### Google Cloud Speech-to-Text
1. Install: `pip install google-cloud-speech`
2. Set up credentials and update transcription service

### Azure Speech Services
1. Install: `pip install azure-cognitiveservices-speech`
2. Add Azure credentials to `.env`
3. Update transcription service

### OpenAI Whisper API
1. Uses existing OpenAI API key
2. Simple integration but may be slower
3. Good accuracy for various languages

## Security Notes

- Never commit AWS credentials to version control
- Use IAM roles in production (not access keys)
- Regularly rotate access keys
- Monitor AWS CloudTrail for usage
- Set up S3 lifecycle policies to auto-delete old audio files

---

*Last Updated: January 2025*