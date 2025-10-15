#!/bin/bash
# Archive completed sprint to archive/ directory
# Usage: ./scripts/archive-completed-sprint.sh <sprint-name>

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCHIVE_DIR="$PROJECT_ROOT/archive"
DATE=$(date +%Y%m%d)

# Check for sprint name argument
if [ -z "$1" ]; then
  echo "Usage: $0 <sprint-name>"
  echo "Example: $0 'Sprint-3-4'"
  exit 1
fi

SPRINT_NAME="$1"
OUTPUT_FILE="$ARCHIVE_DIR/SPRINT_${SPRINT_NAME}_${DATE}.md"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Archiving $SPRINT_NAME to $OUTPUT_FILE...${NC}"

# Create archive directory if it doesn't exist
mkdir -p "$ARCHIVE_DIR"

# Create header
cat > "$OUTPUT_FILE" << EOF
# Sprint Archive - $SPRINT_NAME

**Archived**: $DATE
**Sprint**: $SPRINT_NAME
**Source**: bd database snapshot

> ℹ️ **NOTE**: This is a historical snapshot of completed work.
> For current task status, use bd: \`bd list\`

---

## Sprint Summary

EOF

# Get all closed tasks
CLOSED_COUNT=$(bd list --status closed --json | jq 'length')

cat >> "$OUTPUT_FILE" << EOF
**Completed Tasks**: $CLOSED_COUNT

---

## Completed Work

EOF

# Export all closed tasks with full details
bd list --status closed --json | jq -r '.[] | "### ✅ \(.id): \(.title)\n\n**Priority**: P\(.priority) | **Closed**: \(.closed_at) | **Assignee**: \(.assignee // "unassigned")\n\n**Description**:\n\(.description // "No description")\n\n**Close Reason**:\n\(.close_reason // "No reason provided")\n\n**Dependencies**:\n" + (if (.dependencies | length) > 0 then ([.dependencies[] | "- \(.)"] | join("\n")) else "None\n" end) + "\n---\n"' >> "$OUTPUT_FILE"

# Add statistics
cat >> "$OUTPUT_FILE" << EOF

## Sprint Statistics

- **Total Completed**: $CLOSED_COUNT tasks
- **Archive Date**: $DATE
- **Sprint**: $SPRINT_NAME

---

## Database Snapshot

EOF

# Add raw JSON for complete data preservation
echo "\`\`\`json" >> "$OUTPUT_FILE"
bd list --status closed --json >> "$OUTPUT_FILE"
echo "\`\`\`" >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" << EOF

---

**Archived**: $DATE
**Command**: \`./scripts/archive-completed-sprint.sh '$SPRINT_NAME'\`
**Source**: bd database (\`.beads/*.db\`)
EOF

echo -e "${GREEN}✓ Archive complete: $OUTPUT_FILE${NC}"
echo -e "${YELLOW}Sprint '$SPRINT_NAME' archived with $CLOSED_COUNT completed tasks${NC}"
echo -e "${BLUE}View archived tasks: cat $OUTPUT_FILE${NC}"
