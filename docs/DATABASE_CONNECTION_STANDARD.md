# Database Connection Standard

**Last Updated**: 2025-12-29
**Status**: ✅ FINAL - All code is consistent with this standard

## 🎯 The Standard (Non-Negotiable)

### Connection URI: NO Database Name
```
✅ CORRECT:   mongodb+srv://user:pass@cluster.mongodb.net/
❌ INCORRECT: mongodb+srv://user:pass@cluster.mongodb.net/mydb
```

### Database Name: Separate Variable
```
DATABASE_NAME=auto_author_staging
```

## 📋 Variable Naming Convention

| Context | Variable Name | Contains | Example |
|---------|---------------|----------|---------|
| **GitHub Secret** | `MONGODB_URI` | Connection URI (no DB) | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| **GitHub Secret** | `DATABASE_NAME` | Database name only | `auto_author_staging` |
| **Environment Variable** | `DATABASE_URL` | Set from `MONGODB_URI` | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| **Environment Variable** | `DATABASE_NAME` | Database name only | `auto_author_staging` |
| **Python Code** | `settings.DATABASE_URL` | Read from env var | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| **Python Code** | `settings.DATABASE_NAME` | Read from env var | `auto_author_staging` |

## 🔄 How It Works

### 1. GitHub Secrets (Repository Settings)
```yaml
# In GitHub repository secrets:
MONGODB_URI: mongodb+srv://frankbria:password@cluster.mongodb.net/
DATABASE_NAME: auto_author_staging
```

### 2. GitHub Actions Workflow
```yaml
# Workflows map secrets to environment variables:
env:
  DATABASE_URL: ${{ secrets.MONGODB_URI }}      # Note: Maps MONGODB_URI → DATABASE_URL
  DATABASE_NAME: ${{ secrets.DATABASE_NAME }}
```

### 3. Backend Configuration (config.py)
```python
class Settings(BaseSettings):
    DATABASE_URL: str = "mongodb://localhost:27017"  # Read from env var
    DATABASE_NAME: str = "auto_author_test"          # Read from env var
```

### 4. Database Connection (base.py)
```python
# Connect to MongoDB cluster (no database specified in URI)
_client = AsyncIOMotorClient(settings.DATABASE_URL, ...)

# Explicitly select database
_db = _client[settings.DATABASE_NAME]
```

## ✅ Why This Pattern?

### Flexibility
- **Same URI** works for multiple databases (dev, staging, prod)
- **Easy switching**: Change `DATABASE_NAME` without touching `MONGODB_URI`
- **Testing**: Different test databases without new connection strings

### Security
- **Separate concerns**: Connection credentials vs. database selection
- **Easier rotation**: Rotate database user password without changing database names

### Clarity
- **Explicit**: Clear which database you're using
- **No ambiguity**: No confusion about whether database is in URI or not

## 📍 Where This Standard Applies

### ✅ Already Consistent

1. **Backend Code**
   - `backend/app/core/config.py` - Settings definition
   - `backend/app/db/base.py` - Database connection
   - `backend/app/populate_db_test_data.py` - Test data script
   - `backend/.env.example` - Environment template

2. **GitHub Workflows**
   - `.github/workflows/tests.yml` - E2E test workflow
   - `.github/workflows/deploy-staging.yml` - Staging deployment

3. **Documentation**
   - `docs/GITHUB_SECRETS_SETUP.md` - Secrets configuration guide
   - `docs/DATABASE_CONNECTION_STANDARD.md` - This document

## 🚫 Common Mistakes to Avoid

### ❌ DON'T: Put database name in URI
```python
# WRONG - Database name in URI
DATABASE_URL = "mongodb+srv://user:pass@cluster.mongodb.net/mydb"
_client = AsyncIOMotorClient(DATABASE_URL)
_db = _client[DATABASE_NAME]  # This would try to access DATABASE_NAME, not "mydb"
```

### ✅ DO: Keep them separate
```python
# CORRECT - URI without database
DATABASE_URL = "mongodb+srv://user:pass@cluster.mongodb.net/"
_client = AsyncIOMotorClient(DATABASE_URL)
_db = _client[DATABASE_NAME]  # Explicitly selects the database
```

### ❌ DON'T: Hardcode database name
```python
# WRONG - Hardcoded
_db = _client["auto_author_staging"]
```

### ✅ DO: Use the setting
```python
# CORRECT - From settings
_db = _client[settings.DATABASE_NAME]
```

## 🔍 How to Verify Compliance

### Check GitHub Secrets
```bash
gh secret list | grep -E "MONGODB_URI|DATABASE_NAME"
```

Should show:
```
DATABASE_NAME    Updated 2025-12-XX
MONGODB_URI      Updated 2025-12-XX
```

### Check Environment Variables
```bash
# In backend directory
grep -E "DATABASE_URL|DATABASE_NAME" .env .env.example
```

Should show separate values:
```
DATABASE_URL=mongodb://localhost:27017
DATABASE_NAME=auto_author_test
```

### Check Code Usage
```bash
# Search for improper usage
grep -r "mongodb.*/" backend/app --include="*.py" | grep -v "mongodb://localhost" | grep -v "mongodb+srv://"
```

Should return minimal results (only in comments/docs).

## 📝 Examples

### Local Development (.env)
```bash
DATABASE_URL=mongodb://localhost:27017
DATABASE_NAME=auto_author_dev
```

### Staging Environment (GitHub Secrets)
```bash
MONGODB_URI=mongodb+srv://staging_user:pass@cluster.mongodb.net/
DATABASE_NAME=auto_author_staging
```

### Production Environment (GitHub Secrets)
```bash
MONGODB_URI=mongodb+srv://prod_user:pass@cluster.mongodb.net/
DATABASE_NAME=auto_author_prod
```

### Testing Environment (pytest)
```bash
DATABASE_URL=mongodb://localhost:27017
DATABASE_NAME=auto_author_test
```

## 🔒 Security Notes

1. **Never commit** `MONGODB_URI` values to git
2. **Use different credentials** for each environment
3. **Limit permissions** on database users (no admin access for app)
4. **Rotate credentials** periodically (quarterly recommended)
5. **Monitor access** via MongoDB Atlas logs

## 🤝 Enforcement

**This standard is enforced by**:
- Code reviews (check PR diffs for violations)
- Integration tests (verify connection works)
- Documentation (this file serves as source of truth)

**If you find inconsistencies**:
1. File an issue
2. Reference this document
3. Propose a fix that aligns with this standard

---

**Questions?** Refer to `docs/GITHUB_SECRETS_SETUP.md` for implementation details.
