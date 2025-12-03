# MongoDB Database Backup and Restoration Guide

## Overview

This document describes the automated backup system for the Auto-Author MongoDB database and provides step-by-step procedures for restoring from backups.

## Backup System

### Schedule and Retention

- **Backup Frequency**: Daily at 2:00 AM UTC
- **Retention Period**: 30 days (configurable)
- **Storage Location**: GitHub Actions Artifacts
- **Backup Method**: `mongodump` with gzip compression
- **Workflow File**: `.github/workflows/database-backup.yml`

### What Gets Backed Up

The backup includes:
- All collections in the `auto_author_production` database (or configured database)
- Indexes and collection metadata
- Document data with gzip compression
- Backup metadata (timestamp, size, duration, etc.)

### Backup Artifacts

Each backup creates a compressed archive with the naming format:
```
mongodb-backup-YYYYMMDD_HHMMSS.tar.gz
```

The archive contains:
- `auto_author_production/` - Database dump directory
- `backup-metadata.json` - Backup information and metadata

### Backup Metadata

Each backup includes a `backup-metadata.json` file with:
```json
{
  "timestamp": "20250102_020000",
  "database": "auto_author_production",
  "size": "152M",
  "duration_seconds": 45,
  "backup_date": "2025-01-02 02:00:45 UTC",
  "github_workflow": "MongoDB Database Backup",
  "github_run_id": "12345678",
  "github_run_number": "123",
  "mongodb_tools_version": "mongodump version: 100.9.0"
}
```

## Manual Backup Trigger

You can trigger a manual backup at any time:

1. Go to **Actions** tab in GitHub repository
2. Select **MongoDB Database Backup** workflow
3. Click **Run workflow** dropdown
4. (Optional) Specify custom retention period in days
5. Click **Run workflow** button

## Configuration

### Required GitHub Secrets

Configure these secrets in your GitHub repository settings:

| Secret | Description | Example |
|--------|-------------|---------|
| `DATABASE_URI` | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority` |
| `MONGODB_DATABASE` | Database name (optional) | `auto_author_production` |

**Note**: If `MONGODB_DATABASE` is not set, the workflow defaults to `auto_author_production`.

### Optional GitHub Variables

For notifications (optional):

| Variable | Description | Example |
|----------|-------------|---------|
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | `https://hooks.slack.com/services/...` |

### Setting Up Secrets

1. Navigate to repository **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add each secret:
   - Name: `DATABASE_URI`
   - Value: Your MongoDB connection string
4. Repeat for other secrets

## Restoration Procedures

### Prerequisites

Before restoring, ensure you have:
- MongoDB Database Tools installed (`mongorestore` command)
- Access to download GitHub Actions artifacts
- MongoDB connection credentials
- Sufficient permissions to write to the target database

### Step 1: Download Backup Artifact

#### Option A: Via GitHub Web Interface

1. Go to **Actions** tab in GitHub repository
2. Click on **MongoDB Database Backup** workflow
3. Select the workflow run with the backup you need
4. Scroll to **Artifacts** section at the bottom
5. Click to download `mongodb-backup-YYYYMMDD_HHMMSS`
6. The artifact will download as a ZIP file

#### Option B: Via GitHub CLI

```bash
# List available backups
gh run list --workflow=database-backup.yml --limit 30

# Download specific backup artifact
gh run download <RUN_ID> -n mongodb-backup-YYYYMMDD_HHMMSS

# Or download the latest backup
LATEST_RUN=$(gh run list --workflow=database-backup.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run download $LATEST_RUN
```

### Step 2: Extract Backup Archive

```bash
# If downloaded via web interface (ZIP format)
unzip mongodb-backup-YYYYMMDD_HHMMSS.zip

# Extract the tar.gz archive
tar -xzf mongodb-backup-YYYYMMDD_HHMMSS.tar.gz

# Navigate to backup directory
cd mongodb-backup-YYYYMMDD_HHMMSS
```

### Step 3: Verify Backup Integrity

```bash
# Check backup metadata
cat backup-metadata.json

# List backed up collections
ls -la auto_author_production/

# Check collection file sizes
du -sh auto_author_production/*
```

### Step 4: Restore Database

#### Full Database Restoration

