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
- **Performance Monitoring** (Core Web Vitals + custom operation tracking with budgets)
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
1. **API Contract Formalization** - ✅ COMPLETE (TypeScript interfaces and JSDoc documentation)
2. **Performance Monitoring** - ✅ COMPLETE (Core Web Vitals tracking and operation budgets)
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

### Loading State Components

**Location**: `frontend/src/components/loading/`

**Description**: Comprehensive loading indicators with progress feedback for async operations.

**Components**:
1. **LoadingStateManager** - Full-featured loading indicator with progress, time estimates, and cancellation
2. **ProgressIndicator** - Visual progress display with percentage and count tracking

**Key Features**:
- Progress bars with smooth transitions
- Time estimates with countdown (uses time budgets from `lib/loading/timeEstimator.ts`)
- Cancellable operations (optional)
- Accessible ARIA labels (WCAG 2.1 compliant)
- Graceful transitions (200ms delay to avoid flicker)
- Inline and full-screen variants
- Compact variant for space-constrained UI

**Usage Example - LoadingStateManager**:
```tsx
import { LoadingStateManager } from '@/components/loading';
import { createProgressTracker } from '@/lib/loading';

// Create progress tracker for time estimates
const getProgress = useMemo(() =>
  createProgressTracker('toc.generation'),
  []
);
const { progress, estimatedTimeRemaining } = getProgress();

<LoadingStateManager
  isLoading={isGenerating}
  operation="Generating Table of Contents"
  progress={progress}
  estimatedTime={estimatedTimeRemaining}
  message="Analyzing your summary and generating chapter structure..."
  onCancel={() => setIsGenerating(false)}
  inline={false}
/>
```

**Usage Example - ProgressIndicator**:
```tsx
import { ProgressIndicator } from '@/components/loading';

<ProgressIndicator
  current={5}
  total={10}
  unit="chapters"
  showPercentage={true}
  message="Processing chapters..."
  size="default"
/>

// Compact variant for space-constrained UI
<ProgressIndicator.Compact
  current={3}
  total={10}
  unit="items"
/>
```

**Time Estimation**:
The `timeEstimator` utility provides intelligent time estimates based on:
- Operation type (TOC generation, export, draft generation, etc.)
- Data size (word count, chapter count)
- Historical performance data

```tsx
import { estimateOperationTime, formatTime } from '@/lib/loading';

// Get time estimate
const estimate = estimateOperationTime('export.pdf', {
  wordCount: 50000,
  chapterCount: 15
});
// Returns: { min: 5000, max: 60000, average: 35000 }

// Format for display
const timeString = formatTime(estimate.average);
// Returns: "35s" or "1m 15s"
```

**Integrated Operations**:
- **TOC Generation**: `components/toc/TocGenerating.tsx` - 10-30 seconds
- **Export Operations**: `app/dashboard/books/[bookId]/export/page.tsx` - 5-20 seconds
- **Draft Generation**: `components/chapters/DraftGenerator.tsx` - 10-30 seconds

**Test Coverage**: 100% (53 tests, 100% pass rate)

**Accessibility**: All components include proper ARIA labels, roles, and live regions for screen reader support

---

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

## Performance Monitoring

### Overview
Comprehensive performance tracking system with Core Web Vitals and custom operation monitoring.

**Location**: `frontend/src/lib/performance/`, `frontend/src/hooks/usePerformanceTracking.ts`

### Core Components

1. **Metrics System** (`frontend/src/lib/performance/metrics.ts`):
   - Core Web Vitals tracking (LCP, FID, INP, CLS, TTFB, FCP)
   - PerformanceTracker class for custom operations
   - Rating system (good/needs-improvement/poor)
   - localStorage caching for offline scenarios
   - Development console logging and production analytics integration

2. **Performance Budgets** (`frontend/src/lib/performance/budgets.ts`):
   - 25+ operation budgets defined
   - Critical operations: TOC generation (3000ms), Export (5000ms), Draft generation (4000ms)
   - Auto-save budget: 1000ms
   - Budget validation and warning system
   - Priority-based categorization (1=critical, 3=low)

