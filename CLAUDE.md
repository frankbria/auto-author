# Claude Development Instructions

This is a monorepo for the auto-author project with a Next.js frontend and FastAPI backend.

## Project Structure
- `frontend/` - Next.js application
- `backend/` - FastAPI Python application
- `docs/` - Project documentation

## Development Commands

### Backend (FastAPI)
- **Setup**: `cd backend && uv venv && source .venv/bin/activate && uv pip install -r requirements.txt`
- **Start server**: `cd backend && uv run uvicorn app.main:app --reload`
- **Run tests**: `cd backend && uv run pytest`
- **Quick validation**: `cd backend && uv run python quick_validate.py`
- **Lint/Format**: `cd backend && uv run ruff check . && uv run ruff format .`

### Frontend (Next.js)
- **Start dev server**: `cd frontend && npm run dev`
- **Run tests**: `cd frontend && npm test`
- **Build**: `cd frontend && npm run build`
- **Lint**: `cd frontend && npm run lint`
- **Type check**: `cd frontend && npm run type-check`

## Testing
- Backend tests are in `backend/tests/`
- Frontend tests are in `frontend/src/__tests__/`
- Use pytest for backend, Jest for frontend
- Always run tests after making changes
- Maintain 80%+ test coverage for new features

## Key Features
- Book creation and metadata management
- Chapter editing with rich text editor
- Table of contents generation
- Question generation system
- User authentication with Clerk
- File upload for book covers

## Current Implementation Status

### ✅ Completed Features
- User authentication (Clerk integration)
- Book CRUD operations with metadata
- TOC generation with AI wizard
- Chapter tabs interface (vertical layout)
- Question-based content creation system
- Basic test infrastructure

### 🚧 In Progress (High Priority)
1. **Rich Text Editor** - Chapter content editing capability
2. **AI Draft Generation** - Connect AI service for Q&A to narrative
3. **Voice Input Integration** - Production speech-to-text service
4. **Mock Service Replacement** - Real transcription and file storage

### 📋 Planned Features
- Export functionality (PDF/DOCX)
- Collaborative editing
- Advanced AI features
- Mobile companion app

## Implementation Priorities

### Sprint 1-2: MVP Completion
Focus on completing the core authoring workflow:
1. Implement rich text editor (TipTap recommended)
2. Complete AI draft generation integration
3. Replace mock services with production implementations

### Sprint 3-4: Enhanced UX
Polish and improve reliability:
1. Voice input integration across all text areas
2. Basic export functionality
3. Comprehensive error handling

### Sprint 5: Production Ready
Security and performance:
1. Security hardening and audit
2. Performance optimization
3. Production infrastructure setup

## Development Guidelines

### Code Quality Standards
- Write clean, self-documenting code
- Follow existing patterns and conventions
- Implement proper error handling
- Add comprehensive logging
- Maintain backward compatibility

### Testing Requirements
- Unit tests: 80% minimum coverage
- Integration tests for critical flows
- E2E tests for happy paths
- Performance benchmarks for new features
- Security testing for sensitive operations

### Security Considerations
- Always validate and sanitize user input
- Use proper authentication checks
- Implement rate limiting for expensive operations
- Encrypt sensitive data
- Follow OWASP guidelines

### Performance Guidelines
- Optimize database queries
- Implement proper caching strategies
- Use lazy loading where appropriate
- Monitor bundle sizes
- Profile and optimize bottlenecks

## Important Notes
- Always run linting and type checking before committing
- Follow existing code conventions in each directory
- Check documentation in `docs/` for specific feature guides
- Review IMPLEMENTATION_PLAN.md for detailed sprint planning
- Test coverage must meet 80% threshold before merging