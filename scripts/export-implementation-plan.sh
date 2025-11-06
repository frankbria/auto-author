#!/bin/bash
# Export high-level implementation plan from bd to IMPLEMENTATION_PLAN.md
# This maintains the narrative structure while referencing bd for task details
# Usage: ./scripts/export-implementation-plan.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_FILE="$PROJECT_ROOT/IMPLEMENTATION_PLAN.md"
DATE=$(date +%Y-%m-%d)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Exporting implementation plan to markdown...${NC}"

# Get all statistics up front
TOTAL=$(bd list --json | jq 'length')
CLOSED=$(bd list --status closed --json | jq 'length')
OPEN=$(bd list --status open --json | jq 'length')
IN_PROGRESS=$(bd list --status in_progress --json | jq 'length')
BLOCKED=$(bd blocked --json | jq 'length')
READY=$(bd ready --json | jq 'length')

# Get counts by priority
P0_COUNT=$(bd list --priority 0 --json | jq 'length')
P1_COUNT=$(bd list --priority 1 --json | jq 'length')
P2_COUNT=$(bd list --priority 2 --json | jq 'length')
P3_COUNT=$(bd list --priority 3 --json | jq 'length')

# Get counts by type
BUG_COUNT=$(bd list --type bug --json | jq 'length')
FEATURE_COUNT=$(bd list --type feature --json | jq 'length')
TASK_COUNT=$(bd list --type task --json | jq 'length')

# Calculate percentage
COMPLETION_PCT=0
if [ "$TOTAL" -gt 0 ]; then
  COMPLETION_PCT=$((CLOSED * 100 / TOTAL))
fi

# Determine project phase based on completion
PROJECT_PHASE="MVP Development"
if [ "$COMPLETION_PCT" -ge 75 ]; then
  PROJECT_PHASE="Production Ready"
elif [ "$COMPLETION_PCT" -ge 50 ]; then
  PROJECT_PHASE="Stabilization & Quality"
elif [ "$COMPLETION_PCT" -ge 25 ]; then
  PROJECT_PHASE="Feature Development"
fi

# Create header
cat > "$OUTPUT_FILE" << EOF
# Auto-Author Implementation Plan

**Last Updated**: $DATE
**Status**: Active Development
**Current Phase**: $PROJECT_PHASE ($COMPLETION_PCT% complete)