```bash
# Restore entire database (recommended for disaster recovery)
mongorestore \
  --uri="mongodb://localhost:27017" \
  --db="auto_author_production" \
  --gzip \
  --drop \
  auto_author_production/

# Notes:
# --drop: Drops existing collections before restoring (WARNING: destructive)
# --gzip: Handles gzip-compressed backup files
# --uri: MongoDB connection string (use production URI for production restore)
```

#### Selective Collection Restoration

```bash
# Restore only specific collection (e.g., books)
mongorestore \
  --uri="mongodb://localhost:27017" \
  --db="auto_author_production" \
  --collection="books" \
  --gzip \
  --drop \
  auto_author_production/books.bson.gz
```

#### Restore to Different Database (Testing)

```bash
# Restore to a different database name (useful for testing)
mongorestore \
  --uri="mongodb://localhost:27017" \
  --db="auto_author_test_restore" \
  --gzip \
  auto_author_production/
```

#### Restore to MongoDB Atlas

```bash
# Restore to Atlas cluster
mongorestore \
  --uri="mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority" \
  --db="auto_author_production" \
  --gzip \
  --drop \
  auto_author_production/
```

### Step 5: Verify Restoration

```bash
# Connect to MongoDB and verify data
mongosh "mongodb://localhost:27017/auto_author_production"

# In MongoDB shell, check collections:
> show collections
> db.books.countDocuments()
> db.users.countDocuments()
> db.chapters.countDocuments()

# Verify indexes
> db.books.getIndexes()
> db.chapters.getIndexes()

# Sample data check
> db.books.findOne()
> db.users.findOne()
```

### Step 6: Application Testing

After restoration, perform application-level testing:

1. **Backend API Tests**
   ```bash
   cd backend
   uv run pytest tests/ -v
   ```

2. **Integration Tests**
   ```bash
   uv run pytest tests/integration/ -v
   ```

3. **Manual Testing**
   - Start backend: `cd backend && uv run uvicorn app.main:app --reload`
   - Start frontend: `cd frontend && npm run dev`
   - Test critical user workflows:
     - User login
     - Book creation
     - Chapter editing
     - TOC generation
     - Export functionality

## Common Restoration Scenarios

### Scenario 1: Disaster Recovery (Complete Data Loss)

**Use Case**: Production database completely lost or corrupted

```bash
# 1. Download latest backup
gh run download $(gh run list --workflow=database-backup.yml --limit 1 --json databaseId --jq '.[0].databaseId')

# 2. Extract backup
tar -xzf mongodb-backup-*.tar.gz
cd mongodb-backup-*

# 3. Restore to production database
mongorestore \
  --uri="${PRODUCTION_DATABASE_URI}" \
  --db="auto_author_production" \
  --gzip \
  --drop \
  auto_author_production/

# 4. Verify restoration
mongosh "${PRODUCTION_DATABASE_URI}" --eval "
  use auto_author_production;
  db.stats();
  db.books.countDocuments();
  db.users.countDocuments();
"

# 5. Test application
curl -X GET https://api.autoauthor.app/health
```

### Scenario 2: Point-in-Time Recovery

**Use Case**: Need to restore data from a specific date/time

```bash
# 1. List available backups
gh run list --workflow=database-backup.yml --json startedAt,databaseId --jq '.[] | "\(.startedAt) - \(.databaseId)"'

# 2. Download specific backup from desired date
gh run download <RUN_ID>

# 3. Restore (as shown in Step 4 above)
```

### Scenario 3: Accidental Data Deletion

**Use Case**: Specific collection or documents accidentally deleted

```bash
# 1. Download latest backup (before deletion)
gh run download $(gh run list --workflow=database-backup.yml --limit 1 --json databaseId --jq '.[0].databaseId')

# 2. Extract and restore only affected collection
tar -xzf mongodb-backup-*.tar.gz
cd mongodb-backup-*

# 3. Restore only affected collection (e.g., books)
mongorestore \
  --uri="mongodb://localhost:27017" \
  --db="auto_author_production" \
  --collection="books" \
  --gzip \
  --drop \
  auto_author_production/books.bson.gz

# 4. Verify restoration
mongosh "mongodb://localhost:27017/auto_author_production" --eval "db.books.countDocuments()"
```

### Scenario 4: Development Database Reset

**Use Case**: Reset development database to production-like state

