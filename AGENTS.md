# AGENTS.md - Auto-Author Development Guide

## Build/Test Commands
**Backend (Python/FastAPI)**: `cd backend && uv run pytest` | Single test: `uv run pytest tests/test_file.py::test_function`
**Frontend (Next.js)**: `cd frontend && npm test` | Single test: `npm test -- --testNamePattern="test name"`
**Lint**: Backend: `uv run ruff check . && uv run ruff format .` | Frontend: `npm run lint && npm run type-check`
**Dev servers**: Backend: `uv run uvicorn app.main:app --reload` | Frontend: `npm run dev`

## Code Style Guidelines
- **Python**: Use Pydantic models, async/await, type hints, snake_case. Import order: stdlib, third-party, local
- **TypeScript**: Strict types, JSDoc for complex logic, PascalCase components, camelCase variables
- **Error handling**: Use try/catch blocks, proper HTTP status codes, detailed error messages
- **File naming**: kebab-case for components, snake_case for Python modules
- **Testing**: 80% coverage minimum, descriptive test names, arrange-act-assert pattern

## Project Rules (from .roo/rules)
- **Simplicity**: Clear, maintainable solutions over complexity
- **Focus**: Stick to defined tasks, avoid scope creep
- **Quality**: Clean, tested, documented, secure code
- **No comments**: Code should be self-documenting unless complex logic requires clarification
- **DRY principle**: Use symbolic reasoning to identify and eliminate redundancy
- **File limits**: Keep files under 300 lines, refactor when needed
- **Security**: Server-side validation, no hardcoded credentials, input sanitization