> ℹ️ **NOTE**: This is a high-level implementation roadmap organized by priority and status.
> For current task status and details, run: \`bd list\` or \`bd ready\`
> To update this plan, run: \`./scripts/export-implementation-plan.sh\`

---

## Executive Summary

This document serves as the single source of truth for the Auto-Author implementation roadmap. All tasks are tracked in bd (Beads issue tracker) and organized by priority and status.

**Task Management**: All tasks are tracked in bd.
- View tasks: \`bd list\`
- Ready work: \`bd ready\`
- Task details: \`bd show <task-id>\`
- Statistics: \`bd stats\`

### Project Overview

**Progress**: $CLOSED of $TOTAL tasks complete ($COMPLETION_PCT%)

**Status Breakdown**:
- ✅ Completed: $CLOSED tasks
- 🚧 In Progress: $IN_PROGRESS tasks
- 📋 Ready to Start: $READY tasks (no blockers)
- 🔒 Blocked: $BLOCKED tasks
- 📝 Planned: $OPEN tasks

**Priority Distribution**:
- P0 (Critical): $P0_COUNT tasks
- P1 (High): $P1_COUNT tasks
- P2 (Medium): $P2_COUNT tasks
- P3 (Low): $P3_COUNT tasks

**Type Breakdown**:
- 🐛 Bugs: $BUG_COUNT
- ✨ Features: $FEATURE_COUNT
- 📋 Tasks: $TASK_COUNT

---

## Current Work

### In Progress

EOF

# Export in-progress tasks
if [ "$IN_PROGRESS" -gt 0 ]; then
  bd list --status in_progress --json | jq -r '.[] | "#### \(.id): \(.title)\n**Priority**: P\(.priority) | **Type**: \(.issue_type)\n\n\(.description // "No description")\n\n**Dependencies**: " + (if (.dependencies | length) > 0 then (.dependencies | join(", ")) else "None" end) + "\n"' >> "$OUTPUT_FILE"
else
  echo "No tasks currently in progress." >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
fi

# Export ready tasks (organized by priority)
cat >> "$OUTPUT_FILE" << EOF

### Ready to Start (No Blockers)

**P0 Critical Path** ($P0_COUNT total):

EOF

# P0 ready tasks
P0_READY=$(bd ready --json | jq '[.[] | select(.priority == 0)]')
P0_READY_COUNT=$(echo "$P0_READY" | jq 'length')
if [ "$P0_READY_COUNT" -gt 0 ]; then
  echo "$P0_READY" | jq -r '.[] | "#### \(.id): \(.title)\n**Type**: \(.issue_type)\n\n\(.description // "No description")\n"' >> "$OUTPUT_FILE"
else
  echo "No P0 tasks ready to start." >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
fi

cat >> "$OUTPUT_FILE" << EOF

**P1 High Priority** ($P1_COUNT total):

EOF

# P1 ready tasks
P1_READY=$(bd ready --json | jq '[.[] | select(.priority == 1)]')
P1_READY_COUNT=$(echo "$P1_READY" | jq 'length')
if [ "$P1_READY_COUNT" -gt 0 ]; then
  echo "$P1_READY" | jq -r '.[] | "#### \(.id): \(.title)\n**Type**: \(.issue_type)\n\n\(.description // "No description")\n"' >> "$OUTPUT_FILE"
else
  echo "No P1 tasks ready to start." >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
fi

# Export blocked tasks
cat >> "$OUTPUT_FILE" << EOF

### Blocked Tasks

EOF

if [ "$BLOCKED" -gt 0 ]; then
  bd blocked --json | jq -r '.[] | "#### \(.id): \(.title)\n**Priority**: P\(.priority) | **Type**: \(.issue_type)\n\n\(.description // "No description")\n\n**Blocked by**: " + (.blocked_by | join(", ")) + "\n"' >> "$OUTPUT_FILE"
else
  echo "No blocked tasks." >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
fi

# Export planned tasks by priority
cat >> "$OUTPUT_FILE" << EOF

---

## Planned Work

### P0 Critical Path

EOF

bd list --priority 0 --status open --json | jq -r '.[] | "#### \(.id): \(.title)\n**Type**: \(.issue_type)\n\n\(.description // "No description")\n\n**Dependencies**: " + (if (.dependencies | length) > 0 then (.dependencies | join(", ")) else "None" end) + "\n"' >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" << EOF

### P1 High Priority

EOF

bd list --priority 1 --status open --json | jq -r '.[] | "#### \(.id): \(.title)\n**Type**: \(.issue_type)\n\n\(.description // "No description")\n\n**Dependencies**: " + (if (.dependencies | length) > 0 then (.dependencies | join(", ")) else "None" end) + "\n"' >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" << EOF

### P2 Medium Priority

EOF

bd list --priority 2 --status open --json | jq -r '.[] | "#### \(.id): \(.title)\n**Type**: \(.issue_type)\n\n\(.description // "No description")\n\n**Dependencies**: " + (if (.dependencies | length) > 0 then (.dependencies | join(", ")) else "None" end) + "\n"' >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" << EOF

### P3 Lower Priority

EOF

bd list --priority 3 --status open --json | jq -r '.[] | "#### \(.id): \(.title)\n**Type**: \(.issue_type)\n\n\(.description // "No description")\n\n**Dependencies**: " + (if (.dependencies | length) > 0 then (.dependencies | join(", ")) else "None" end) + "\n"' >> "$OUTPUT_FILE"

# Export completed tasks
cat >> "$OUTPUT_FILE" << EOF

---

## Completed Work

**Total Completed**: $CLOSED tasks ($COMPLETION_PCT%)

EOF

bd list --status closed --json | jq -r '.[] | "#### ✅ \(.id): \(.title)\n**Priority**: P\(.priority) | **Type**: \(.issue_type) | **Closed**: \(.closed_at)\n\n\(.close_reason // "No reason provided")\n"' >> "$OUTPUT_FILE"

# Add dependency tree section
cat >> "$OUTPUT_FILE" << EOF

---

## Dependency Analysis

EOF

# Check if there are any dependencies
HAS_DEPS=$(bd list --json | jq '[.[] | select(.dependencies | length > 0)] | length')

if [ "$HAS_DEPS" -gt 0 ]; then
  echo "### Dependency Trees" >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
  echo "\`\`\`" >> "$OUTPUT_FILE"

  # Get all tasks with dependencies and show their trees
  bd list --json | jq -r '.[] | select(.dependencies | length > 0) | .id' | while read -r task_id; do
    echo "# Dependency tree for $task_id" >> "$OUTPUT_FILE"
    bd dep tree "$task_id" 2>/dev/null >> "$OUTPUT_FILE" || echo "No dependency tree available" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
  done

  echo "\`\`\`" >> "$OUTPUT_FILE"
else
  echo "No tasks with dependencies." >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
fi

# Add success criteria
cat >> "$OUTPUT_FILE" << EOF

---

## Success Criteria

### Production Readiness Checklist

The following critical and high-priority tasks must be completed for production deployment:

EOF

# Add checklist based on P0 and P1 tasks
bd list --json | jq -r '.[] | select(.priority <= 1) | "- [\(if .status == "closed" then "x" else " " end)] \(.title) (\(.id)) - P\(.priority)"' >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" << EOF

---

## Quick Commands

\`\`\`bash
# View current implementation plan (this file)
./scripts/export-implementation-plan.sh

# View current sprint snapshot
./scripts/export-current-sprint.sh

# Task management in bd
bd list                     # List all tasks
bd ready                    # Show unblocked tasks
bd blocked                  # Show blocked tasks
bd stats                    # Show statistics
bd show <task-id>           # Show task details
bd dep tree <task-id>       # View dependency tree

# Filter tasks
bd list --priority 0        # Show P0 tasks
bd list --status open       # Show open tasks
bd list --type bug          # Show bugs

# Create new task
bd create "Task title" -p 1 -t feature -d "Description"

# Update task
bd update <task-id> --status in_progress
bd update <task-id> --priority 0
bd update <task-id> --assignee alice

# Manage dependencies
bd dep add <task-1> <task-2>    # task-2 blocks task-1
bd dep tree <task-id>           # View dependency tree

# Close task
bd close <task-id> --reason "Completed in PR #123"
\`\`\`

---

## References

### Active Documentation
- **This Plan**: \`IMPLEMENTATION_PLAN.md\` (high-level roadmap)
- **Current Sprint**: \`CURRENT_SPRINT.md\` (weekly snapshot)
- **Main Instructions**: \`CLAUDE.md\` (development guidelines)

### Detailed Plans
- **Quality Monitoring**: \`claudedocs/QUALITY_MONITORING_IMPLEMENTATION_PLAN.md\`
- **Loading State Audit**: \`claudedocs/loading_states_audit_report.md\`
- **Test Coverage**: \`backend/TEST_COVERAGE_REPORT.md\`
- **Test Analysis**: \`docs/POST_DEPLOYMENT_TEST_REPORT.md\`

### Task Management
- **Source of Truth**: bd database (\`.beads/*.db\`)
- **Git Sync**: Auto-synced via JSONL (\`.beads/*.jsonl\`)
- **Export Scripts**: \`scripts/export-*.sh\`
- **Statistics**: Run \`bd stats\` for real-time metrics

---

**Generated**: $DATE
**Command**: \`./scripts/export-implementation-plan.sh\`
**Source of Truth**: bd database (priority and status-driven)
EOF

echo -e "${GREEN}✓ Export complete: $OUTPUT_FILE${NC}"
echo -e "${YELLOW}⚠ Remember: bd is the source of truth for task status${NC}"
echo -e "${BLUE}Update tasks with: bd update <task-id> --status <status>${NC}"
