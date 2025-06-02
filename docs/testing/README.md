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
python -m pytest                    # Run all tests
python -m pytest --cov             # Coverage report
python -m pytest -v tests/unit/    # Unit tests only
python -m pytest tests/integration/ # Integration tests only
```

## Documentation Structure

- **[Setup Guide](./setup-guide.md)** - Environment setup and configuration
- **[Best Practices](./best-practices.md)** - Testing guidelines and standards
- **[Test Architecture](./test-architecture.md)** - Testing strategy and structure
- **[Troubleshooting](./troubleshooting.md)** - Common issues and solutions
- **[Performance Testing](./performance-testing.md)** - Load and performance testing
- **[Accessibility Testing](./accessibility-testing.md)** - Accessibility compliance testing
- **[Mobile Testing](./mobile-testing.md)** - Mobile and responsive testing
- **[CI/CD Integration](./cicd-integration.md)** - Continuous integration setup
- **[Test Data Management](./test-data-management.md)** - Test data and fixtures

## Test Coverage

### Current Coverage Targets
- **Unit Tests**: 90% minimum
- **Integration Tests**: 85% minimum
- **E2E Critical Paths**: 100%
- **API Endpoints**: 95% minimum

### Coverage Reports
- Frontend: `frontend/coverage/`
- Backend: `backend/htmlcov/`

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
- **Factory Boy**: Test data generation
- **Pytest-mock**: Mocking utilities

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
python -m pytest tests/test_api/

# Integration Tests
python -m pytest tests/integration/

# Chapter Questions Tests
python -m pytest tests/integration/test_chapter_questions_integration.py

# Chapter Tabs Tests
python -m pytest tests/integration/run_test_chapter_tabs_integration.py
```

## Test Environment Variables

Create `.env.test` files for test-specific configuration:

### Frontend (.env.test)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=test_key
NODE_ENV=test
```

### Backend (.env.test)
```bash
DATABASE_URL=sqlite:///test.db
OPENAI_API_KEY=test_key
ANTHROPIC_API_KEY=test_key
ENVIRONMENT=test
```

## Continuous Integration

Tests are automatically run on:
- Pull requests
- Pushes to main branch
- Scheduled nightly runs

See [CI/CD Integration](./cicd-integration.md) for detailed configuration.

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure coverage meets minimum requirements
3. Update documentation as needed
4. Run full test suite before submitting PR

## Support

For testing-related questions:
- Check [Troubleshooting Guide](./troubleshooting.md)
- Review [Best Practices](./best-practices.md)
- Consult existing test examples in the codebase
