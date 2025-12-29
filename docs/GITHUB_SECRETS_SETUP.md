# GitHub Secrets Configuration for E2E Tests

This document explains the GitHub Secrets used by the E2E test workflow.

## ✅ Existing Secrets (Already Configured)

The E2E tests workflow uses the following secrets that are **already configured** in your GitHub repository:

### 1. `MONGODB_URI` (Already exists)
**Description**: MongoDB Atlas connection string **WITHOUT database name**
**Format**: `mongodb+srv://<username>:<password>@<cluster>.mongodb.net/`
**Example**: `mongodb+srv://user:pass@cluster.mongodb.net/`
**Usage**: Used by both staging deployment and E2E tests

**IMPORTANT**: The database name is NOT included in this URI. The database is specified separately via `DATABASE_NAME`.

**Note**: This secret is already configured and used by the `deploy-staging.yml` workflow.

### 2. `DATABASE_NAME` (Already exists)
**Description**: Database name only (not part of the connection URI)
**Format**: Just the database name (e.g., `auto_author_staging`, `auto_author_test`)
**Example**: `auto_author_staging`
**Usage**: Explicitly specifies which database to use within the MongoDB cluster

**IMPORTANT**: This is kept separate from `MONGODB_URI` for flexibility. The same connection URI can be used with different databases by changing only this value.

**Note**: This secret is already configured and used by the `deploy-staging.yml` workflow.

### 3. `BETTER_AUTH_SECRET` (Already exists)
**Description**: Secret key for JWT token signing
**Format**: Random string (minimum 32 characters, recommended 64+)

**How to generate**:
```bash
python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

**Security Notes**:
- Use a different secret for CI than production
- Never commit this to source control
- Rotate periodically

### 4. `OPENAI_API_KEY` (Already exists)
**Description**: OpenAI API key for AI features
**Format**: `sk-...`

**Note**: This secret is already configured and used by the `deploy-staging.yml` workflow.

## How These Secrets Are Used in E2E Tests

The secrets are automatically used by the E2E test workflow without any additional configuration needed.

## Workflow Configuration

The E2E tests workflow (`.github/workflows/tests.yml`) uses these secrets as follows:

```yaml
env:
  DATABASE_URL: ${{ secrets.MONGODB_URI }}
  DATABASE_NAME: ${{ secrets.DATABASE_NAME }}
  BETTER_AUTH_SECRET: ${{ secrets.BETTER_AUTH_SECRET }}
  BETTER_AUTH_URL: http://localhost:3000
  BYPASS_AUTH: true
  OPENAI_AUTOAUTHOR_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

**Note**: These are the same secrets used by the staging deployment workflow, ensuring consistency across environments.

## MongoDB Atlas SSL/TLS Configuration

The backend automatically uses SSL/TLS for MongoDB Atlas connections with the following configuration:

- **Certificate Validation**: Uses `certifi` package for trusted CA certificates
- **TLS Enabled**: Automatically enabled for `mongodb+srv://` URIs
- **Timeouts**:
  - Server selection: 30 seconds
  - Connection: 20 seconds
  - Socket operations: 20 seconds

See `backend/app/db/base.py` for implementation details.

## Testing the Configuration

Since all secrets are already configured, you can trigger a workflow run immediately:

1. **Trigger via push** (recommended):
   ```bash
   git add .
   git commit -m "feat: Configure E2E tests with MongoDB Atlas SSL/TLS"
   git push
   ```

2. **Manual trigger** (alternative):
   ```bash
   gh workflow run tests.yml
   ```

3. **Check workflow logs**:
   - Go to **Actions** tab in GitHub
   - Click on the workflow run
   - Check "E2E Tests" job logs
   - Look for "Backend is ready!" message within 60 seconds

## Troubleshooting

### Backend fails to start
**Symptom**: "Backend failed to start within 60 seconds"

**Possible causes**:
1. Invalid MongoDB Atlas URL
2. Network connectivity issues
3. Invalid credentials
4. Database user permissions insufficient

**Solution**: Check workflow logs for detailed error messages

### SSL/TLS handshake errors
**Symptom**: SSL certificate verification failed

**Solution**: Ensure you're using Python 3.13 and the `certifi` package is installed (already configured in `backend/pyproject.toml`)

### Authentication errors
**Symptom**: 401 Unauthorized responses

**Possible causes**:
1. `BETTER_AUTH_SECRET` not set or invalid
2. `BYPASS_AUTH` not properly configured

**Solution**: Verify `BYPASS_AUTH=true` is set in workflow environment

## Security Best Practices

1. **Principle of Least Privilege**: Grant minimal necessary permissions
2. **Separate Environments**: Use different credentials for dev/staging/prod/CI
3. **Credential Rotation**: Rotate secrets periodically (quarterly recommended)
4. **Audit Logs**: Monitor MongoDB Atlas and OpenAI usage
5. **Cost Controls**: Set usage limits on OpenAI API key
6. **Network Security**: Use MongoDB Atlas IP allowlists if possible
7. **Secrets Scanning**: Enable GitHub secret scanning (automatically enabled for public repos)

## Related Documentation

- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [MongoDB Atlas Security](https://www.mongodb.com/docs/atlas/security/)
- [Better Auth Documentation](https://www.better-auth.com/)
- [OpenAI API Best Practices](https://platform.openai.com/docs/guides/safety-best-practices)
