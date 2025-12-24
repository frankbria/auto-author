# Deployment Configuration

## GitHub Secrets Setup

The staging deployment workflow requires the following secrets to be configured in your GitHub repository settings.

### Navigation
Go to: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

---

## Required Secrets

### SSH & Server Access
| Secret | Description | Example |
|--------|-------------|---------|
| `SSH_KEY` | Private SSH key for server access | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `HOST` | Server hostname or IP address | `staging.example.com` or `192.168.1.100` |
| `USER` | SSH username | `deploy` |

### Application URLs
| Secret | Description | Example |
|--------|-------------|---------|
| `API_URL` | Backend API URL | `https://api.dev.autoauthor.app` |
| `FRONTEND_URL` | Frontend application URL | `https://dev.autoauthor.app` |

### Database
| Secret | Description | Example |
|--------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb://user:pass@host:27017` |
| `DATABASE_NAME` | Database name | `auto_author_staging` |

### OpenAI
| Secret | Description | Example |
|--------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-proj-...` |

Get from: https://platform.openai.com/api-keys

### Clerk Authentication
| Secret | Description | Example |
|--------|-------------|---------|
| `CLERK_PUBLISHABLE_KEY` | Clerk publishable key | `pk_test_...` or `pk_live_...` |
| `CLERK_SECRET_KEY` | Clerk secret key | `sk_test_...` or `sk_live_...` |
| `CLERK_API_KEY` | Clerk API key | `sk_test_...` |
| `CLERK_FRONTEND_API` | Clerk frontend API domain | `your-app.clerk.accounts.dev` |
| `CLERK_BACKEND_API` | Clerk backend API | `api.clerk.com` |
| `CLERK_WEBHOOK_SECRET` | Clerk webhook secret | `whsec_...` |

Get from: https://dashboard.clerk.com

---

## Optional Secrets

### AWS (for S3 storage and transcription)
| Secret | Description | Example |
|--------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key ID | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | `wJalrXUtnFEMI/...` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `AWS_S3_BUCKET` | S3 bucket name | `auto-author-uploads` |

Get from: https://console.aws.amazon.com/iam/

### Cloudinary (for image storage)
| Secret | Description | Example |
|--------|-------------|---------|
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | `your-cloud-name` |
| `CLOUDINARY_API_KEY` | Cloudinary API key | `123456789012345` |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | `abcdefghijklmnopqrstuvwxyz` |

Get from: https://console.cloudinary.com/

---

## Verification

After configuring secrets, verify the deployment workflow:

1. **Check workflow file**: `.github/workflows/deploy-staging.yml`
2. **Trigger deployment**: Push to `main` branch or manually trigger workflow
3. **Monitor logs**: GitHub Actions → Deploy to Staging → View logs
4. **Verify health checks**: Workflow includes automated health checks for backend and frontend

---

## Environment Files Created

The deployment workflow automatically creates the following files on the server:

### Backend: `/opt/auto-author/current/backend/.env`
```bash
# Database
DATABASE_URL=<from MONGODB_URI secret>
DATABASE_NAME=<from DATABASE_NAME secret>

# CORS Settings
BACKEND_CORS_ORIGINS=["<FRONTEND_URL>","<API_URL>"]

# OpenAI
OPENAI_AUTOAUTHOR_API_KEY=<from OPENAI_API_KEY secret>

# Clerk Authentication
CLERK_API_KEY=<from CLERK_API_KEY secret>
CLERK_SECRET_KEY=<from CLERK_SECRET_KEY secret>
CLERK_FRONTEND_API=<from CLERK_FRONTEND_API secret>
CLERK_BACKEND_API=<from CLERK_BACKEND_API secret>
CLERK_WEBHOOK_SECRET=<from CLERK_WEBHOOK_SECRET secret>
CLERK_JWT_ALGORITHM=RS256

# API Settings
API_V1_PREFIX=/api/v1

# AWS Settings (Optional)
AWS_ACCESS_KEY_ID=<from AWS_ACCESS_KEY_ID secret>
AWS_SECRET_ACCESS_KEY=<from AWS_SECRET_ACCESS_KEY secret>
AWS_REGION=<from AWS_REGION secret>
AWS_S3_BUCKET=<from AWS_S3_BUCKET secret>

# Cloudinary Settings (Optional)
CLOUDINARY_CLOUD_NAME=<from CLOUDINARY_CLOUD_NAME secret>
CLOUDINARY_API_KEY=<from CLOUDINARY_API_KEY secret>
CLOUDINARY_API_SECRET=<from CLOUDINARY_API_SECRET secret>
```

### Frontend: `/opt/auto-author/current/frontend/.env.production`
```bash
NEXT_PUBLIC_API_URL=<from API_URL secret>
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<from CLERK_PUBLISHABLE_KEY secret>
CLERK_SECRET_KEY=<from CLERK_SECRET_KEY secret>
NEXT_PUBLIC_ENVIRONMENT=staging
PORT=3002
```

---

## Troubleshooting

### Deployment fails with "connection refused"
- Verify `SSH_KEY`, `HOST`, and `USER` secrets are correct
- Ensure SSH key has proper permissions (600)
- Verify server firewall allows SSH connections

### Backend health check fails
- Check MongoDB connection: Verify `MONGODB_URI` is correct
- Check logs: `pm2 logs auto-author-backend`
- Verify `.env` file: `cat /opt/auto-author/current/backend/.env`

### Frontend health check fails
- Check environment variables: `pm2 logs auto-author-frontend`
- Verify build succeeded: Check deployment logs
- Check port 3002 is not blocked: `netstat -tulpn | grep 3002`

### CORS errors
- Verify `BACKEND_CORS_ORIGINS` includes `FRONTEND_URL`
- Check CORS headers: `curl -I -X OPTIONS <API_URL>/api/v1/books -H "Origin: <FRONTEND_URL>"`

---

## Security Best Practices

1. **Rotate secrets regularly**: Update all secrets every 90 days
2. **Use different secrets per environment**: Never share secrets between staging/production
3. **Limit secret access**: Only grant repository access to necessary team members
4. **Monitor secret usage**: Review GitHub Actions logs for unauthorized access
5. **Use environment-specific keys**: Use Clerk test keys for staging, live keys for production
