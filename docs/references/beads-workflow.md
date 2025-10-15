# bd (Beads) Task Management Workflow

**CRITICAL**: bd is the **SINGLE SOURCE OF TRUTH** for all task tracking. This replaces manual markdown task management and prevents "markdown hell" with multiple conflicting plan versions.

## Why bd?

**Problem**: Manual markdown task tracking leads to:
- ❌ Multiple conflicting versions (Phase 1, Phase 2, Phase 3a, Phase 3b...)
- ❌ Outdated task status scattered across files
- ❌ No dependency tracking between tasks
- ❌ AI agents working on duplicate or blocked tasks
- ❌ Manual synchronization burden across documents

**Solution**: bd provides:
- ✅ Single SQLite database as source of truth (`.beads/*.db`)
- ✅ Automatic git sync via JSONL export/import
- ✅ Dependency-aware task management (blocks, related, parent-child)
- ✅ `bd ready` shows unblocked work for AI agents
- ✅ JSON output for programmatic queries
- ✅ Human-readable markdown exports on demand

## Absolute Rules for AI Agents

**🚨 MANDATORY: CHECK bd FIRST - ALWAYS**

Before planning, implementing, or discussing ANY task:

1. **ALWAYS query bd for current status**:
   ```bash
   bd list                    # View all tasks
   bd ready                   # View ready-to-start tasks (no blockers)
   bd show <task-id>          # View task details
   bd dep tree <task-id>      # View dependency tree
   ```

2. **NEVER read markdown task files as source of truth**:
   - ❌ DO NOT parse CURRENT_SPRINT.md for task status
   - ❌ DO NOT parse IMPLEMENTATION_PLAN.md for task list
   - ❌ DO NOT create new TODO.md, TASKS.md, PLAN.md files
   - ✅ ALWAYS query bd database for current task state

3. **NEVER update markdown task files manually**:
   - ❌ DO NOT edit task lists in markdown
   - ❌ DO NOT add checkboxes or status indicators
   - ❌ DO NOT manually sync between bd and markdown
   - ✅ ALWAYS use bd commands to update task status

4. **ALWAYS use bd commands for task operations**:
   ```bash
   # Create tasks
   bd create "Task title" -p 1 -t feature -d "Description"

   # Update tasks
   bd update <task-id> --status in_progress
   bd update <task-id> --assignee alice
   bd update <task-id> --priority 0

   # Add dependencies (task-2 blocks task-1)
   bd dep add <task-1> <task-2>

   # Close tasks
   bd close <task-id> --reason "Completed in commit abc123"
   ```

5. **Export to markdown ONLY at milestones**:
   ```bash
   # Weekly sprint snapshot (human-readable)
   ./scripts/export-current-sprint.sh

   # High-level implementation plan (narrative + bd references)
   ./scripts/export-implementation-plan.sh

   # Archive completed sprint
   ./scripts/archive-completed-sprint.sh "Sprint-3-4"
   ```

## Workflow Patterns

### Starting ANY Task

```bash
# 1. Check bd for current status
bd list --status open
bd ready                    # Show unblocked tasks

# 2. Check dependencies
bd dep tree <task-id>

# 3. Claim task
bd update <task-id> --status in_progress --assignee <your-name>

# 4. Work on task (use TodoWrite for sub-tasks)

# 5. Mark complete
bd close <task-id> --reason "Implemented feature X in commit abc123"
```

### Planning New Work

```bash
# 1. Create task in bd (NOT markdown)
bd create "Implement accessibility audit" -p 0 -t feature -d "WCAG 2.1 AA compliance check"

# 2. Add dependencies if needed
bd dep add accessibility-audit api-contracts  # api-contracts blocks accessibility-audit

# 3. Break down into sub-tasks (if needed)
bd create "Install @axe-core/react" -p 1 -t task
bd dep add <parent-task> <sub-task>

# 4. Export snapshot ONLY when ready for review
./scripts/export-current-sprint.sh
```

### Daily Development Flow

```bash
# Morning: Check what's ready to work on
bd ready

# During work: Update task status
bd update <task-id> --status in_progress

# When blocked: Add dependency
bd dep add <my-task> <blocking-task>

# When complete: Close task
bd close <task-id> --reason "Completed and tested"

# End of day: (Optional) Export snapshot for review
./scripts/export-current-sprint.sh
```

### Sprint Planning / Review

```bash
# Export current sprint for human review
./scripts/export-current-sprint.sh

# Review markdown snapshot with team
# Make decisions...

# Update bd based on decisions (NOT markdown)
bd create "New task from planning"
bd update <task-id> --priority 0

# End of sprint: Archive completed work
./scripts/archive-completed-sprint.sh "Sprint-3-4"

# Start new sprint: Create new tasks in bd
bd create "Sprint 5 task 1" -p 0 -t feature
```

## Preventing "Markdown Hell"

**Problem Scenario**: Multiple plan documents with conflicting information
- `PHASE1_PLAN.md` says task is complete
- `TODO.md` says task is in progress
- `CURRENT_SPRINT.md` says task is blocked
- `IMPLEMENTATION_PLAN.md` says task doesn't exist
- **Result**: Confusion, duplicate work, wasted effort

