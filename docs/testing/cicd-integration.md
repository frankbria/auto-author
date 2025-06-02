# CI/CD Integration

This document describes the continuous integration and deployment setup for the Auto-Author application.

## Overview

The CI/CD pipeline is built with GitHub Actions and includes:

- **Automated Testing**: Run on every push and pull request
- **Quality Gates**: Code quality, security, and performance checks
- **Staging Deployment**: Automatic deployment to staging environment
- **Production Deployment**: Tagged releases to production
- **Notifications**: Team notifications for deployment status

## Workflow Files

### 1. Test Suite (`.github/workflows/test-suite.yml`)
Main testing workflow that runs on every push and pull request.

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Scheduled daily runs at 2 AM UTC

**Jobs:**
- **Frontend Tests**: Unit, integration, and linting
- **Backend Tests**: API, integration, and database tests
- **E2E Tests**: Full workflow testing
- **Performance Tests**: Load and performance testing (scheduled/labeled)
- **Accessibility Tests**: WCAG compliance testing
- **Security Scan**: Vulnerability scanning

### 2. Staging Deployment (`.github/workflows/deploy-staging.yml`)
Deploys to staging environment after successful tests.

**Triggers:**
- Push to `develop` branch
- Successful completion of test suite

**Features:**
- Smoke testing
- Post-deployment verification
- Slack notifications

### 3. Production Deployment (`.github/workflows/deploy-production.yml`)
Deploys tagged releases to production.

**Triggers:**
- Git tags matching `v*` pattern
- GitHub releases

**Features:**
- Full test suite execution
- Security scanning
- Performance benchmarking
- Post-deployment verification

## Setup Instructions

### 1. Environment Setup

#### Repository Secrets
Configure these secrets in GitHub repository settings:

**Staging Environment:**
```
STAGING_API_URL=https://api-staging.auto-author.com
STAGING_CLERK_KEY=pk_test_...
STAGING_DEPLOY_KEY=ssh-rsa...
STAGING_HOST=staging.auto-author.com
```

**Production Environment:**
```
PRODUCTION_API_URL=https://api.auto-author.com
PRODUCTION_CLERK_KEY=pk_live_...
PRODUCTION_DEPLOY_KEY=ssh-rsa...
PRODUCTION_HOST=auto-author.com
```

**Common Secrets:**
```
CODECOV_TOKEN=your_codecov_token
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

#### Environment Configuration
Create GitHub environments:

1. **Staging Environment**
   - URL: https://staging.auto-author.com
   - Required reviewers: None (auto-deploy)
   - Deployment branches: `develop`

2. **Production Environment**
   - URL: https://auto-author.com
   - Required reviewers: Team leads
   - Deployment branches: Tagged releases only

### 2. Branch Protection Rules

#### Main Branch Protection
```yaml
Branch: main
Restrictions:
  - Require pull request reviews (2 reviewers)
  - Require status checks to pass
  - Require branches to be up to date
  - Include administrators
  - Restrict pushes to admins only

Required Status Checks:
  - Frontend Tests
  - Backend Tests
  - E2E Tests
  - Security Scan
```

#### Develop Branch Protection
```yaml
Branch: develop
Restrictions:
  - Require pull request reviews (1 reviewer)
  - Require status checks to pass
  - Include administrators

Required Status Checks:
  - Frontend Tests
  - Backend Tests
```

### 3. Test Configuration

#### Frontend Test Scripts
Add to `frontend/package.json`:
```json
{
  "scripts": {
    "test": "jest",
    "test:ci": "jest --ci --coverage --watchAll=false",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:integration": "jest --testNamePattern='Integration'",
    "test:e2e": "jest --testNamePattern='End to End'",
    "test:performance": "jest --testNamePattern='Performance'",
    "test:accessibility": "jest --testNamePattern='Accessibility'",
    "test:smoke": "jest --testNamePattern='Smoke'"
  }
}
```

#### Backend Test Configuration
Update `backend/pytest.ini`:
```ini
[tool:pytest]
testpaths = tests
addopts = 
    -v
    --tb=short
    --cov=app
    --cov-report=xml
    --cov-report=term-missing
    --cov-fail-under=85
    --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance tests
    smoke: Smoke tests
    critical: Critical path tests