3. **React Hook** (`frontend/src/hooks/usePerformanceTracking.ts`):
   - Async operation tracking: `trackOperation(name, operation, metadata)`
   - Automatic cleanup on unmount
   - Budget validation with warnings
   - Error handling with performance context
   - Manual tracker creation for complex scenarios

4. **Web Vitals Initialization** (`frontend/src/components/performance/WebVitalsInit.tsx`):
   - Automatic Core Web Vitals tracking on app load
   - Client-side only (no SSR)
   - Integrated into app layout

### Usage

**Basic Operation Tracking**:
```typescript
import { usePerformanceTracking } from '@/hooks/usePerformanceTracking';

const { trackOperation } = usePerformanceTracking();

const handleExport = async () => {
  const result = await trackOperation('export-pdf', async () => {
    return await bookClient.exportPDF(bookId);
  }, { bookId, format: 'pdf' });

  if (result.metric.exceeded_budget) {
    console.warn(`Export took ${result.metric.duration}ms`);
  }
};
```

**Manual Tracker for Complex Scenarios**:
```typescript
const { createTracker } = usePerformanceTracking();

const tracker = createTracker('complex-operation', { phase: 'init' });
// ... do work across multiple functions ...
const metric = tracker.end({ result: 'success' });
```

### Integrated Operations

Performance tracking is active in:
- **TOC Generation**: toc-generation, toc-questions, toc-readiness, analyze-summary
- **Export**: export-pdf, export-docx, export-stats
- **Draft Generation**: generate-draft
- **Auto-save**: auto-save, manual-save
- **Chapter Operations**: chapter-load, chapter-list

### Performance Budgets

| Operation | Budget | Priority | Description |
|-----------|--------|----------|-------------|
| toc-generation | 3000ms | 1 | AI-powered TOC generation |
| export-pdf | 5000ms | 1 | PDF export |
| export-docx | 5000ms | 1 | DOCX export |
| generate-draft | 4000ms | 1 | AI draft from Q&A |
| auto-save | 1000ms | 1 | Auto-save (3s debounce) |
| chapter-load | 500ms | 1 | Load chapter content |
| book-list | 1200ms | 2 | Load user books |
| toc-questions | 2000ms | 2 | Generate clarifying questions |

### Development Mode

In development, performance metrics are logged to console with color-coded output:
- ✅ Green: Within budget (good)
- ⚠️ Yellow: Near budget (needs-improvement)
- ❌ Red: Exceeded budget (poor)

### Production Mode

In production, metrics are cached in localStorage for offline scenarios and should be sent to analytics endpoints:
```typescript
// TODO: Replace with actual analytics implementation
// window.gtag?.('event', event.event_name, event);
// window.analytics?.track(event.event_name, event);
```

### Testing

Test suite: `frontend/src/lib/performance/__tests__/metrics.test.ts`
- 20/20 tests passing (100% pass rate)
- Coverage: Basic tracking, budget validation, localStorage caching, error handling
- Development mode logging verification

### Future Enhancements

1. **Analytics Integration**: Connect to Google Analytics, Mixpanel, or custom endpoint
2. **Performance Dashboards**: Visualize metrics over time
3. **Alerting**: Automatic alerts when operations consistently exceed budgets
4. **Historical Analysis**: Track performance trends and regressions
5. **User Segmentation**: Performance metrics by user type or device

---

## Testing Infrastructure

### Overview
Comprehensive testing strategy implemented across backend, frontend, and E2E layers following TDD methodology with 80% coverage target.

**Status**:
- Backend: 85-90% coverage (189 passing tests, 5 skipped)
- Frontend: 65.28% coverage (325 passing tests, 68 blocked by dependencies)
- E2E: 3 comprehensive journey tests across 8 browser configurations

### Test Helpers & Utilities

#### 1. Condition-Based Waiting (`frontend/src/__tests__/helpers/conditionWaiting.ts`)

Replaces arbitrary timeouts with condition polling for reliable async testing.

