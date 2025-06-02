# Testing Setup Guide

This guide walks you through setting up the complete testing environment for the Auto-Author application.

## Prerequisites

### System Requirements
- Node.js 18+ (for frontend)
- Python 3.9+ (for backend)
- Git
- VS Code (recommended)

### Environment Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd auto-author
```

2. **Install root dependencies**
```bash
npm install
```

## Frontend Testing Setup

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configuration Files

#### Jest Configuration (`jest.config.cjs`)
```javascript
const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
}

module.exports = createJestConfig(customJestConfig)
```

#### Jest Setup (`jest.setup.js`)
```javascript
import '@testing-library/jest-dom'

// Mock Next.js router
jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
    pathname: '/',
    query: {},
  }),
}))

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'
```

### 3. Test Scripts
Add these scripts to `package.json`:
```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:ci": "jest --ci --coverage --watchAll=false",
    "test:e2e": "jest --testNamePattern='End to End'",
    "test:integration": "jest --testNamePattern='Integration'",
    "test:unit": "jest --testPathPattern='unit'",
    "test:performance": "jest --testNamePattern='Performance'",
    "test:accessibility": "jest --testNamePattern='Accessibility'"
  }
}
```

### 4. VS Code Configuration
Create `.vscode/settings.json`:
```json
{
  "jest.jestCommandLine": "npm test --",
  "jest.autoRun": "watch",
  "jest.showCoverageOnLoad": true,
  "testing.automaticallyOpenPeekView": "never"
}
```

## Backend Testing Setup

### 1. Virtual Environment
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-mock factory-boy
```

### 3. Configuration Files

#### Pytest Configuration (`pytest.ini`)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=85
asyncio_mode = auto
env_files = .env.test
```

#### Coverage Configuration (`.coveragerc`)
```ini
[run]
source = app
omit = 
    */tests/*
    */venv/*
    */__pycache__/*
    */migrations/*
    app/main.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
```

### 4. Test Environment
Create `.env.test`:
```bash
DATABASE_URL=sqlite:///test.db
OPENAI_API_KEY=test_key_openai
ANTHROPIC_API_KEY=test_key_anthropic
ENVIRONMENT=test
LOG_LEVEL=WARNING
CORS_ORIGINS=["http://localhost:3000"]
```

### 5. Test Database Setup
Create `conftest.py` (if not exists):
```python
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_db():
    """Create test database."""
    engine = create_engine("sqlite:///test.db")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(test_db):
    """Create database session for tests."""
    SessionLocal = sessionmaker(bind=test_db)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()
```

## IDE Integration

### VS Code Extensions
Install these recommended extensions:
- Jest Runner
- Python Test Explorer
- Coverage Gutters
- Test Adapter Converter

### IntelliJ/PyCharm
1. Configure Python interpreter to use virtual environment
2. Set test runner to pytest
3. Enable coverage integration

## Database Setup for Testing

### SQLite (Development/Testing)
```bash
# Backend directory
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"
```

### PostgreSQL (Production-like Testing)
```bash
# Install PostgreSQL locally or use Docker
docker run --name test-postgres -e POSTGRES_PASSWORD=testpass -d -p 5433:5432 postgres

# Update .env.test
DATABASE_URL=postgresql://postgres:testpass@localhost:5433/test_db
```

## Mock Services Setup

### AI Service Mocking
Create `tests/mocks/ai_services.py`:
```python
class MockOpenAIClient:
    def generate_questions(self, content, count=5):
        return [f"Test question {i}?" for i in range(count)]

class MockAnthropicClient:
    def generate_content(self, prompt):
        return "Mock generated content"
```

### API Client Mocking
Create `frontend/src/__tests__/mocks/apiClient.ts`:
```typescript
export const mockApiClient = {
  generateQuestions: jest.fn(),
  saveResponse: jest.fn(),
  getProgress: jest.fn(),
}
```

## Running Tests

### Frontend
```bash
cd frontend

# All tests
npm test

# Specific test files
npm test ChapterQuestions
npm test -- --testNamePattern="should handle question generation"

# Coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

### Backend
```bash
cd backend

# All tests
python -m pytest

# Specific test files
python -m pytest tests/test_api/test_chapter_questions_api.py

# With coverage
python -m pytest --cov

# Verbose output
python -m pytest -v

# Fast fail
python -m pytest -x
```

## Troubleshooting

### Common Issues

#### Frontend
1. **Module resolution issues**
   - Check `jest.config.cjs` moduleNameMapping
   - Verify tsconfig.json paths

2. **Jest environment issues**
   - Ensure `jest-environment-jsdom` is installed
   - Check Jest configuration

#### Backend
1. **Database connection issues**
   - Verify `.env.test` configuration
   - Check database permissions

2. **Import path issues**
   - Ensure PYTHONPATH includes app directory
   - Check relative imports

### Performance Issues
- Use `--maxWorkers=50%` for Jest on limited resources
- Set `pytest -n auto` for parallel test execution

## Next Steps

1. Run initial test suite to verify setup
2. Review [Best Practices](./best-practices.md)
3. Explore [Test Architecture](./test-architecture.md)
4. Set up [CI/CD Integration](./cicd-integration.md)