```bash
# 1. Download latest production backup
gh run download $(gh run list --workflow=database-backup.yml --limit 1 --json databaseId --jq '.[0].databaseId')

# 2. Extract backup
tar -xzf mongodb-backup-*.tar.gz
cd mongodb-backup-*

# 3. Restore to development database
mongorestore \
  --uri="mongodb://localhost:27017" \
  --db="auto_author_dev" \
  --gzip \
  auto_author_production/

# 4. Anonymize sensitive data (recommended)
mongosh "mongodb://localhost:27017/auto_author_dev" --eval "
  db.users.updateMany({}, {
    \$set: {
      email: 'dev.user@example.com',
      hashed_pw: 'ANONYMIZED_HASH'
    }
  });
"
```

## Testing Restoration Procedures

### Monthly Restoration Test

**Best Practice**: Test restoration procedures monthly to ensure backups are valid.

```bash
#!/bin/bash
# test-restoration.sh

set -e

echo "🧪 Testing MongoDB Backup Restoration"

# 1. Download latest backup
echo "📥 Downloading latest backup..."
LATEST_RUN=$(gh run list --workflow=database-backup.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run download $LATEST_RUN

# 2. Extract backup
echo "📦 Extracting backup..."
BACKUP_FILE=$(ls mongodb-backup-*.tar.gz | head -n1)
tar -xzf "$BACKUP_FILE"
BACKUP_DIR=$(basename "$BACKUP_FILE" .tar.gz)

# 3. Restore to test database
echo "🔄 Restoring to test database..."
mongorestore \
  --uri="mongodb://localhost:27017" \
  --db="auto_author_restore_test" \
  --gzip \
  --drop \
  "${BACKUP_DIR}/auto_author_production/"

# 4. Verify restoration
echo "✅ Verifying restoration..."
BOOK_COUNT=$(mongosh "mongodb://localhost:27017/auto_author_restore_test" --quiet --eval "db.books.countDocuments()")
USER_COUNT=$(mongosh "mongodb://localhost:27017/auto_author_restore_test" --quiet --eval "db.users.countDocuments()")

echo "📊 Restoration Test Results:"
echo "   - Books: ${BOOK_COUNT}"
echo "   - Users: ${USER_COUNT}"

# 5. Cleanup
echo "🧹 Cleaning up..."
rm -rf "$BACKUP_DIR" "$BACKUP_FILE"
mongosh "mongodb://localhost:27017" --quiet --eval "db.getSiblingDB('auto_author_restore_test').dropDatabase()"

echo "✅ Restoration test completed successfully!"
```

Run this test monthly:
```bash
chmod +x test-restoration.sh
./test-restoration.sh
```

## Troubleshooting

### Issue: Backup workflow fails with connection error

**Symptoms**: Workflow fails at "Perform MongoDB backup" step with connection timeout

**Solutions**:
1. Verify `DATABASE_URI` secret is correctly configured
2. Check MongoDB Atlas IP whitelist (add GitHub Actions IPs if using Atlas)
3. Verify MongoDB cluster is running and accessible
4. Test connection string locally:
   ```bash
   mongodump --uri="${DATABASE_URI}" --db="auto_author_production" --dryRun
   ```

### Issue: Restoration fails with authentication error

**Symptoms**: `mongorestore` fails with "authentication failed"

**Solutions**:
1. Verify MongoDB user has write permissions
2. Check connection string includes credentials
3. Ensure database user has `dbAdmin` or `restore` role:
   ```javascript
   // In MongoDB shell
   db.grantRolesToUser("username", [{role: "dbAdmin", db: "auto_author_production"}])
   ```

### Issue: Backup artifact not found

**Symptoms**: Cannot find backup artifact after 30 days

**Solutions**:
1. Check artifact retention period in workflow run
2. Download backups before they expire (30 days default)
3. Consider longer-term backup storage (AWS S3, Azure Blob, etc.)
4. Set up external backup archiving:
   ```bash
   # Download and archive to S3 (example)
   gh run download $RUN_ID
   aws s3 cp mongodb-backup-*.tar.gz s3://my-backup-bucket/mongodb/
   ```

### Issue: Partial restoration (missing collections)

**Symptoms**: Some collections missing after restoration

**Solutions**:
1. Check backup integrity:
   ```bash
   tar -tzf mongodb-backup-*.tar.gz | grep ".bson.gz"
   ```