**Usage**:
```typescript
import { waitForCondition } from '@/__tests__/helpers/conditionWaiting';

// Wait for element to appear
await waitForCondition(
  async () => await page.locator('[data-testid="save-status"]').isVisible(),
  {
    timeout: 5000,
    interval: 100,
    timeoutMessage: 'Save status indicator did not appear'
  }
);
```

**Benefits**:
- Tests complete faster (returns immediately when condition met)
- More reliable (no race conditions)
- Clearer error messages
- 10-30x more reliable than fixed timeouts

**Test Coverage**: 7/7 tests passing (100%)

#### 2. Test Data Setup Helpers (`frontend/src/__tests__/helpers/testDataSetup.ts`)

API-based test data creation for E2E tests (10-30x faster than UI-driven setup).

**Usage**:
```typescript
import { testBookFactory } from '@/__tests__/helpers/testDataSetup';

// Create book with 3 chapters via API
const { book, chapters } = await testBookFactory.withChapters(token, 3);

// Navigate directly to chapter editor
await page.goto(`/dashboard/books/${book.id}/chapters/${chapters[0].id}`);

// Test the actual functionality without UI setup time
```

**Factory Patterns**:
- `testBookFactory.nonFiction(token, title?)` - Create non-fiction book
- `testBookFactory.fiction(token, title?)` - Create fiction book
- `testBookFactory.withChapters(token, count)` - Create book with N chapters

**Benefits**:
- 10-30x faster test execution
- Consistent test data
- Reduces test flakiness
- Enables focus on critical path testing

**Note**: Requires backend API client implementation (placeholders currently in place)

#### 3. Unified Error Handler (`frontend/src/lib/errors/errorHandler.ts`)

Production-ready error classification with automatic retry and exponential backoff.

**Features**:
- Error classification (NETWORK, VALIDATION, AUTH, SERVER, UNKNOWN)
- Automatic retry for transient errors (503, 429, network failures)
- Exponential backoff (1s, 2s, 4s, max 30s)
- Max retry limit (3 attempts, configurable)
- Toast notification integration
- TypeScript with full type safety

**Usage**:
```typescript
import { handleApiError } from '@/lib/errors';
import { useToast } from '@/components/ui/use-toast';

const { toast } = useToast();

// Automatic retry on transient errors
const books = await handleApiError(
  () => fetch('/api/books').then(r => r.json()),
  toast,
  { customMessage: 'Failed to load books' }
);
```

**Configuration**:
```typescript
import { ErrorHandler } from '@/lib/errors';

const handler = new ErrorHandler({
  maxRetries: 5,
  baseDelay: 2000,
  maxDelay: 60000
});
```

**Test Coverage**: 43/43 tests passing (100%)

### E2E Test Suites

#### 1. Complete Authoring Journey (`frontend/src/e2e/complete-authoring-journey.spec.ts`)

Comprehensive 8-step workflow validation from book creation to draft generation.

**Test Flow**:
1. User authentication (Clerk)
2. Book creation with metadata
3. AI TOC generation
4. Chapter navigation
5. Question generation & answering
6. Draft generation from Q&A
7. Content verification in editor
8. Complete workflow validation

**Key Features**:
- 491 lines of comprehensive test code
- Uses condition-based waiting throughout
- Tests real AI integration (not mocked)
- Addresses #1 critical gap from E2E assessment
- Cross-browser: 8 scenarios × 8 browser configs = 64 test runs

**Documentation**: `docs/testing/e2e-complete-authoring-journey.md`

**Execution Time**: ~2-3 minutes (includes real AI API calls)

#### 2. Editing & Auto-save Flow (`frontend/src/e2e/editing-autosave-flow.spec.ts`)

Validates chapter editor auto-save, localStorage backup, and save status indicators.

**Test Scenarios** (7 scenarios):
1. Auto-save with 3-second debounce
2. localStorage backup on network failure
3. Content recovery from localStorage
4. Backup dismissal workflow
5. Save status indicator lifecycle
6. Debounce behavior validation
7. Network recovery after backup

**Key Features**:
- 743 lines of test code
- Network failure simulation via `page.route()`
- Direct localStorage access via `page.evaluate()`
- 5 reusable helper functions
- No fixed timeouts (condition-based only)

