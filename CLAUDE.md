# Claude Code Configuration - SPARC Development Environment

## 🚨 CRITICAL: CONCURRENT EXECUTION & FILE MANAGEMENT

**ABSOLUTE RULES**:
1. ALL operations MUST be concurrent/parallel in a single message
2. **NEVER save working files, text/mds and tests to the root folder**
3. ALWAYS organize files in appropriate subdirectories

## Project Structure
- `frontend/` - Next.js application
- `backend/` - FastAPI Python application
- `docs/` - Project documentation
- `claudedocs/` - Claude-specific analysis reports and detailed plans
- `archive/` - Historical planning documents (read-only)

## Documentation Management

### Document Hierarchy (Single Source of Truth)

**Active Documents** (always current):
- **IMPLEMENTATION_PLAN.md** - Master implementation roadmap (single source of truth)
- **CURRENT_SPRINT.md** - Current sprint tasks and daily progress
- **CLAUDE.md** - This file - development guidelines and standards

**Detailed Plans** (reference as needed):
- `claudedocs/QUALITY_MONITORING_IMPLEMENTATION_PLAN.md` - Quality monitoring implementation
- `claudedocs/loading_states_audit_report.md` - Loading state gap analysis

**Historical Reference** (archived):
- `archive/TODO.md` - Legacy task tracking
- `archive/PHASE1_IMPLEMENTATION_PLAN.md` - Phase 1 detailed notes
- `archive/UI_IMPROVEMENTS_TODO.md` - Expert panel requirements
- `archive/KEYBOARD_NAVIGATION_ACTION_PLAN.md` - Accessibility action plan

### Where Should Information Go? Decision Tree

```
New information to document?
│
├─ Is it a development standard or guideline?
│  └─ YES → Update CLAUDE.md
│
├─ Is it current sprint work or daily progress?
│  └─ YES → Update CURRENT_SPRINT.md
│
├─ Is it a feature/sprint implementation plan?
│  └─ YES → Update IMPLEMENTATION_PLAN.md (master plan)
│
├─ Is it detailed technical analysis (>500 lines)?
│  ├─ YES → Create in claudedocs/ with descriptive name
│  └─ AND → Reference from IMPLEMENTATION_PLAN.md
│
├─ Is it completed/obsolete planning info?
│  └─ YES → Move to archive/ directory
│
├─ Is it a task or ADR for Backlog?
│  └─ YES → Use `backlog task create` or `backlog doc create`
│
└─ NOT SURE? → Default to updating IMPLEMENTATION_PLAN.md
```

### Document Type Guidelines