2. Verify mongorestore output for errors
3. Check MongoDB logs for restoration issues
4. Try restoring individual collections:
   ```bash
   mongorestore --collection=missing_collection --gzip ...
   ```

### Issue: Indexes not restored correctly

**Symptoms**: Application slow after restoration, missing indexes

**Solutions**:
1. Verify indexes in backup:
   ```bash
   tar -xzf mongodb-backup-*.tar.gz
   ls -la */metadata.json
   ```
2. Manually rebuild indexes if needed:
   ```javascript
   // In MongoDB shell
   db.books.createIndex({user_id: 1})
   db.chapters.createIndex({book_id: 1, order: 1})
   ```

### Issue: Large backup size exceeds artifact limits

**Symptoms**: Workflow fails uploading artifact (GitHub limit: 10GB per artifact)

**Solutions**:
1. Split backup into multiple artifacts
2. Implement incremental backups
3. Use external storage (S3, Azure Blob) for large backups
4. Compress backup more aggressively
5. Archive old data before backup

## Security Considerations

### Backup Security

1. **Secrets Protection**
   - Never commit `DATABASE_URI` to repository
   - Use GitHub Secrets for sensitive credentials
   - Rotate database passwords regularly

2. **Access Control**
   - Limit who can trigger manual backups
   - Restrict artifact download permissions
   - Use read-only database users for backups if possible

3. **Data Privacy**
   - Backups contain sensitive user data
   - Follow GDPR/data retention policies
   - Consider encrypting backup artifacts
   - Document data handling procedures

### Restoration Security

1. **Production Restoration**
   - Require approval for production restores
   - Document all restoration activities
   - Notify team before/after restoration
   - Test in staging first when possible

2. **Development Use**
   - Anonymize sensitive data in dev databases
   - Never restore production backups to public environments
   - Use separate credentials for dev/staging

## Backup Monitoring

### Success Metrics

Monitor these metrics to ensure backup health:

- ✅ **Backup Success Rate**: Should be 100%
- ✅ **Backup Duration**: Should complete within 30 minutes
- ✅ **Backup Size Trend**: Should grow gradually with data
- ✅ **Artifact Availability**: Should have 30 days of backups available

### Alerting

Set up alerts for:

- ❌ Backup workflow failures (critical)
- ⚠️ Backup duration exceeds 20 minutes (warning)
- ⚠️ Backup size increases >50% week-over-week (warning)
- ⚠️ Missing scheduled backup (critical)

Configure Slack/email notifications in workflow for immediate alerts.

## Best Practices

### Backup Best Practices

1. **Test Regularly**: Run monthly restoration tests
2. **Monitor Closely**: Check backup success daily
3. **Document Changes**: Update this guide when workflow changes
4. **Verify Integrity**: Periodically verify backup contents
5. **Plan Retention**: Archive important backups beyond 30 days

### Restoration Best Practices

1. **Test First**: Always test restoration in staging before production
2. **Communicate**: Notify team before production restoration
3. **Verify Data**: Check data integrity after restoration
4. **Document**: Record all restoration activities
5. **Root Cause**: Investigate why restoration was needed

## Related Documentation

- [MongoDB Backup Methods](https://www.mongodb.com/docs/manual/core/backups/)
- [mongodump Documentation](https://www.mongodb.com/docs/database-tools/mongodump/)
- [mongorestore Documentation](https://www.mongodb.com/docs/database-tools/mongorestore/)
- [GitHub Actions Artifacts](https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts)

## Support

For backup/restoration issues:

1. Check this troubleshooting guide
2. Review workflow logs in GitHub Actions
3. Check MongoDB server logs
4. Contact DevOps team
5. Escalate to database administrator if unresolved

## Appendix: MongoDB Database Tools Installation

### Ubuntu/Debian

```bash
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update
sudo apt-get install -y mongodb-database-tools
```

### macOS

```bash
brew tap mongodb/brew
brew install mongodb-database-tools
```

### Verify Installation

```bash
mongodump --version
mongorestore --version
```

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-12-02 | Initial backup system implementation | Claude Code |
| | - Daily automated backups at 2 AM UTC | |
| | - 30-day retention period | |
| | - GitHub Actions artifacts storage | |
| | - Comprehensive restoration procedures | |
