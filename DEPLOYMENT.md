# Deployment and Development Setup

**Last Updated**: 2025-10-18
**Environment**: 3-Stage Deployment Process

---

## 🎯 3-Stage Deployment Process

This project follows a 3-stage deployment process to ensure code quality and stability:

### Stage 1: Local Development
- **Environment**: Local development machine
- **Purpose**: Development and initial testing
- **Location**: `/home/frankbria/projects/auto-author`
- **Usage**: Primary development environment where features are built and initially tested

### Stage 2: Staging Server ⚠️ **HIGH PRIORITY SETUP**
- **Environment**: frankbria-inspiron-7586 staging server
- **Purpose**: Stable "sprint demo" environment
- **Usage**: 
  - Integration testing
  - Sprint demonstrations
  - QA testing
  - Pre-production validation
- **Status**: 🚧 **NEEDS SETUP** - This should be one of the first tasks when beginning development work

### Stage 3: Production Deployment
- **Environment**: Live VPS with production configurations
- **Purpose**: End-user production environment
- **Features**:
  - Full production configurations
  - Live user access
  - Production monitoring and logging

---

## 🚀 Quick Start

### Prerequisites
- **Node.js**: v18.x or higher
- **Python**: 3.11 or higher
- **uv**: Python package manager (install: `pip install uv`)
- **PostgreSQL**: 14 or higher (for production)

---

## 📦 Installation

### Frontend Setup
```bash
cd frontend
npm install
```

### Backend Setup
```bash
cd backend
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

---

## 🏃 Development

### Start Development Servers

#### Frontend (Next.js)
```bash
cd frontend
npm run dev
# Server runs at: http://localhost:3002
```

#### Backend (FastAPI)
```bash
cd backend
source .venv/bin/activate  # If not already activated
uv run uvicorn app.main:app --reload --port 8000
# API runs at: http://localhost:8000
# API docs: http://localhost:8000/docs
```

---

## 🧪 Testing

### Frontend Tests

#### Run All Tests
```bash
cd frontend
npm test
```

#### Run Tests with Coverage
```bash
npm run test:coverage
```

#### Watch Mode (Development)
```bash
npm test -- --watch
```

### Backend Tests

#### Run All Tests
```bash
cd backend
uv run pytest
```

#### Run Specific Test File
```bash
uv run pytest tests/test_services/test_ai_service_draft_generation.py -v
```

#### Run with Coverage
```bash
uv run pytest --cov=app tests/ --cov-report=term-missing
```

---

## 🔍 Code Quality

### Frontend

#### Type Checking
```bash
cd frontend
npm run typecheck
```

#### Linting
```bash
npm run lint
```

#### Auto-fix Lint Issues
```bash
npm run lint -- --fix
```

### Backend

#### Format Code (Ruff)
```bash
cd backend
uv run ruff format .
```

#### Check Code Style (Ruff)
```bash
uv run ruff check .
```

#### Type Checking (mypy)
```bash
uv run mypy app/
```

---

## 🏗️ Build

### Frontend Production Build
```bash
cd frontend
npm run build
```

### Frontend Production Start
```bash
npm start
```

---

## 🗄️ Database

### Run Migrations (Alembic)
```bash
cd backend
uv run alembic upgrade head
```

### Create New Migration
```bash
uv run alembic revision --autogenerate -m "Description of changes"
```

### Rollback Migration
```bash
uv run alembic downgrade -1
```

---

## 🔐 Environment Variables

### Frontend (.env.local)
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# Authentication (Clerk)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# Optional: AWS Transcribe
NEXT_PUBLIC_AWS_REGION=us-east-1
NEXT_PUBLIC_AWS_ACCESS_KEY_ID=...
NEXT_PUBLIC_AWS_SECRET_ACCESS_KEY=...
```

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/autoauthor

# Authentication
CLERK_JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----
...
-----END PUBLIC KEY-----

# OpenAI
OPENAI_API_KEY=sk-...

# AWS (Optional)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Storage
FILE_STORAGE_PATH=/path/to/storage
CLOUD_STORAGE_ENABLED=false
```

---

## 🚢 Production Deployment

### Frontend (Vercel/Netlify)

#### Build Command
```bash
npm run build
```

#### Start Command
```bash
npm start
```

#### Environment Variables
Set all `NEXT_PUBLIC_*` variables in deployment platform.

### Backend (Docker)

#### Build Image
```bash
cd backend
docker build -t auto-author-backend .
```

#### Run Container
```bash
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e OPENAI_API_KEY=sk-... \
  --name auto-author-backend \
  auto-author-backend
```

---

## 🔧 Troubleshooting

### Frontend Issues

#### Port Already in Use
```bash
# Kill process on port 3002
lsof -ti:3002 | xargs kill -9
```

#### Module Not Found
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

#### Type Errors in Tests
These are known non-blocking errors in test files. Production code passes type checking.

### Backend Issues

#### Database Connection Failed
1. Verify PostgreSQL is running: `pg_isready`
2. Check DATABASE_URL in .env
3. Ensure database exists: `createdb autoauthor`

#### Import Errors
```bash
cd backend
source .venv/bin/activate
uv pip install -r requirements.txt
```

#### Pydantic V2 Warnings
These are deprecation warnings from dependencies and can be ignored.

---

## 📊 Performance Monitoring

### Frontend Performance

#### Lighthouse Audit
```bash
# Install globally
npm install -g lighthouse

# Run audit
lighthouse http://localhost:3002 --view
```

#### Bundle Analysis
```bash
cd frontend
npm run build
# Review .next/analyze/ directory
```

### Backend Performance

#### Request Profiling
```bash
# Add profiling middleware (dev only)
# Results logged to console
```

---

## 🔐 Security

### Frontend Security Audit
```bash
cd frontend
npm audit
npm audit fix
```

### Backend Security Audit
```bash
cd backend
uv pip install safety
uv run safety check
```

---

## 📝 Logs

### Frontend Logs
- **Development**: Console output
- **Production**: Check platform-specific logs (Vercel/Netlify)

### Backend Logs
- **Development**: Console output with colored formatting
- **Production**: Structured JSON logs to stdout

---

## 🆘 Support

### Common Issues
- See `CLAUDE.md` for development guidelines
- See `IMPLEMENTATION_PLAN.md` for current project status
- See `claudedocs/` for detailed technical documentation

### Getting Help
1. Check existing documentation
2. Review closed issues in GitHub
3. Check test files for usage examples
4. Consult API documentation at `/docs` endpoint

---

## 📚 Additional Resources

### Documentation
- **API Documentation**: http://localhost:8000/docs (FastAPI auto-generated)
- **Component Docs**: See `frontend/src/components/README.md`
- **Architecture**: See `claudedocs/architecture.md`

### Tools
- **Database GUI**: pgAdmin, DBeaver, TablePlus
- **API Testing**: Postman, Insomnia, Thunder Client
- **Performance**: Chrome DevTools, React DevTools, Redux DevTools

---

**Maintained By**: Development Team
**Review Frequency**: As needed (when deployment changes)
**Last Review**: 2025-10-12
