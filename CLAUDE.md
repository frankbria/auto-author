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

## Project Management with Backlog.md

This project uses [Backlog.md](https://github.com/frankbria/Backlog.md) for task management and documentation. The CLI tool manages development tasks and project documentation within the Git repository.

### Task Management Commands
- **Initialize project**: `backlog init` (sets up .backlog/ directory)
- **Create task**: `backlog task create "Task title"`
  - Add metadata: description, assignee, status, labels, priority
  - Create subtasks and dependencies
- **List tasks**: `backlog task list` (filter by status, assignee, labels)
- **View Kanban board**: `backlog browser` (interactive web interface)
- **Export board**: `backlog board export` (markdown format)

### Documentation Commands  
- **Create document**: `backlog doc create "Document title"`
- **List documents**: `backlog doc list`
- **View document**: `backlog doc view <doc-id>`

### AI Agent Guidelines for Backlog Management
When working on this project, AI agents should:

1. **Review Existing Tasks**: Before starting work, check current tasks with `backlog task list`
2. **Create Tasks for New Features**: When implementing new features or fixing bugs:
   ```bash
   backlog task create "Feature: Add user authentication"
   # Add description, set priority, assign labels
   ```
3. **Update Task Status**: Move tasks through workflow (backlog → in-progress → completed)
4. **Document Decisions**: Create architecture decision records and technical documentation:
   ```bash
   backlog doc create "ADR: Database Migration Strategy"
   backlog doc create "API Design Guidelines"
   ```
5. **Link Related Work**: Reference task IDs in commit messages and PRs
6. **Export Progress**: Generate status reports for reviews: `backlog board export`

### Backlog Integration Workflow
1. Check existing tasks before starting new work
2. Create task for significant changes (features, refactoring, bug fixes)
3. Move task to "in-progress" when starting work
4. Document architectural decisions and technical choices
5. Update task status and add completion notes
6. Export board for sprint reviews and planning

### Task Categories and Labels
Use consistent labels for better organization:
- `frontend`, `backend`, `docs`, `tests`, `infrastructure`
- `bug`, `feature`, `enhancement`, `refactor`
- `high-priority`, `medium-priority`, `low-priority`
- `sprint-current`, `sprint-next`, `backlog`

## Testing
- Backend tests are in `backend/tests/`
- Frontend tests are in `frontend/src/__tests__/`
- Use pytest for backend, Jest for frontend
- Always run tests after making changes
- Maintain 80%+ test coverage for new features

## Key Features
- Book creation and metadata management
- **Book deletion with confirmation** (requires typing exact title)
- Chapter editing with rich text editor (TipTap)
- Table of contents generation with AI wizard
- Question generation system for content development
- User authentication with Clerk
- File upload for book covers
- **Export functionality** (PDF/DOCX with customizable options)
- **Unified error handling** with automatic retry logic

## Current Implementation Status

### ✅ Completed Features
- User authentication (Clerk integration)
- Book CRUD operations with metadata
- **Book Deletion UI** (Type-to-confirm with comprehensive data loss warnings)
- TOC generation with AI wizard
- Chapter tabs interface (vertical layout)
- Question-based content creation system
- **Rich Text Editor** (TipTap with full formatting capabilities)
- **AI Draft Generation** (Q&A to narrative with multiple writing styles)
- **Voice Input Integration** (Browser Speech API - production ready)
- **Export functionality** (PDF/DOCX with customizable options)
- Auto-save functionality (3-second debounce)
- Character count and save status indicators
- **Comprehensive test infrastructure** (100% backend tests passing, 11 skipped)
- **E2E Test Suite** (Complete workflow validation from book creation to draft generation)
- Production-ready file storage (local/cloud with automatic fallback)
- AWS Transcribe integration (optional, with graceful fallback)
- Chapter access logging and analytics
- Chapter status workflow (draft → in-progress → completed → published)

### 🚧 In Progress (High Priority)
1. **Export UI Enhancement** - Add prominent Export button to book detail page
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
3. ✅ Complete test coverage - DONE (100% backend tests passing)
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

## Component Documentation

### Book Deletion UI

**Location**: `frontend/src/components/books/DeleteBookModal.tsx`

**Description**: A comprehensive deletion confirmation modal that prevents accidental book deletion through a type-to-confirm pattern.

**Key Features**:
- **Type-to-Confirm**: Users must type the exact book title (case-sensitive) to enable deletion
- **Data Loss Warnings**: Displays comprehensive warnings about what will be permanently deleted
- **Book Statistics**: Shows chapter count and word count before deletion
- **Loading States**: Disables all controls during deletion operation
- **Prevention Mechanisms**: Blocks modal closure during deletion, prevents escape key and outside clicks
- **Accessibility**: Full ARIA label support, keyboard navigation, autofocus on input field

**Usage Example**:
```tsx
import { DeleteBookModal } from '@/components/books';

<DeleteBookModal
  isOpen={showDeleteDialog}
  onOpenChange={setShowDeleteDialog}
  bookTitle={book.title}
  bookStats={{
    chapterCount: book.chapters,
    wordCount: book.word_count ?? 0,  // Optional field with null coalescing
  }}
  onConfirm={handleDeleteBook}
  isDeleting={isDeleting}
/>
```

**Props**:
- `isOpen: boolean` - Controls modal visibility
- `onOpenChange: (open: boolean) => void` - Callback when modal open state changes
- `bookTitle: string` - Title of book to delete (used for confirmation)
- `bookStats?: { chapterCount: number; wordCount: number }` - Optional statistics to display
  - Note: `word_count` field may be null/undefined on Book objects; use null coalescing (`?? 0`)
- `onConfirm: () => void | Promise<void>` - Callback when user confirms deletion
- `isDeleting?: boolean` - Loading state during deletion

**Test Coverage**: 86.2% overall, 91.66% for DeleteBookModal.tsx (29 tests, 100% pass rate)

**Integration Points**:
- Dashboard book cards (BookCard.tsx) - Delete button with trash icon
- Book detail page (future enhancement)

**Error Handling**:
- Parent component handles deletion errors
- Toast notifications for success/failure
- Network error retry via parent logic

---

## Feature Development Quality Standards

**CRITICAL**: All new features MUST meet the following mandatory requirements before being considered complete.

### Testing Requirements

- **Minimum Coverage**: 85% code coverage ratio required for all new code
- **Test Pass Rate**: 100% - all tests must pass, no exceptions
- **Test Types Required**:
  - Unit tests for all business logic and services
  - Integration tests for API endpoints
  - End-to-end tests for critical user workflows
- **Coverage Validation**: Run coverage reports before marking features complete:
  ```bash
  # Backend
  cd backend && uv run pytest --cov=app tests/ --cov-report=term-missing
  
  # Frontend
  cd frontend && npm run test:coverage
  ```
- **Test Quality**: Tests must validate behavior, not just achieve coverage metrics
- **Test Documentation**: Complex test scenarios must include comments explaining the test strategy

### Git Workflow Requirements

Before moving to the next feature, ALL changes must be:

1. **Committed with Clear Messages**:
   ```bash
   git add .
   git commit -m "feat(module): descriptive message following conventional commits"
   ```
   - Use conventional commit format: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, etc.
   - Include scope when applicable: `feat(backend):`, `fix(frontend):`, `test(auth):`
   - Write descriptive messages that explain WHAT changed and WHY

2. **Pushed to Remote Repository**:
   ```bash
   git push origin <branch-name>
   ```
   - Never leave completed features uncommitted
   - Push regularly to maintain backup and enable collaboration
   - Ensure CI/CD pipelines pass before considering feature complete

3. **Branch Hygiene**:
   - Work on feature branches, never directly on `main`
   - Branch naming convention: `feature/<feature-name>`, `fix/<issue-name>`, `docs/<doc-update>`
   - Create pull requests for all significant changes

4. **Backlog Integration**:
   - Create or update tasks in Backlog.md before starting work
   - Move tasks to "in-progress" when beginning implementation
   - Update task status upon completion
   - Reference task IDs in commit messages

### Documentation Requirements

**ALL implementation documentation MUST remain synchronized with the codebase**:

1. **API Documentation**:
   - Update OpenAPI specifications when endpoints change
   - Document all request/response schemas
   - Include example requests and responses
   - Document error responses and status codes

2. **Code Documentation**:
   - Python: Docstrings for all public functions, classes, and modules
   - TypeScript: JSDoc comments for complex functions and components
   - Update inline comments when implementation changes
   - Remove outdated comments immediately

3. **Implementation Documentation**:
   - Update relevant sections in this CLAUDE.md file
   - Update IMPLEMENTATION_PLAN.md when scope changes
   - Keep architecture diagrams current
   - Update configuration examples when defaults change
   - Document breaking changes prominently

4. **README Updates**:
   - Keep feature lists current
   - Update setup instructions when dependencies change
   - Maintain accurate command examples
   - Update version compatibility information

5. **Backlog Documentation**:
   - Create architecture decision records for significant changes
   - Document technical choices and trade-offs
   - Update task descriptions with implementation notes
   - Export board status for sprint reviews

### Feature Completion Checklist

Before marking ANY feature as complete, verify:

- [ ] All tests pass (backend and frontend)
- [ ] Code coverage meets 85% minimum threshold
- [ ] Coverage report reviewed for meaningful test quality
- [ ] Code formatted and linted (ruff, ESLint)
- [ ] Type checking passes (mypy for Python, tsc for TypeScript)
- [ ] All changes committed with conventional commit messages
- [ ] All commits pushed to remote repository
- [ ] Backlog task status updated to completed
- [ ] API documentation updated (if applicable)
- [ ] Implementation documentation updated
- [ ] Inline code comments updated or added
- [ ] CLAUDE.md updated (if new patterns introduced)
- [ ] Breaking changes documented
- [ ] Security considerations reviewed
- [ ] Performance impact assessed
- [ ] CI/CD pipeline passes

### Rationale

These standards ensure:
- **Quality**: High test coverage and pass rates prevent regressions
- **Traceability**: Git commits and Backlog integration provide clear history of changes
- **Maintainability**: Current documentation reduces onboarding time and prevents knowledge loss
- **Collaboration**: Pushed changes and task management enable team visibility and code review
- **Reliability**: Consistent quality gates maintain production stability

**Enforcement**: AI agents should automatically apply these standards to all feature development tasks without requiring explicit instruction for each task.
