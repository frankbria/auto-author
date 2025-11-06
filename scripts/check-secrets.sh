#!/bin/bash
#
# Git pre-commit hook to prevent committing secrets, keys, and sensitive files
#

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get list of files being committed
FILES=$(git diff --cached --name-only --diff-filter=ACM)

# Exit if no files to check
if [ -z "$FILES" ]; then
    exit 0
fi

FOUND_SECRETS=0

# Check for .pem files
PEM_FILES=$(echo "$FILES" | grep -E '\.pem$')
if [ -n "$PEM_FILES" ]; then
    echo -e "${RED}ERROR: Attempting to commit .pem files:${NC}"
    echo "$PEM_FILES"
    FOUND_SECRETS=1
fi

# Patterns to detect secrets
PATTERNS=(
    # AWS keys
    'AKIA[0-9A-Z]{16}'
    # Generic API keys and secrets
    '[aA][pP][iI][-_]?[kK][eE][yY].*['\''"][0-9a-zA-Z]{32,}['\''"]'
    '[sS][eE][cC][rR][eE][tT].*['\''"][0-9a-zA-Z]{32,}['\''"]'
    '[pP][aA][sS][sS][wW][oO][rR][dD].*['\''"][^'\''\"]{8,}['\''"]'
    '[tT][oO][kK][eE][nN].*['\''"][0-9a-zA-Z]{32,}['\''"]'
    # OAuth tokens
    'ghp_[0-9a-zA-Z]{36}'
    'gho_[0-9a-zA-Z]{36}'
    'github_pat_[0-9a-zA-Z_]{82}'
    # Slack tokens
    'xox[baprs]-[0-9a-zA-Z-]+'
    # Generic base64 encoded strings in config (likely secrets)
    '[aA][uU][tT][hH].*['\''"][A-Za-z0-9+/]{40,}={0,2}['\''"]'
    # JWT tokens (real tokens, not examples)
    'eyJ[A-Za-z0-9_-]{100,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'
)

# Check each file for secret patterns
for FILE in $FILES; do
    # Skip binary files
    if git diff --cached --numstat "$FILE" | grep -q '^-'; then
        continue
    fi

    # Get the content being committed
    CONTENT=$(git diff --cached "$FILE")

    for PATTERN in "${PATTERNS[@]}"; do
        MATCHES=$(echo "$CONTENT" | grep -E "$PATTERN" | head -5)
        if [ -n "$MATCHES" ]; then
            if [ $FOUND_SECRETS -eq 0 ]; then
                echo -e "${RED}ERROR: Potential secrets detected in staged files!${NC}"
                echo ""
            fi
            echo -e "${YELLOW}File: $FILE${NC}"
            echo "Matched pattern: $PATTERN"
            echo "Context:"
            echo "$MATCHES" | sed 's/^/  /'
            echo ""
            FOUND_SECRETS=1
        fi
    done
done

if [ $FOUND_SECRETS -eq 1 ]; then
    echo -e "${RED}Commit rejected: Remove secrets before committing${NC}"
    echo ""
    echo "If this is a false positive, you can:"
    echo "  1. Remove the actual secret and use environment variables instead"
    echo "  2. Add the pattern to .gitignore"
    echo "  3. Use 'git commit --no-verify' to bypass this check (NOT recommended)"
    exit 1
fi

exit 0
