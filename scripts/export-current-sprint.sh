#!/bin/bash
# Export current sprint tasks from bd to CURRENT_SPRINT.md
# Usage: ./scripts/export-current-sprint.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_FILE="$PROJECT_ROOT/CURRENT_SPRINT.md"
SPRINT=""
DATE=$(date +%Y-%m-%d)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Exporting current sprint tasks to markdown...${NC}"

# Create header
cat > "$OUTPUT_FILE" << EOF
# Current Sprint - $SPRINT

**Last Updated**: $DATE

**Source**: Auto-generated from bd - DO NOT EDIT MANUALLY

> ⚠️ **WARNING**: This file is auto-generated from bd (Beads issue tracker).
> To update tasks, use: \`bd create\`, \`bd update\`, or \`bd close\`
> To regenerate this file, run: \`./scripts/export-current-sprint.sh\`

---

## 🎯 Current Sprint Status

EOF

# Export open tasks
echo "### 🚧 Active Tasks (In Progress)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
IN_PROGRESS_TASKS=$(bd list --status in_progress --json)
if [ "$IN_PROGRESS_TASKS" != "[]" ] && [ "$IN_PROGRESS_TASKS" != "null" ] && [ -n "$IN_PROGRESS_TASKS" ]; then
  echo "$IN_PROGRESS_TASKS" | jq -r '.[] | "- **[\(.id)]** \(.title)\n  - Status: \(.status)\n  - Priority: \(.priority)\n  - Assignee: \(.assignee // "unassigned")\n  - Created: \(.created_at)\n"' >> "$OUTPUT_FILE"
else
  echo "No tasks currently in progress." >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
fi

# Export ready tasks
echo "" >> "$OUTPUT_FILE"
echo "### ✅ Ready to Start" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
READY_TASKS=$(bd ready --json 2>/dev/null || echo "[]")
if [ "$READY_TASKS" != "[]" ] && [ -n "$READY_TASKS" ] && [ "$READY_TASKS" != "null" ]; then
  echo "$READY_TASKS" | jq -r '.[] | "- **[\(.id)]** \(.title)\n  - Priority: \(.priority)\n  - No blocking dependencies\n"' >> "$OUTPUT_FILE" 2>/dev/null || echo "Error parsing ready tasks" >> "$OUTPUT_FILE"
else
  echo "No tasks ready to start (all tasks may have dependencies)." >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
fi

# Export planned tasks
echo "" >> "$OUTPUT_FILE"
echo "### 📋 Planned (Open)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
OPEN_TASKS=$(bd list --status open --json)
if [ "$OPEN_TASKS" != "[]" ] && [ "$OPEN_TASKS" != "null" ] && [ -n "$OPEN_TASKS" ]; then
  echo "$OPEN_TASKS" | jq -r '.[] | "- **[\(.id)]** \(.title)\n  - Priority: \(.priority)\n"' >> "$OUTPUT_FILE"
else
  echo "No planned tasks." >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
fi

# Export completed tasks this week
echo "" >> "$OUTPUT_FILE"
echo "### ✅ Completed This Week" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
# Get tasks closed in last 7 days
CLOSED_TASKS=$(bd list --status closed --json)
if [ "$CLOSED_TASKS" != "[]" ] && [ "$CLOSED_TASKS" != "null" ] && [ -n "$CLOSED_TASKS" ]; then
  echo "$CLOSED_TASKS" | jq -r --arg week_ago "$(date -d '7 days ago' +%Y-%m-%d)" '.[] | select(.closed_at >= $week_ago) | "- **[\(.id)]** \(.title)\n  - Closed: \(.closed_at)\n  - Reason: \(.close_reason // "none")\n"' >> "$OUTPUT_FILE"
else
  echo "No tasks completed this week." >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
fi

# Add footer
cat >> "$OUTPUT_FILE" << EOF

---

## 📊 Sprint Metrics

EOF

# Calculate metrics from bd
TOTAL_ISSUES=$(bd list --json | jq 'length')
OPEN_ISSUES=$(bd list --status open --json | jq 'length')
IN_PROGRESS=$(bd list --status in_progress --json | jq 'length')
CLOSED_ISSUES=$(bd list --status closed --json | jq 'length')
READY_ISSUES=$(bd ready --json | jq 'length')

cat >> "$OUTPUT_FILE" << EOF
- **Total Issues**: $TOTAL_ISSUES
- **Open**: $OPEN_ISSUES
- **In Progress**: $IN_PROGRESS
- **Closed**: $CLOSED_ISSUES
- **Ready to Start**: $READY_ISSUES

---

## 🔗 Quick Commands

\`\`\`bash
# View all tasks
bd list

# View ready tasks (no blockers)
bd ready

# Show task details
bd show <task-id>

# Update task status
bd update <task-id> --status in_progress

# Create new task
bd create "Task title" -p 1 -t feature

# Add dependency (task-2 blocks task-1)
bd dep add <task-1> <task-2>
\`\`\`

---

**Generated**: $DATE
**Command**: \`./scripts/export-current-sprint.sh\`
**Source of Truth**: bd database (\`.beads/*.db\`)
EOF

echo -e "${GREEN}✓ Export complete: $OUTPUT_FILE${NC}"
echo -e "${BLUE}View tasks in bd: bd list${NC}"
echo -e "${BLUE}Show ready work: bd ready${NC}"
