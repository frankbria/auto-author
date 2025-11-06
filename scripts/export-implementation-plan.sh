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

# Create header
cat > "$OUTPUT_FILE" << EOF
# Auto-Author Implementation Plan

**Last Updated**: $DATE
**Status**: Active Development
**Current Phase**: Sprint 3-4 - Production Ready
**Source**: High-level plan with bd task references

> ℹ️ **NOTE**: This is a high-level implementation roadmap.
> For current task status and details, run: \`bd list\` or \`bd ready\`
> To update this plan, run: \`./scripts/export-implementation-plan.sh\`

---

## Executive Summary

This document serves as the single source of truth for the Auto-Author implementation roadmap. It consolidates all planning documents into a unified, phase-based structure aligned with the project's evolution from MVP to production-ready application.

**Task Management**: All tasks are tracked in bd (Beads issue tracker).
- View tasks: \`bd list\`
- Ready work: \`bd ready\`
- Task details: \`bd show <task-id>\`

### Project Status Overview

EOF

# Get sprint statistics
TOTAL=$(bd list --json | jq 'length')
CLOSED=$(bd list --status closed --json | jq 'length')
OPEN=$(bd list --status open --json | jq 'length')
IN_PROGRESS=$(bd list --status in_progress --json | jq 'length')

# Calculate percentage
COMPLETION_PCT=0
if [ "$TOTAL" -gt 0 ]; then
  COMPLETION_PCT=$((CLOSED * 100 / TOTAL))
fi

cat >> "$OUTPUT_FILE" << EOF
- ✅ **MVP Complete**: Core authoring workflow functional
- ✅ **Sprint 1-2**: Rich text editing and AI integration complete
- 🚧 **Sprint 3-4**: Production readiness - $COMPLETION_PCT% complete ($CLOSED/$TOTAL tasks)
- 📋 **Sprint 5-6**: Enhanced features (planned)

### Task Summary
- **Total Tasks**: $TOTAL
- **Completed**: $CLOSED ($COMPLETION_PCT%)
- **In Progress**: $IN_PROGRESS
- **Open**: $OPEN

---

## Sprint 3-4: Production Ready (CURRENT)

**Timeline**: 6 weeks
**Progress**: $CLOSED/$TOTAL tasks complete ($COMPLETION_PCT%)
**Focus**: Export, error handling, quality monitoring, API contracts, accessibility

### Active Tasks (In Progress)

EOF

# Export in-progress tasks with dependencies
bd list --status in_progress --json | jq -r '.[] | "#### \(.id): \(.title)\n**Priority**: P\(.priority) | **Assignee**: \(.assignee // "unassigned")\n\n\(.description // "No description")\n\n**Dependencies**:\n" + (if (.dependencies | length) > 0 then ([.dependencies[] | "- Blocked by: \(.)"] | join("\n")) else "- No dependencies\n" end) + "\n"' >> "$OUTPUT_FILE"

# Export ready tasks
echo "" >> "$OUTPUT_FILE"
echo "### Ready to Start (No Blockers)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

bd ready --json | jq -r '.[] | "#### \(.id): \(.title)\n**Priority**: P\(.priority)\n\n\(.description // "No description")\n"' >> "$OUTPUT_FILE"

# Export planned tasks
echo "" >> "$OUTPUT_FILE"
echo "### Planned Tasks (Open)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

bd list --status open --json | jq -r '.[] | "#### \(.id): \(.title)\n**Priority**: P\(.priority)\n\n\(.description // "No description")\n\n**Blocked by**: " + (if (.dependencies | length) > 0 then (.dependencies | join(", ")) else "None" end) + "\n"' >> "$OUTPUT_FILE"

# Export completed tasks
echo "" >> "$OUTPUT_FILE"
echo "### Completed Tasks" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

bd list --status closed --json | jq -r '.[] | "#### ✅ \(.id): \(.title)\n**Closed**: \(.closed_at) | **Priority**: P\(.priority)\n\n\(.close_reason // "No reason provided")\n"' >> "$OUTPUT_FILE"

# Add dependency tree section
echo "" >> "$OUTPUT_FILE"
echo "---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "## Dependency Trees" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "\`\`\`" >> "$OUTPUT_FILE"

# Get all tasks and show dependency trees for tasks with dependencies
bd list --json | jq -r '.[] | select(.dependencies | length > 0) | .id' | while read -r task_id; do
  echo "# Dependency tree for $task_id" >> "$OUTPUT_FILE"
  bd dep tree "$task_id" 2>/dev/null >> "$OUTPUT_FILE" || echo "No dependency tree" >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
done

echo "\`\`\`" >> "$OUTPUT_FILE"

# Add footer
cat >> "$OUTPUT_FILE" << EOF

---

## Success Criteria

### Production Ready Checklist

EOF

# Add checklist based on open tasks with P0/P1 priority
bd list --json | jq -r '.[] | select(.priority <= 1) | "- [\(if .status == "closed" then "x" else " " end)] \(.title) (\(.id))"' >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" << EOF

---

## Quick Commands

\`\`\`bash
# View current sprint snapshot
./scripts/export-current-sprint.sh

# View full implementation plan (this file)
./scripts/export-implementation-plan.sh

# Check task status in bd
bd list
bd ready                    # Show unblocked tasks
bd show <task-id>           # Show details
bd dep tree <task-id>       # View dependencies

# Create new task
bd create "Task title" -p 1 -t feature -d "Description"

# Update task
bd update <task-id> --status in_progress
bd update <task-id> --assignee alice

# Add dependency (task-2 blocks task-1)
bd dep add <task-1> <task-2>

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

### Task Management
- **Source of Truth**: bd database (\`.beads/*.db\`)
- **Git Sync**: Auto-synced via JSONL (\`.beads/*.jsonl\`)
- **Export Scripts**: \`scripts/export-*.sh\`

---

**Generated**: $DATE
**Command**: \`./scripts/export-implementation-plan.sh\`
**Source of Truth**: bd database + narrative context
EOF

echo -e "${GREEN}✓ Export complete: $OUTPUT_FILE${NC}"
echo -e "${YELLOW}⚠ Remember: bd is the source of truth for task status${NC}"
echo -e "${BLUE}Update tasks with: bd update <task-id> --status <status>${NC}"
