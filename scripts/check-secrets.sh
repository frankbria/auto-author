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
    # Require an actual assignment between the name and the quoted value, the
    # same narrowing the NEXT_PUBLIC_ pattern below uses. This is the loosest
    # pattern in the set — its value side accepts any 8+ characters, where the
    # api-key/secret/token patterns demand a 32+ char alphanumeric run — so
    # without an operator it fired on any identifier merely CONTAINING
    # "password" that happened to sit near a quoted string. The real case that
    # blocked #411: `const { sendPasswordResetEmail } = await import("@/lib/email")`
    # matched on "Password" + ".*" + the quoted module path.
    #
    # The name-continuation class must include - and . alongside word chars:
    # with [A-Za-z0-9_]* alone the match stopped at the hyphen and could never
    # reach the operator, silently dropping YAML/JSON keys like
    # `password-value: "..."` and `"password-field": "..."` that the old pattern
    # did catch. (`db-password: "..."` was unaffected — there the hyphen precedes
    # the word.) Bounded repetition of a restricted class still can't cross the
    # " } = await import(" in the false positive above, because `}` and space are
    # outside the class and the operator must follow immediately.
    '[pP][aA][sS][sS][wW][oO][rR][dD][A-Za-z0-9_.-]*['\''"]?[[:space:]]*[=:][[:space:]]*['\''"][^'\''\"]{8,}['\''"]'
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
    # Secrets assigned to a NEXT_PUBLIC_ name (#343). Next.js inlines every
    # NEXT_PUBLIC_* var into the client bundle at build time, so the value is
    # published to every visitor regardless of how it is stored. Here the
    # variable NAME is the defect, not the value. Requiring a trailing = or :
    # limits this to actual assignments (.env, docs, workflow yaml), so prose
    # warning against the anti-pattern does not trip the check.
    # A bare _KEY suffix is deliberately NOT matched: plenty of publishable
    # keys are meant to be public (NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY,
    # NEXT_PUBLIC_SENTRY_DSN), so matching it would be mostly false positives.
    # A genuinely secret NEXT_PUBLIC_*_KEY still needs human review.
    # The optional quote before the operator also catches JSON and quoted JS
    # object keys, where a quote character sits between the name and the colon.
    'NEXT_PUBLIC_[A-Z0-9_]*(SECRET|PRIVATE_KEY|PASSWORD|CREDENTIALS?)[A-Z0-9_]*['\''"]?[[:space:]]*[=:]'
)

# Check each file for secret patterns
for FILE in $FILES; do
    # This script cannot scan itself. The PATTERNS array above is, by
    # construction, a list of strings that look exactly like the secrets it
    # hunts for — every rule added here would flag its own definition. Skipping
    # it is a false-positive fix, not a coverage gap: the file holds no
    # credentials, and changes to it get reviewed precisely because it is the
    # scanner.
    if [ "$FILE" = "scripts/check-secrets.sh" ]; then
        continue
    fi

    # Skip binary files
    if git diff --cached --numstat "$FILE" | grep -q '^-'; then
        continue
    fi

    # Skip files that are typically large and don't contain secrets
    case "$FILE" in
        *.lock|package-lock.json|yarn.lock|*.min.js|*.bundle.js|*.map|*.svg|*.woff*|*.ttf|*.eot|*.otf)
            continue
            ;;
    esac

    # Skip files larger than 100KB (byte size check)
    if [ -f "$FILE" ]; then
        # Try GNU stat first, fall back to macOS stat
        FILE_BYTES=$(stat -c%s "$FILE" 2>/dev/null || stat -f%z "$FILE" 2>/dev/null || echo 0)
        if [ "$FILE_BYTES" -gt 102400 ]; then
            continue
        fi
    fi

    # Additional safeguard: skip files with very large diffs (>10000 lines changed)
    LINES_CHANGED=$(git diff --cached --numstat "$FILE" | awk '{print $1 + $2}')
    if [ -n "$LINES_CHANGED" ] && [ "$LINES_CHANGED" -gt 10000 ]; then
        continue
    fi

    # Get the content being ADDED (only '+' lines, excluding the '+++' file header).
    # Scanning added lines only — not removed/context lines — so that deleting a
    # hardcoded secret or editing nearby code doesn't falsely block the commit.
    # Capped at 100KB, matching the file-size guard above rather than a smaller
    # arbitrary number: at 10KB a secret added past the first ~10KB of a file's
    # diff was silently skipped, so whether a leak was caught depended on where
    # in the file it landed. The two guards above already bound the work.
    CONTENT=$(git diff --cached "$FILE" | grep '^+' | grep -v '^+++' | head -c 102400)

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
