#!/bin/bash

set -e

echo "==================================================================="
echo "CORS Configuration Validation Script"
echo "==================================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test CORS for a given origin and API endpoint
test_cors() {
    local origin=$1
    local api_url=$2
    local endpoint=${3:-"/api/v1/books"}

    echo "Testing CORS for origin: ${origin}"
    echo "API endpoint: ${api_url}${endpoint}"
    echo "-------------------------------------------------------------------"

    # Perform OPTIONS preflight request
    response=$(curl -s -I -X OPTIONS \
        -H "Origin: ${origin}" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: Content-Type,Authorization" \
        "${api_url}${endpoint}" 2>&1)

    # Check if curl succeeded
    if [ $? -ne 0 ]; then
        echo -e "${RED}[FAIL]${NC} Failed to connect to ${api_url}"
        echo "Error: ${response}"
        return 1
    fi

    # Check for Access-Control-Allow-Origin header
    if echo "${response}" | grep -q "Access-Control-Allow-Origin"; then
        allowed_origin=$(echo "${response}" | grep "Access-Control-Allow-Origin" | cut -d' ' -f2 | tr -d '\r')

        if [[ "${allowed_origin}" == "${origin}" ]] || [[ "${allowed_origin}" == "*" ]]; then
            echo -e "${GREEN}[PASS]${NC} Access-Control-Allow-Origin: ${allowed_origin}"
        else
            echo -e "${RED}[FAIL]${NC} Expected origin '${origin}' but got '${allowed_origin}'"
            return 1
        fi
    else
        echo -e "${RED}[FAIL]${NC} Access-Control-Allow-Origin header not found"
        echo "Response headers:"
        echo "${response}"
        return 1
    fi

    # Check for Access-Control-Allow-Methods
    if echo "${response}" | grep -q "Access-Control-Allow-Methods"; then
        methods=$(echo "${response}" | grep "Access-Control-Allow-Methods" | cut -d' ' -f2- | tr -d '\r')
        echo -e "${GREEN}[PASS]${NC} Access-Control-Allow-Methods: ${methods}"
    else
        echo -e "${YELLOW}[WARN]${NC} Access-Control-Allow-Methods header not found"
    fi

    # Check for Access-Control-Allow-Headers
    if echo "${response}" | grep -q "Access-Control-Allow-Headers"; then
        headers=$(echo "${response}" | grep "Access-Control-Allow-Headers" | cut -d' ' -f2- | tr -d '\r')
        echo -e "${GREEN}[PASS]${NC} Access-Control-Allow-Headers: ${headers}"
    else
        echo -e "${YELLOW}[WARN]${NC} Access-Control-Allow-Headers header not found"
    fi

    # Check for Access-Control-Allow-Credentials
    if echo "${response}" | grep -q "Access-Control-Allow-Credentials"; then
        credentials=$(echo "${response}" | grep "Access-Control-Allow-Credentials" | cut -d' ' -f2 | tr -d '\r')
        echo -e "${GREEN}[PASS]${NC} Access-Control-Allow-Credentials: ${credentials}"
    else
        echo -e "${YELLOW}[WARN]${NC} Access-Control-Allow-Credentials header not found"
    fi

    echo ""
    return 0
}

# Parse command line arguments
ENVIRONMENT=${1:-"staging"}
FAILED_TESTS=0
TOTAL_TESTS=0

echo "Environment: ${ENVIRONMENT}"
echo ""

# Test based on environment
case "${ENVIRONMENT}" in
    "staging"|"dev")
        echo "Testing STAGING environment..."
        echo "==================================================================="
        echo ""

        # Test staging frontend -> staging backend
        ((TOTAL_TESTS++))
        if ! test_cors "https://dev.autoauthor.app" "https://api.dev.autoauthor.app"; then
            ((FAILED_TESTS++))
        fi

        # Test localhost -> staging backend (for local development)
        ((TOTAL_TESTS++))
        if ! test_cors "http://localhost:3000" "https://api.dev.autoauthor.app"; then
            ((FAILED_TESTS++))
        fi

        ((TOTAL_TESTS++))
        if ! test_cors "http://localhost:3003" "https://api.dev.autoauthor.app"; then
            ((FAILED_TESTS++))
        fi
        ;;

    "production"|"prod")
        echo "Testing PRODUCTION environment..."
        echo "==================================================================="
        echo ""

        # Test production frontend -> production backend
        ((TOTAL_TESTS++))
        if ! test_cors "https://autoauthor.app" "https://api.autoauthor.app"; then
            ((FAILED_TESTS++))
        fi

        # Also verify staging still works (shouldn't break existing environments)
        ((TOTAL_TESTS++))
        if ! test_cors "https://dev.autoauthor.app" "https://api.autoauthor.app"; then
            ((FAILED_TESTS++))
        fi
        ;;

    "local")
        echo "Testing LOCAL environment..."
        echo "==================================================================="
        echo ""

        # Test local development
        ((TOTAL_TESTS++))
        if ! test_cors "http://localhost:3000" "http://localhost:8000"; then
            ((FAILED_TESTS++))
        fi

        ((TOTAL_TESTS++))
        if ! test_cors "http://localhost:3002" "http://localhost:8000"; then
            ((FAILED_TESTS++))
        fi
        ;;

    *)
        echo -e "${RED}[ERROR]${NC} Unknown environment: ${ENVIRONMENT}"
        echo "Usage: $0 [staging|production|local]"
        exit 1
        ;;
esac

# Summary
echo "==================================================================="
echo "VALIDATION SUMMARY"
echo "==================================================================="
echo "Total tests: ${TOTAL_TESTS}"
echo "Passed: $((TOTAL_TESTS - FAILED_TESTS))"
echo "Failed: ${FAILED_TESTS}"
echo ""

if [ ${FAILED_TESTS} -eq 0 ]; then
    echo -e "${GREEN}[SUCCESS]${NC} All CORS validation tests passed!"
    exit 0
else
    echo -e "${RED}[FAILURE]${NC} ${FAILED_TESTS} CORS validation test(s) failed"
    echo ""
    echo "Common fixes:"
    echo "1. Check backend/app/core/config.py for correct CORS origins"
    echo "2. Verify environment variables in .env or deployment config"
    echo "3. Ensure the backend service is running and accessible"
    echo "4. Check nginx configuration for proper proxy headers"
    exit 1
fi
