<!--
Sync Impact Report - Constitution v1.0.0
═══════════════════════════════════════

Version Change: INITIAL → 1.0.0 (MAJOR - First ratification)

Modified Principles: N/A (Initial creation)
Added Sections:
  - 8 Core Principles (Test-First Development, 85% Coverage Requirement, E2E Testing,
    Pre-Commit Quality Gates, Security & Authentication, Performance Budgets,
    Accessibility Compliance, Documentation Synchronization)
  - Development Workflow section
  - Quality Gates section
  - Governance rules

Removed Sections: N/A

Templates Requiring Updates:
  ✅ Updated: plan-template.md (constitution check section validated)
  ✅ Updated: spec-template.md (user scenarios align with test-first principle)
  ✅ Updated: tasks-template.md (task types align with principle-driven categories)

Follow-up TODOs: None - all placeholders filled
-->

# Auto Author Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)

Test-Driven Development (TDD) is **mandatory** for all features:
- Tests MUST be written before implementation
- Red-Green-Refactor cycle strictly enforced
- Unit tests (<1s each), E2E tests (<30s each)
- Tests MUST be isolated, repeatable, meaningful, and maintainable
- NEVER use arbitrary timeouts; use condition-based waiting patterns

**Rationale**: TDD ensures code quality, prevents regressions, and provides living documentation. The current test infrastructure (88.7% frontend pass rate, 98.9% backend pass rate) demonstrates this principle in action. All environmental test failures are being tracked and systematically resolved.

### II. 85% Coverage Requirement

Minimum 85% test coverage required for all code:
- Both frontend (Jest) and backend (pytest) must meet threshold
- Coverage measured on lines, branches, functions, and statements
- New features CANNOT be merged without meeting coverage targets
- Pre-commit hooks enforce coverage gates automatically

**Rationale**: High coverage ensures thorough testing and reduces production bugs. The backend is currently at 41% coverage with a documented 4-5 week improvement plan to reach 85%, demonstrating our commitment to this principle.

### III. E2E Testing

Every user-facing feature MUST have E2E tests validating:
1. **Happy Path**: Complete user journey from start to finish
2. **Error Handling**: System behavior during failures
3. **Performance**: Operations complete within defined budgets
4. **Accessibility**: Keyboard navigation and WCAG 2.1 compliance
5. **Data Integrity**: Data persists correctly across operations

**Rationale**: E2E tests catch integration issues and ensure the user experience works end-to-end. The Playwright test suite with auth bypass support enables comprehensive testing without compromising security.

### IV. Pre-Commit Quality Gates

ALL commits MUST pass automated quality gates:
- **Linting**: ESLint (frontend), ruff (backend) with zero errors
- **Type Checking**: TypeScript strict mode, mypy for Python
- **Unit Tests**: All existing tests must pass
- **E2E Tests**: All Playwright tests must pass
- **Coverage**: Must meet or exceed 85% threshold
- **Security**: Secret detection, large file prevention (>1MB blocked)
- **Documentation**: CURRENT_SPRINT.md and IMPLEMENTATION_PLAN.md auto-sync from bd tracker

**Rationale**: Automated quality gates catch issues before they enter the codebase, maintaining consistent quality standards. Emergency bypasses (`--no-verify`) require immediate follow-up tasks.

### V. Security & Authentication

Security principles are non-negotiable:
- **Production**: JWT verification via Clerk JWKS endpoint only
- **Development**: `BYPASS_AUTH=true` allowed ONLY in development/testing environments
- **Secrets Management**: NEVER hardcode secrets; use environment variables
- **Token Validation**: All authentication tokens MUST be verified with proper error handling
- **Session Management**: 30-minute idle timeout, 12-hour absolute timeout with activity tracking

**Rationale**: Security vulnerabilities are unacceptable. The recent fix for auth test coverage (auto-author-71) demonstrates our commitment to ensuring tests properly exercise security logic even in development environments.

### VI. Performance Budgets

Performance standards MUST be met:
- **TOC Generation**: <3000ms (3 seconds)
- **Export Operations**: <5000ms (5 seconds)
- **Core Web Vitals**: LCP <2.5s, FID <100ms, CLS <0.1
- **Auto-save**: 3-second debounce with localStorage backup on network failure
- **API Response Times**: <200ms p95 latency

