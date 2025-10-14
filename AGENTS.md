# AGENTS.md - Auto-Author Development Guide

## Build/Test Commands
**Backend (Python/FastAPI)**:
- Run tests: `cd backend && uv run pytest`
- With coverage: `uv run pytest --cov=app tests/ --cov-report=term-missing`
- Single test: `uv run pytest tests/test_file.py::test_function`
- Dev server: `uv run uvicorn app.main:app --reload`

**Frontend (Next.js)**:
- Run tests: `cd frontend && npm test`
- With coverage: `npm run test:coverage`
- Single test: `npm test -- --testNamePattern="test name"`
- E2E tests: `npx playwright test` (requires both servers running)
- Dev server: `npm run dev`

**Lint & Format**:
- Backend: `uv run ruff check . && uv run ruff format .`
- Frontend: `npm run lint && npm run type-check`

## Code Style Guidelines
- **Python**: Use Pydantic models, async/await, type hints, snake_case. Import order: stdlib, third-party, local
- **TypeScript**: Strict types, JSDoc for complex logic, PascalCase components, camelCase variables
- **Error handling**: Use try/catch blocks, proper HTTP status codes, detailed error messages, automatic retry for transient errors
- **File naming**: kebab-case for components, snake_case for Python modules
- **Testing**: 85% coverage minimum for new code, descriptive test names, arrange-act-assert pattern
- **UI Components**: Use shadcn/ui, ensure WCAG 2.1 accessibility compliance, implement loading states
- **Performance**: Track operations with budgets (TOC: 3000ms, Export: 5000ms, Auto-save: 1000ms)

## Quality Standards (MANDATORY)
- **Test Coverage**: 85% minimum for all new code, 100% pass rate required
- **Git Workflow**: Conventional commits, feature branches, never commit directly to main
- **Documentation**: Update API docs, code comments, and implementation docs with every change
- **Performance Budgets**: All operations must meet defined time budgets or log warnings
- **Accessibility**: All interactive elements must be keyboard accessible (WCAG 2.1)

## Project Rules & Development Standards
- **Simplicity**: Clear, maintainable solutions over complexity
- **Focus**: Stick to defined tasks, avoid scope creep
- **Quality**: Clean, tested, documented, secure code
- **Self-documenting code**: Minimize comments unless complex logic requires clarification
- **DRY principle**: Use symbolic reasoning to identify and eliminate redundancy
- **File limits**: Keep files under 300 lines (500 for components), refactor when needed
- **Security**: Server-side validation, no hardcoded credentials, input sanitization from the start

## Feature Completion Checklist
Before marking ANY feature complete:
- [ ] All tests pass (100% pass rate)
- [ ] Code coverage meets 85% minimum
- [ ] Code formatted and linted
- [ ] Type checking passes
- [ ] All changes committed with conventional messages
- [ ] Changes pushed to remote repository
- [ ] API documentation updated (if applicable)
- [ ] Performance impact assessed
- [ ] Accessibility verified (WCAG 2.1)
- [ ] Error handling implemented

## Key Development Tools
- **Testing**: pytest (backend), Vitest (frontend), Playwright (E2E)
- **Error Handling**: Unified error handler with exponential backoff retry
- **Performance**: `usePerformanceTracking` hook with operation budgets
- **Loading States**: `LoadingStateManager` and `ProgressIndicator` components
- **Test Helpers**: Condition-based waiting, API-based test data factories