**Documentation**: `docs/testing/e2e-editing-autosave-flow.md`

**Execution Time**: ~90-120 seconds

#### 3. Error Recovery Flow (`frontend/src/e2e/error-recovery-flow.spec.ts`)

Validates automatic retry logic with exponential backoff for transient errors.

**Test Scenarios** (8 scenarios):
1. Successful recovery on transient error (503 → retry → success)
2. Exponential backoff timing validation (1s, 2s, 4s with ±200ms tolerance)
3. Non-retryable errors fail immediately (400, no retry)
4. Max retry limit respected (stops after 3 attempts)
5. Network errors retry automatically
6. Rate limiting triggers retry (429)
7. Auth errors don't retry (401/403)
8. User experience during retries

**Key Features**:
- 600+ lines of test code
- Millisecond-precision timing validation
- API interception for controlled error simulation
- Integration with error handler from Task 4
- Validates exponential backoff formula: `baseDelay * 2^attempt`

**Documentation**: `docs/testing/error-recovery-e2e-documentation.md`

**Execution Time**: ~60-90 seconds

### Test Organization

**Unit Tests**: `frontend/src/lib/**/*.test.ts`, `frontend/src/components/**/*.test.tsx`
**Integration Tests**: `frontend/src/__tests__/*.test.tsx`
**E2E Tests**: `frontend/src/e2e/*.spec.ts`
**Test Helpers**: `frontend/src/__tests__/helpers/`
**Test Documentation**: `docs/testing/`

### Running Tests

**Backend Tests**:
```bash
cd backend
uv run pytest --cov=app tests/ --cov-report=term-missing
```

**Frontend Unit/Integration Tests**:
```bash
cd frontend
npm test                    # Run all tests
npm run test:coverage       # With coverage report
npm test -- conditionWaiting.test  # Run specific test
```

**E2E Tests** (requires backend + frontend running):
```bash
cd frontend
npx playwright install      # One-time browser setup
npx playwright test         # Run all E2E tests
npx playwright test --ui    # Run with UI mode (recommended)
npx playwright test complete-authoring-journey  # Run specific test
```

### Coverage Reports

**Baseline Report**: `docs/testing/baseline-coverage-report.md`
- Comprehensive analysis of current state
- Prioritized improvement plan
- Path to 80% coverage target

**Component Test Review**: `docs/testing/component-test-review.md`
- 53 test files analyzed
- Gap analysis by priority (P0-P3)
- Specific recommendations for Tasks 10-11

### Quality Standards

All tests must meet:
- **100% Pass Rate**: No failing tests allowed
- **Meaningful Assertions**: Tests validate behavior, not just coverage
- **Condition-Based Waiting**: No arbitrary timeouts in E2E tests
- **Proper Cleanup**: All tests clean up resources
- **Documentation**: Complex tests include explanatory comments
- **Accessibility**: E2E tests verify WCAG 2.1 compliance where applicable

### Known Issues

**Frontend**:
- 68 ChapterEditor tests blocked by missing `web-vitals` dependency mock
- Custom hooks at 50% coverage (useChapters, useBooks, useAutoSave undertested)
- Fix: Add mocks to `jest.setup.ts` (1-2 hours work, will unblock all tests)

**Backend**:
- 5 skipped tests for rate limiting, race conditions, admin authorization
- These are intentionally skipped pending feature completion

### Next Steps

Per the agile testing strategy plan (see `docs/plans/2025-10-13-agile-testing-strategy.md`):

1. **Fix dependency mocks** (1-2 hours) → Unblocks 68 tests, +8-10% coverage
2. **Task 10: BookCreationWizard tests** (6-8 hours) → +4-6% coverage
3. **Task 11: useChapterTabs hook tests** (10-14 hours) → +3-4% coverage
4. **Task 12: Updated coverage report** → Verify 80% target reached

**Projected Final Coverage**: 77-83% frontend (exceeds 80% target)

We track work in Beads instead of Markdown for AI Agents. Run `bd quickstart` to see how.