**Rationale**: Performance directly impacts user experience. Performance monitoring is integrated into the application with real-time tracking and budgets enforced during development.

### VII. Accessibility Compliance (WCAG 2.1 Level AA)

All UI components MUST be fully accessible:
- **Keyboard Navigation**: Every interactive element accessible via keyboard
- **Screen Reader Support**: Proper ARIA labels and semantic HTML
- **Touch Targets**: 44x44px minimum (WCAG 2.1 Level AAA compliant)
- **Responsive Design**: Support 320px (iPhone SE) to desktop
- **Focus Management**: Visible focus indicators and logical tab order

**Rationale**: Accessibility is a fundamental right, not an optional feature. The project has 100% WCAG 2.1 Level AAA touch target compliance and comprehensive keyboard accessibility.

### VIII. Documentation Synchronization

Documentation MUST remain synchronized with code:
- **Task Tracking**: bd (Beads) is the single source of truth
- **Auto-Generated Docs**: CURRENT_SPRINT.md and IMPLEMENTATION_PLAN.md sync automatically via pre-commit hooks
- **Reference Documentation**: On-demand docs in `docs/references/` for detailed guidance
- **Conventional Commits**: All commits follow conventional commit format (`feat:`, `fix:`, `docs:`, etc.)
- **Code Comments**: Updated inline when implementation changes

**Rationale**: Outdated documentation is worse than no documentation. Automated synchronization ensures documentation reflects current project state without manual overhead.

## Development Workflow

### Feature Branch Workflow (MANDATORY)

NEVER commit directly to `main` or `develop`:

1. **Branch Creation**: `git checkout -b feature/your-feature-name`
2. **Development**: Write tests → Implement → Refactor
3. **Quality Checks**: Pre-commit hooks run automatically
4. **Pull Request**: Create PR with description, tests, and documentation
5. **Code Review**: PR must be approved before merging
6. **Task Closure**: Close bd task with reason: `bd close <id> --reason "Completed in PR #123"`

### Task Management (bd/Beads)

- `bd ready` - View unblocked tasks ready to start
- `bd list --status open` - View all open tasks
- `bd create "Task" -p 0 -t feature -d "Description"` - Create task
- `bd close <task-id> --reason "Completed"` - Close completed task
- Markdown files are auto-generated snapshots; bd is the source of truth

## Quality Gates

### Feature Completion Checklist

A feature is NOT complete until ALL criteria are met:

- [ ] Unit tests written (≥85% coverage for new code)
- [ ] E2E test created (for user-facing features)
- [ ] All tests passing (unit + E2E)
- [ ] Documentation updated (CLAUDE.md, API docs, user guides)
- [ ] Performance validated (meets operation budgets)
- [ ] Accessibility verified (WCAG 2.1 Level AA minimum)
- [ ] Code reviewed (PR approved by team)
- [ ] bd task closed with completion reason

### Test Quality Standards

**Tests MUST be:**
- **Isolated**: No dependencies on external services (use mocks)
- **Repeatable**: Same result every time
- **Fast**: Unit <1s, E2E <30s
- **Meaningful**: Test behavior, not implementation
- **Maintainable**: Clear, well-documented test code

**Tests MUST NOT:**
- Use arbitrary timeouts (`await page.waitForTimeout(5000)`)
- Depend on test execution order
- Leave side effects (data, files, processes)
- Test internal implementation details

## Governance

This constitution supersedes all other practices and documentation. Any conflict between this constitution and other project documentation must be resolved in favor of the constitution.

### Amendment Procedure

1. **Proposal**: Document proposed change with rationale
2. **Impact Analysis**: Assess affected code, tests, and documentation
3. **Team Review**: Discuss and approve/reject proposal
4. **Implementation**: Update constitution, bump version, propagate changes to templates
5. **Migration**: Update existing code/docs to comply with new rules
6. **Communication**: Announce changes to all team members

### Versioning Policy

Constitution follows semantic versioning:
- **MAJOR**: Backward incompatible governance/principle removals or redefinitions
- **MINOR**: New principle/section added or materially expanded guidance
- **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements

### Compliance Review

- All PRs must verify compliance with constitution principles
- Complexity must be justified against simplicity principle
- Violations require explicit approval and documented exception
- Use `CLAUDE.md` for runtime development guidance

**Version**: 1.0.0 | **Ratified**: 2025-11-07 | **Last Amended**: 2025-11-07