| Document Type | Location | Purpose | Update Frequency |
|--------------|----------|---------|------------------|
| **Development Standards** | CLAUDE.md | Code quality, testing, git workflow, security | Rarely (major policy changes) |
| **Implementation Roadmap** | IMPLEMENTATION_PLAN.md | Sprint plans, feature specs, timelines | Weekly (sprint planning) |
| **Current Work** | CURRENT_SPRINT.md | Active tasks, daily progress, blockers | Daily (progress updates) |
| **Technical Analysis** | claudedocs/*.md | Detailed audits, gap analysis, designs | As needed (specific analyses) |
| **Architecture Decisions** | Backlog ADRs | Technical choices, trade-offs | Per decision |
| **Historical Plans** | archive/*.md | Completed/obsolete planning docs | Never (read-only) |
| **API Documentation** | Code comments | Endpoint specs, schemas, examples | Per code change |
| **Component Docs** | CLAUDE.md | Reusable component usage patterns | Per component addition |

### Rules for Creating New Documents

**BEFORE creating any new document, answer these questions:**

1. **Does this information belong in an existing document?**
   - Check IMPLEMENTATION_PLAN.md first (90% of planning goes here)
   - Check CURRENT_SPRINT.md for active work
   - Check CLAUDE.md for standards/guidelines

2. **Is this document >500 lines of detailed analysis?**
   - NO → Add to IMPLEMENTATION_PLAN.md or CURRENT_SPRINT.md
   - YES → Consider claudedocs/ but get justification first

3. **Will this document be updated regularly?**
   - YES → Use CURRENT_SPRINT.md (daily) or IMPLEMENTATION_PLAN.md (weekly)
   - NO → Probably doesn't need a separate document

4. **Does this overlap with existing content?**
   - YES → Update existing document, DO NOT create duplicate
   - NO → Proceed with creation (but verify with decision tree)

### AI Agent Instructions: Document Creation Prevention

**CRITICAL RULES FOR AI AGENTS:**

1. **NEVER create a new planning document without explicit user approval**
   - This includes: TODO.md, PLAN.md, ROADMAP.md, TASKS.md, etc.
   - Exception: Files in claudedocs/ for detailed analysis (>500 lines)

2. **ALWAYS check existing documents first**
   ```bash
   # Before creating any document, run:
   ls -la *.md
   ls -la claudedocs/*.md
   ls -la archive/*.md
   ```

3. **DEFAULT to updating IMPLEMENTATION_PLAN.md**
   - When unsure where information goes → IMPLEMENTATION_PLAN.md
   - When planning features → IMPLEMENTATION_PLAN.md
   - When tracking progress → CURRENT_SPRINT.md (if active) or IMPLEMENTATION_PLAN.md

4. **USE Backlog for tasks and ADRs**
   - Task tracking → `backlog task create`
   - Architecture decisions → `backlog doc create "ADR: Title"`
   - NOT separate markdown files in project root

5. **ASK before creating claudedocs/ files**
   - Justify: "This analysis is >500 lines and references specific data"
   - Get user approval before proceeding
   - Always reference from IMPLEMENTATION_PLAN.md

6. **CONSOLIDATE when you find duplicates**
   - If multiple documents cover same topic → merge into master document
   - Move obsolete versions to archive/
   - Update references in other documents

### Document Lifecycle Management

#### When to Archive Documents

Move documents to `archive/` when:
- ✅ All tasks completed and verified
- ✅ Sprint/phase finished and retrospective done
- ✅ Information no longer relevant to current work
- ✅ Superseded by newer planning document
- ✅ >30 days since last update AND not referenced

**Archive Process**:
```bash
# 1. Verify document is truly obsolete
grep -r "DOCUMENT_NAME" *.md claudedocs/*.md

# 2. Move to archive with descriptive name
mv DOCUMENT.md archive/DOCUMENT_$(date +%Y%m%d).md

# 3. Update references in active documents
# 4. Add note in IMPLEMENTATION_PLAN.md if historically significant
```

#### When to Delete Documents (RARE)

Delete documents only when:
- ❌ Duplicate information with no unique content
- ❌ Incorrect/misleading information that was never implemented
- ❌ Test/scratch files accidentally committed

**Deletion requires explicit user approval.**

### Examples of Correct vs Incorrect Behavior

#### ✅ CORRECT: Update Existing Document
```
Situation: User asks to track new feature implementation
AI Action:
1. Check IMPLEMENTATION_PLAN.md for relevant section
2. Update appropriate sprint section with feature details
3. Reference detailed specs if needed from claudedocs/
4. Update CURRENT_SPRINT.md with active tasks
```

#### ❌ INCORRECT: Create New Document
```
Situation: User asks to track new feature implementation
AI Action: Creates "FEATURE_PLAN.md" in project root
Problem: Proliferates documents, creates duplicate information
Fix: Consolidate into IMPLEMENTATION_PLAN.md
```

#### ✅ CORRECT: Detailed Analysis
```
Situation: 800-line security audit with specific vulnerability data
AI Action:
1. Ask user: "This analysis is extensive. Create claudedocs/security_audit_2024.md?"
2. Get approval
3. Create detailed document in claudedocs/
4. Add summary and reference to IMPLEMENTATION_PLAN.md
```

#### ❌ INCORRECT: Small Update as New File
```
Situation: 50-line status update on current sprint
AI Action: Creates "STATUS_UPDATE.md"
Problem: Small updates don't need separate files
Fix: Add to CURRENT_SPRINT.md or IMPLEMENTATION_PLAN.md
```

#### ✅ CORRECT: Consolidation
```
Situation: Discovers 3 files with overlapping TODOs
AI Action:
1. Analyze content overlap
2. Propose consolidation plan to user
3. Merge into IMPLEMENTATION_PLAN.md
4. Archive obsolete documents
5. Update all references
```

### Documentation Quality Standards

All documentation must meet these standards:

1. **Accuracy**: Information reflects current implementation state
2. **Completeness**: No TODOs or incomplete sections in active docs
3. **Consistency**: Terminology and formatting matches project standards
4. **Traceability**: Clear references between related documents
5. **Maintainability**: Easy to find, update, and understand

### Verification Checklist for AI Agents

Before completing any documentation task:

- [ ] Checked all existing documents for relevant content
- [ ] Updated master documents (IMPLEMENTATION_PLAN.md, CURRENT_SPRINT.md, CLAUDE.md)
- [ ] No new documents created without justification and approval
- [ ] All cross-references updated if documents moved/renamed
- [ ] Backlog system used for tasks and ADRs
- [ ] Archive directory contains only historical/completed content
- [ ] Document hierarchy reflects current project structure

### ⚡ GOLDEN RULE: "1 MESSAGE = ALL RELATED OPERATIONS"

**MANDATORY PATTERNS:**
- **TodoWrite**: ALWAYS batch ALL todos in ONE call (5-10+ todos minimum)
- **Task tool**: ALWAYS spawn ALL agents in ONE message with full instructions
- **File operations**: ALWAYS batch ALL reads/writes/edits in ONE message
- **Bash commands**: ALWAYS batch ALL terminal operations in ONE message
- **Memory operations**: ALWAYS batch ALL memory store/retrieve in ONE message

### 📁 File Organization Rules

**NEVER save to root folder. Use these directories:**
- `/src` - Source code files
- `/tests` - Test files
- `/docs` - Documentation and markdown files
- `/config` - Configuration files
- `/scripts` - Utility scripts
- `/examples` - Example code

## Project Overview

This project uses SPARC (Specification, Pseudocode, Architecture, Refinement, Completion) methodology with Claude-Flow orchestration for systematic Test-Driven Development.

## SPARC Commands

### Core Commands
- `npx claude-flow sparc modes` - List available modes
- `npx claude-flow sparc run <mode> "<task>"` - Execute specific mode
- `npx claude-flow sparc tdd "<feature>"` - Run complete TDD workflow
- `npx claude-flow sparc info <mode>` - Get mode details

### Batchtools Commands
- `npx claude-flow sparc batch <modes> "<task>"` - Parallel execution
- `npx claude-flow sparc pipeline "<task>"` - Full pipeline processing
- `npx claude-flow sparc concurrent <mode> "<tasks-file>"` - Multi-task processing

### Build Commands
- `npm run build` - Build project
- `npm run test` - Run tests
- `npm run lint` - Linting
- `npm run typecheck` - Type checking

## SPARC Workflow Phases

1. **Specification** - Requirements analysis (`sparc run spec-pseudocode`)
2. **Pseudocode** - Algorithm design (`sparc run spec-pseudocode`)
3. **Architecture** - System design (`sparc run architect`)
4. **Refinement** - TDD implementation (`sparc tdd`)
5. **Completion** - Integration (`sparc run integration`)

## Key Features
- Book creation and metadata management
- **Book deletion with confirmation** (requires typing exact title)
- Chapter editing with rich text editor (TipTap)
- **Auto-save with localStorage backup** (saves every 3 seconds, backs up on network failure)
- **Enhanced save status indicators** (visual feedback for saving/saved/error states)
- Table of contents generation with AI wizard
- Question generation system for content development
- User authentication with Clerk
- File upload for book covers
- **Export functionality** (PDF/DOCX with customizable options)
- **Unified error handling** with automatic retry logic
- **WCAG 2.1 compliant keyboard navigation** (all interactive elements accessible via keyboard)

## Code Style & Best Practices

- **Modular Design**: Files under 500 lines
- **Environment Safety**: Never hardcode secrets
- **Test-First**: Write tests before implementation
- **Clean Architecture**: Separate concerns
- **Documentation**: Keep updated

### ✅ Completed Features
- User authentication (Clerk integration)
- Book CRUD operations with metadata
- **Book Deletion UI** (Type-to-confirm with comprehensive data loss warnings)
- TOC generation with AI wizard
- Chapter tabs interface (vertical layout with keyboard shortcuts Ctrl+1-9)
- Question-based content creation system
- **Rich Text Editor** (TipTap with full formatting capabilities)
- **AI Draft Generation** (Q&A to narrative with multiple writing styles)
- **Enhanced Auto-save System** (3-second debounce with localStorage backup on network failure)
- **Save Status Indicators** (Visual feedback: "Not saved yet" → "Saving..." → "Saved ✓ [timestamp]")
- **Keyboard Accessibility** (WCAG 2.1 compliant - all tabs and interactive elements accessible via Enter/Space)
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
See `CURRENT_SPRINT.md` for active tasks. Current focus:
1. **API Contract Formalization** - TypeScript interfaces and JSDoc documentation
2. **Performance Monitoring** - Core Web Vitals tracking and operation budgets
3. **Quality Enhancement** - Loading states, data preservation, responsive validation

## 🚀 Available Agents (54 Total)

### Core Development
`coder`, `reviewer`, `tester`, `planner`, `researcher`

### Swarm Coordination
`hierarchical-coordinator`, `mesh-coordinator`, `adaptive-coordinator`, `collective-intelligence-coordinator`, `swarm-memory-manager`

### Consensus & Distributed
`byzantine-coordinator`, `raft-manager`, `gossip-coordinator`, `consensus-builder`, `crdt-synchronizer`, `quorum-manager`, `security-manager`

### Performance & Optimization
`perf-analyzer`, `performance-benchmarker`, `task-orchestrator`, `memory-coordinator`, `smart-agent`

### GitHub & Repository
`github-modes`, `pr-manager`, `code-review-swarm`, `issue-tracker`, `release-manager`, `workflow-automation`, `project-board-sync`, `repo-architect`, `multi-repo-swarm`

### SPARC Methodology
`sparc-coord`, `sparc-coder`, `specification`, `pseudocode`, `architecture`, `refinement`

### Specialized Development
`backend-dev`, `mobile-dev`, `ml-developer`, `cicd-engineer`, `api-docs`, `system-architect`, `code-analyzer`, `base-template-generator`

### Testing & Validation
`tdd-london-swarm`, `production-validator`

### Migration & Planning
`migration-planner`, `swarm-init`

## 🎯 Claude Code vs MCP Tools

### Claude Code Handles ALL:
- File operations (Read, Write, Edit, MultiEdit, Glob, Grep)
- Code generation and programming
- Bash commands and system operations
- Implementation work
- Project navigation and analysis
- TodoWrite and task management
- Git operations
- Package management
- Testing and debugging

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