```

## Test Environments

### 1. Local Development
```bash
# Frontend
cd frontend
npm install
npm test

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m pytest
```

### 2. CI Environment
- **OS**: Ubuntu Latest
- **Node.js**: 18.x, 20.x (matrix)
- **Python**: 3.9, 3.10, 3.11 (matrix)
- **Database**: PostgreSQL 15 (for integration tests)
- **Cache**: npm and pip dependencies

### 3. Staging Environment
- **Database**: PostgreSQL (separate from production)
- **AI Services**: Test API keys
- **File Storage**: Separate S3 bucket
- **Monitoring**: Basic health checks

### 4. Production Environment
- **Database**: PostgreSQL (production)
- **AI Services**: Production API keys
- **File Storage**: Production S3 bucket
- **Monitoring**: Full monitoring and alerting

## Quality Gates

### 1. Code Quality
- **ESLint**: JavaScript/TypeScript linting
- **Black**: Python code formatting
- **isort**: Python import sorting
- **mypy**: Python type checking

### 2. Test Coverage
- **Frontend**: 85% minimum coverage
- **Backend**: 85% minimum coverage
- **Integration**: Critical paths covered

### 3. Security
- **npm audit**: Frontend dependency vulnerabilities
- **safety**: Backend dependency vulnerabilities
- **CodeQL**: Static security analysis

### 4. Performance
- **Bundle size**: Frontend bundle analysis
- **Load testing**: Backend API performance
- **Memory usage**: Application memory profiling

## Deployment Strategy

### 1. Feature Development
```
feature/branch → develop → staging
```

1. Create feature branch from `develop`
2. Implement feature with tests
3. Create pull request to `develop`
4. Code review and testing
5. Merge to `develop`
6. Automatic deployment to staging

### 2. Release Process
```
develop → main → production
```

1. Create pull request from `develop` to `main`
2. Full test suite execution
3. Code review and approval
4. Merge to `main`
5. Create git tag (`v1.0.0`)
6. Automatic production deployment

### 3. Hotfix Process
```
hotfix/branch → main → production
```

1. Create hotfix branch from `main`
2. Implement fix with tests
3. Create pull request to `main`
4. Expedited review process
5. Merge and tag
6. Production deployment
7. Merge back to `develop`

## Monitoring and Alerts

### 1. Test Failure Notifications
- **Slack**: Real-time test failure alerts
- **Email**: Daily test summary reports
- **GitHub**: PR status checks

### 2. Deployment Notifications
- **Slack**: Deployment status updates
- **Email**: Production deployment confirmations
- **PagerDuty**: Critical deployment failures

### 3. Performance Monitoring
- **Test execution time**: Track test performance
- **Deployment duration**: Monitor deployment speed
- **Coverage trends**: Track coverage over time

## Troubleshooting

### Common CI Issues

#### 1. Test Failures
```bash
# Check test logs
cat test-results.xml

# Run tests locally
npm test -- --verbose
python -m pytest -v
```

#### 2. Dependency Issues
```bash
# Clear cache
npm ci --cache .npm --prefer-offline

# Update requirements
pip install -r requirements.txt --upgrade
```

#### 3. Environment Issues
```bash
# Check environment variables
env | grep NODE_ENV
env | grep DATABASE_URL

# Verify service health
curl -f $API_URL/health
```

### Test Environment Debugging

#### 1. Database Connection
```python
# Test database connectivity
import asyncio
from app.database import engine

async def test_db():
    async with engine.begin() as conn:
        result = await conn.execute("SELECT 1")
        print(result.scalar())

asyncio.run(test_db())
```

#### 2. API Connectivity
```bash
# Test API endpoints
curl -X GET $API_URL/health
curl -X POST $API_URL/api/test -H "Content-Type: application/json"
```

## Best Practices

### 1. Test Reliability
- Use stable test data
- Clean up test artifacts
- Avoid external dependencies
- Implement proper waits

### 2. Performance
- Parallelize test execution
- Cache dependencies
- Optimize test data setup
- Monitor resource usage

### 3. Security
- Rotate secrets regularly
- Use least privilege access
- Scan for vulnerabilities
- Audit deployment logs

### 4. Maintenance
- Regular dependency updates
- Test environment cleanup
- Performance optimization
- Documentation updates

## Metrics and Reporting

### 1. Test Metrics
- **Test execution time**: Average and trend
- **Test success rate**: Pass/fail percentage
- **Coverage percentage**: Line and branch coverage
- **Flaky test detection**: Tests with inconsistent results

### 2. Deployment Metrics
- **Deployment frequency**: How often deployments occur
- **Lead time**: Time from commit to production
- **Recovery time**: Time to resolve issues
- **Change failure rate**: Percentage of deployments causing issues

### 3. Quality Metrics
- **Bug discovery rate**: Issues found in different stages
- **Security vulnerabilities**: Count and severity
- **Performance regression**: Response time changes
- **User satisfaction**: Feedback and error rates
