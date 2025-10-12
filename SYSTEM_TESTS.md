# Auto Author System Tests

This document describes the complete end-to-end system tests that validate the core functionality of the Auto Author application.

## Overview

We have created multiple system tests that validate the complete authoring workflow from book creation through chapter draft generation using real AI services. These tests ensure that all core components are working together properly.

## Available System Tests

### 1. Jest Integration Test (Frontend)
**Location:** `/frontend/src/__tests__/SystemIntegration.test.tsx`

This test uses Jest and makes real API calls to validate the workflow.

**Run Command:**
```bash
cd frontend
npm run test:system
```

### 2. Playwright E2E Test (Frontend)
**Location:** `/frontend/src/__tests__/e2e/SystemE2E.test.tsx`

This test uses Playwright to simulate user interactions in a real browser.

**Run Command:**
```bash
cd frontend
npm run test:e2e
```

### 3. Node.js Script Test
**Location:** `/frontend/scripts/system-test.js`

A standalone Node.js script that can be run independently.

**Run Command:**
```bash
cd frontend
node scripts/system-test.js [--cleanup]
```

Options:
- `--cleanup`: Delete test data after completion

### 4. Python Backend Test
**Location:** `/backend/tests/test_system_e2e.py`

Backend-focused system test using pytest.

**Run Command:**
```bash
cd backend
uv run pytest tests/test_system_e2e.py -v -s
```

## Test Workflow

All system tests follow the same core workflow:

1. **Create Book** - Create a non-fiction book with title and summary
2. **Generate Book Questions** - AI generates questions about the book concept
3. **Answer Book Questions** - Provide answers to clarify book details
4. **Generate TOC** - AI creates a Table of Contents based on answers
5. **Create Chapters** - Convert TOC into chapter structure
6. **Generate Chapter Questions** - AI generates questions for Chapter 1
7. **Answer Chapter Questions** - Provide detailed answers about chapter content
8. **Generate Draft** - AI generates chapter draft from answers
9. **Verify System** - Confirm all components worked correctly

## Prerequisites

### Backend Requirements
- Backend server running on `http://localhost:8000`
- Valid OpenAI API key configured
- Database accessible

### Frontend Requirements
- Frontend dev server running on `http://localhost:3000`
- Clerk authentication configured (or in dev mode)

### Environment Variables
```bash
# Backend
OPENAI_API_KEY=your-key-here

# Frontend (if needed)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your-key
CLERK_SECRET_KEY=your-key
```

## Running All Tests

To run a complete system validation:

1. **Start Backend:**
   ```bash
   cd backend
   uv run uvicorn app.main:app --reload
   ```

2. **Start Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Run Tests:**
   ```bash
   # Quick smoke test
   cd frontend
   node scripts/system-test.js --cleanup

   # Full integration test
   npm run test:system

   # Browser E2E test
   npm run test:e2e
   ```

## Expected Results

A successful test run should:
- Create a book with metadata
- Generate 3-5 book-level questions
- Generate a TOC with 10+ chapters
- Generate 3-5 questions for Chapter 1
- Generate a draft with 1000+ characters
- Complete in under 5 minutes

## Troubleshooting

### Common Issues

1. **API Timeout Errors**
   - Ensure OpenAI API key is valid
   - Check network connectivity
   - Increase timeout values if needed

2. **Authentication Errors**
   - Ensure Clerk is configured properly
   - Use test/dev mode for automated tests

3. **Database Errors**
   - Ensure database migrations are current
   - Check database connectivity

### Debug Mode

For more verbose output:
```bash
# Node.js script
DEBUG=* node scripts/system-test.js

# Jest test
npm run test:system -- --verbose

# Pytest
pytest tests/test_system_e2e.py -v -s --log-cli-level=DEBUG
```

## Maintenance

These tests should be run:
- Before each deployment
- After major feature changes
- As part of CI/CD pipeline
- Weekly for production validation

Keep tests updated when:
- API contracts change
- New features are added
- UI workflows are modified