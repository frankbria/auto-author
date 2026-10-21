# Testing Documentation

This directory contains comprehensive testing documentation for the Auto-Author application.

## Overview

The Auto-Author project implements a multi-layered testing strategy covering:

- **Unit Tests**: Individual component and function testing
- **Integration Tests**: Cross-service and database interaction testing
- **End-to-End Tests**: Complete user workflow testing
- **Performance Tests**: Load, stress, and benchmark testing
- **Accessibility Tests**: Screen reader, keyboard navigation, and ARIA compliance
- **Mobile Tests**: Touch interactions and responsive design testing

## Quick Start

### Frontend Testing
```bash
cd frontend
npm test                 # Run all tests
npm run test:watch      # Watch mode
npm run test:coverage   # Coverage report
```

### Backend Testing
```bash
cd backend
uv sync --extra test                # one-time; test tooling is in the `test` extra
uv run pytest                       # Run all tests (needs MongoDB on localhost:27017)
uv run pytest --cov=app             # Coverage report
uv run pytest tests/integration/    # Integration tests only
```

## Documentation Structure

- **[Setup Guide](./setup-guide.md)** - Environment setup and configuration
- **[Best Practices](./best-practices.md)** - Testing guidelines and standards
- **[Editing and Auto-save E2E Flow](./e2e-editing-autosave-flow.md)** - The editing and auto-save end-to-end flow
- **[Accessibility Testing](../development/accessibility-testing.md)** - Accessibility compliance testing

## Test Coverage

### Coverage gates
CI (`.github/workflows/tests.yml`) and the pre-commit hooks enforce:
- **Backend**: 85% (`--cov-fail-under=85`)
- **Frontend**: 85% lines, 85% statements, 75% branches, 85% functions

### Coverage Reports
- Frontend: `frontend/coverage/`
- Backend: `uv run pytest --cov=app --cov-report=html` writes `backend/htmlcov/`

## Tools and Frameworks

### Frontend
- **Jest**: Test runner and framework
- **React Testing Library**: Component testing
- **Jest-DOM**: DOM testing utilities
- **User Event**: User interaction simulation

### Backend
- **Pytest**: Test runner and framework
- **Pytest-asyncio**: Async testing support
- **Pytest-cov**: Coverage reporting
- **HTTPX**: test client for the API
- **Pytest-mock**: Mocking utilities
- **Jest-axe** (frontend): automated accessibility checks

## Test Categories

### 1. Unit Tests
- Component rendering
- Function logic
- State management
- Error handling

### 2. Integration Tests
- API integration
- Database operations
- Service communication
- Authentication flows

### 3. End-to-End Tests
- Complete user workflows
- Cross-browser compatibility
- Mobile responsiveness
- Error recovery

### 4. Performance Tests
- Load testing
- Memory usage
- Response times
- Concurrency handling

### 5. Accessibility Tests
- Screen reader compatibility
- Keyboard navigation
- ARIA compliance
- Color contrast

## Running Specific Test Suites

### Frontend
```bash
# Chapter Questions E2E Tests
npm test ChapterQuestionsEndToEnd

# Mobile/Accessibility Tests
npm test ChapterQuestionsMobileAccessibility

# Performance Tests
npm test ChapterQuestionsPerformance

# Integration Tests
npm test ChapterTabsTocIntegration
```

### Backend
```bash
# API Tests
uv run pytest tests/test_api/

# Integration Tests
uv run pytest tests/integration/

# Chapter Questions Tests
uv run pytest tests/integration/test_chapter_questions_integration.py

# Chapter Tabs Tests
uv run pytest tests/integration/test_chapter_tabs_integration.py
```

## Test Environment

There is no `.env.test` file. `backend/tests/conftest.py` sets `ENVIRONMENT=test` and talks to a real MongoDB at `TEST_MONGO_URI` (default `mongodb://localhost:27017/auto-author-test`). The fixtures drop that database before and after each test, so the guard in `backend/tests/db_guard.py` refuses a URI that is not clearly a local test database. Frontend tests need no environment file; `src/jest.setup.ts` configures jsdom.

## Continuous Integration

Tests are automatically run on:
- Pull requests
- Pushes to main branch

The workflows are in [`.github/workflows/`](../../.github/workflows/); `tests.yml` runs the frontend and backend suites with the coverage gates, a Playwright E2E job and the security audit. Staging E2E runs after each staging deploy (`e2e-staging-tests.yml`).

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure coverage meets minimum requirements
3. Update documentation as needed
4. Run full test suite before submitting PR

## Support

For testing-related questions:
- Review [Best Practices](./best-practices.md)
- Consult existing test examples in the codebase
