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
- **Rich Text Editor** (TipTap with full formatting capabilities)
- **AI Draft Generation** (Q&A to narrative with multiple writing styles)
- **Voice Input Integration** (Browser Speech API - production ready)
- **Export functionality** (PDF/DOCX with customizable options)
- Auto-save functionality (3-second debounce)
- Character count and save status indicators
- Comprehensive test infrastructure (92.4% pass rate)
- Production-ready file storage (local/cloud with automatic fallback)
- AWS Transcribe integration (optional, with graceful fallback)

### 🚧 In Progress (High Priority)
1. **Test Coverage** - Fix remaining 20 tests for 100% pass rate
2. **Production Deployment** - Infrastructure and CI/CD setup
3. **Security Hardening** - Security audit and implementation

### 📋 Planned Features
- Collaborative editing
- Advanced AI features (style suggestions, grammar check)
- EPUB export format
- Mobile companion app
- Performance optimizations
- Enhanced export UI discoverability

## Implementation Priorities

### Sprint 1-2: ✅ MVP COMPLETED
All core authoring workflow features are implemented:
1. ✅ Rich text editor (TipTap) - DONE
2. ✅ AI draft generation integration - DONE
3. ✅ Production services (no mocks in production) - DONE

### Sprint 3-4: Production Ready (CURRENT)
Focus on production readiness and quality:
1. ✅ Voice input - DONE (Browser Speech API)
2. ✅ Export functionality - DONE (PDF/DOCX)
3. 🚧 Complete test coverage (currently at 92.4%)
4. 🚧 Security hardening and audit
5. 🚧 Production infrastructure setup
6. 🚧 Performance optimization

### Sprint 5-6: Enhanced Features
Add collaborative and advanced features:
1. Collaborative editing (real-time collaboration)
2. Advanced AI features (style suggestions, grammar check, content analysis)
3. Additional export formats (EPUB, Markdown)
4. Enhanced analytics and progress tracking
5. Version control for chapters

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