**Solution with bd**:
- ✅ ONE database with ONE source of truth per task
- ✅ Markdown files are READ-ONLY snapshots (auto-generated)
- ✅ All updates go through bd commands
- ✅ Dependencies prevent duplicate work (`bd ready` only shows unblocked tasks)
- ✅ Task history tracked automatically (created, updated, closed timestamps)

## When NOT to Use bd

bd is ONLY for **task tracking**. Use regular documentation for:

1. **Development Guidelines**: CLAUDE.md (code standards, testing requirements, git workflow)
2. **Technical Analysis**: claudedocs/*.md (detailed audits, gap analysis, architecture docs >500 lines)
3. **API Documentation**: Code comments (JSDoc, docstrings, OpenAPI specs)
4. **Architecture Decisions**: bd ADRs (`bd doc create "ADR: Title"`) for formal decisions
5. **Component Usage**: CLAUDE.md (reusable component patterns and examples)

## bd Database Location

```
/home/frankbria/projects/auto-author/.beads/
├── autoauthor-*.db          # SQLite database (source of truth)
└── autoauthor-*.jsonl       # Git-synced export (auto-generated)
```

- **Database**: Never edited manually, always via bd commands
- **JSONL**: Auto-exported after CRUD operations (5s debounce)
- **Git Sync**: Auto-imported after `git pull` if JSONL newer than DB
- **No manual sync required**: bd handles synchronization automatically

## Integration with Existing Workflow

**Updated Decision Tree**:

```
New information to document?
│
├─ Is it a task, feature request, or bug?
│  └─ YES → Create in bd: `bd create "Title" -p 1 -t feature`
│
├─ Is it an architecture decision?
│  └─ YES → Create ADR in bd: `bd doc create "ADR: Title"`
│
├─ Need to check task status or plan work?
│  └─ YES → Query bd: `bd list`, `bd ready`, `bd show <task-id>`
│
├─ Need human-readable snapshot for review?
│  └─ YES → Export: `./scripts/export-current-sprint.sh`
│
├─ Is it a development standard or guideline?
│  └─ YES → Update CLAUDE.md
│
├─ Is it detailed technical analysis (>500 lines)?
│  └─ YES → Create in claudedocs/ with descriptive name
│
└─ NOT SURE? → Query bd first, then decide
```

## Markdown File Status

| File | Status | Purpose | Update Method |
|------|--------|---------|---------------|
| **CURRENT_SPRINT.md** | 🔄 Auto-generated | Weekly snapshot for review | `./scripts/export-current-sprint.sh` |
| **IMPLEMENTATION_PLAN.md** | 🔄 Auto-generated | High-level roadmap + bd references | `./scripts/export-implementation-plan.sh` |
| **CLAUDE.md** | ✅ Manual | Development guidelines | Direct edit |
| **claudedocs/*.md** | ✅ Manual | Technical analysis | Direct edit |
| **archive/*.md** | 🔒 Read-only | Historical snapshots | Archived via script |

**Warning Labels in Auto-Generated Files**:
```markdown
> ⚠️ **WARNING**: This file is auto-generated from bd (Beads issue tracker).
> To update tasks, use: `bd create`, `bd update`, or `bd close`
> To regenerate this file, run: `./scripts/export-current-sprint.sh`
```

## Quick Reference Commands

```bash
# Query bd (single source of truth)
bd list                           # All tasks
bd list --status open             # Open tasks
bd list --status in_progress      # Active tasks
bd list --priority 0              # Critical tasks (P0)
bd ready                          # Ready to start (no blockers)
bd show <task-id>                 # Task details
bd dep tree <task-id>             # Dependency visualization

# Create tasks
bd create "Task title"            # Simple task
bd create "Task" -p 0 -t feature -d "Description"  # Full task
bd create "Fix bug" -t bug --assignee alice        # Assigned bug

# Update tasks
bd update <task-id> --status in_progress
bd update <task-id> --priority 0
bd update <task-id> --assignee bob

# Dependencies (task-2 blocks task-1)
bd dep add <task-1> <task-2>      # Add blocking dependency
bd dep add <task-1> <task-2> --type related  # Add related link
bd dep tree <task-id>             # View dependency tree
bd dep cycles                     # Detect circular dependencies

# Close tasks
bd close <task-id>                # Close without reason
bd close <task-id> --reason "Completed in PR #123"  # With reason

# Export snapshots (human-readable markdown)
./scripts/export-current-sprint.sh        # Weekly snapshot
./scripts/export-implementation-plan.sh   # High-level plan
./scripts/archive-completed-sprint.sh "Sprint-3-4"  # Archive

# JSON output (for programmatic parsing)
bd list --json                    # All tasks as JSON
bd ready --json                   # Ready tasks as JSON
bd show <task-id> --json          # Task details as JSON
```

## Verification Checklist for AI Agents

Before completing any planning or task management operation:

- [ ] Queried bd for current task status (`bd list`, `bd ready`)
- [ ] Used bd commands to create/update tasks (NOT markdown editing)
- [ ] Added dependencies between tasks when needed (`bd dep add`)
- [ ] Exported markdown snapshot ONLY for milestones (NOT for every change)
- [ ] Markdown task files marked as auto-generated with warnings
- [ ] No manual task tracking in markdown files
- [ ] Used TodoWrite for session-specific sub-tasks (ephemeral)
- [ ] Used bd for persistent tasks that survive sessions
