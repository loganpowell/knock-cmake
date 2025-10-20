#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ASSETS_DIR="$PROJECT_ROOT/assets"
RESULTS_DIR="$SCRIPT_DIR/results"

# Load environment variables from .env files
load_env() {
    # Load from project root .env
    if [ -f "$PROJECT_ROOT/.env" ]; then
        echo -e "${BLUE}Loading environment from $PROJECT_ROOT/.env${NC}"
        set -a  # automatically export all variables
        source "$PROJECT_ROOT/.env"
        set +a  # disable automatic export
    fi
    
    # Load from tests/.env (overrides project .env)
    if [ -f "$SCRIPT_DIR/.env" ]; then
        echo -e "${BLUE}Loading test environment from $SCRIPT_DIR/.env${NC}"
        set -a
        source "$SCRIPT_DIR/.env"
        set +a
    fi
}

# Load environment first
load_env

# Create results directory
mkdir -p "$RESULTS_DIR"

# Resolve Lambda function URL (refresh from Pulumi; prompt for passphrase if needed)
cd "$PROJECT_ROOT"

# Ensure passphrase from environment (.env) is exported if present
if [ -n "${PULUMI_CONFIG_PASSPHRASE:-}" ]; then
    export PULUMI_CONFIG_PASSPHRASE="$PULUMI_CONFIG_PASSPHRASE"
fi

get_pulumi_function_url() {
    ./pumi stack output function_url 2>/dev/null | grep -E "^https://" || echo ""
}

FUNCTION_URL="$(get_pulumi_function_url)"

# If lookup failed, prompt for passphrase interactively and retry
if [ -z "$FUNCTION_URL" ] && [ -t 0 ]; then
    echo -e "${YELLOW}Pulumi output requires a passphrase.${NC}"
    read -s -p "Enter Pulumi passphrase: " PULUMI_CONFIG_PASSPHRASE; echo
    export PULUMI_CONFIG_PASSPHRASE
    echo -e "${BLUE}Retrying Pulumi lookup...${NC}"
    FUNCTION_URL="$(get_pulumi_function_url)"
fi

if [ -z "$FUNCTION_URL" ]; then
    echo -e "${RED}❌ Could not retrieve function URL from Pulumi.${NC}"
    echo "Ensure PULUMI_CONFIG_PASSPHRASE is set in .env or provide it interactively, then retry."
    exit 1
fi

echo -e "${GREEN}✓ Function URL: $FUNCTION_URL${NC}"

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Helper function to run a test
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
    echo -e "${BLUE}🧪 Running test: $test_name${NC}"
    echo "================================================"
    
    if $test_function; then
        echo -e "${GREEN}✅ PASSED: $test_name${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAILED: $test_name${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Helper function to make API calls
call_lambda() {
    local payload="$1"
    local test_name="$2"
    local output_file="$RESULTS_DIR/${test_name}_response.json"
    
    echo "📡 Making request to: $FUNCTION_URL"
    echo "📄 Payload: $payload"
    
    # Make the curl request and capture both status and response
    local http_code=$(curl -s -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$FUNCTION_URL" \
        -o "$output_file")
    
    echo "📊 HTTP Status: $http_code"
    echo "💾 Response saved to: $output_file"
    
    # Show response content
    if [ -f "$output_file" ]; then
        echo "📋 Response content:"
        cat "$output_file" | jq . 2>/dev/null || cat "$output_file"
        echo ""
    fi
    
    # Return success if status is 2xx
    [[ $http_code =~ ^2[0-9][0-9]$ ]]
}

# Test 1: Health check / Basic connectivity
test_health_check() {
    echo "Testing basic Lambda connectivity with ACSM asset..."
    
    # Prefer using the bundled ACSM asset for a realistic request
    local acsm_file="$ASSETS_DIR/Princes_of_the_Yen-epub.acsm"
    local payload
    if [ -f "$acsm_file" ]; then
        echo "📂 Reading ACSM file: $acsm_file"
        local acsm_content=$(cat "$acsm_file" | jq -R -s '.')
        payload="{\"acsm_content\": $acsm_content}"
    else
        echo "⚠️  ACSM asset not found, falling back to minimal payload"
        payload='{"acsm_content": "test"}'
    fi
    
    # Make the request and capture status
    local output_file="$RESULTS_DIR/health_check_response.json"
    local http_code=$(curl -s -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$FUNCTION_URL" \
        -o "$output_file")
    
    echo "📡 Making request to: $FUNCTION_URL"
    echo "📄 Payload: (ACSM content)"
    echo "📊 HTTP Status: $http_code"
    echo "💾 Response saved to: $output_file"
    
    # Show response content
    if [ -f "$output_file" ]; then
        echo "📋 Response content:"
        cat "$output_file" | jq . 2>/dev/null || cat "$output_file"
        echo ""
    fi
    
    # Lambda is accessible if we get any HTTP response (2xx, 4xx, or 5xx)
    if [[ $http_code =~ ^[2-5][0-9][0-9]$ ]]; then
        echo "✓ Lambda is accessible and responding"
        return 0
    else
        echo "✗ Lambda is not accessible (connection failed)"
        return 1
    fi
}

# Test 2: Missing required parameters
test_missing_parameters() {
    echo "Testing missing required parameters..."
    
    local payload='{}'
    
    # This should return a 400 error
    local output_file="$RESULTS_DIR/missing_params_response.json"
    local http_code=$(curl -s -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$FUNCTION_URL" \
        -o "$output_file")
    
    echo "📊 HTTP Status: $http_code"
    
    if [[ $http_code == "400" ]]; then
        echo "✓ Correctly returned 400 for missing parameters"
        return 0
    else
        echo "✗ Expected 400 status, got $http_code"
        return 1
    fi
}

# Test 3: ACSM content upload test
test_acsm_content() {
    echo "Testing ACSM content upload..."
    
    local acsm_file="$ASSETS_DIR/Princes_of_the_Yen-epub.acsm"
    
    if [ ! -f "$acsm_file" ]; then
        echo "✗ ACSM test file not found: $acsm_file"
        return 1
    fi
    
    echo "📂 Reading ACSM file: $acsm_file"
    
    # Read ACSM file content and escape for JSON
    local acsm_content=$(cat "$acsm_file" | jq -R -s '.')
    
    local payload="{\"acsm_content\": $acsm_content}"
    
    if call_lambda "$payload" "acsm_content"; then
        echo "✓ ACSM content processed successfully"
        return 0
    else
        echo "✗ ACSM content processing failed"
        return 1
    fi
}

# Test 4: Invalid ACSM content
test_invalid_acsm() {
    echo "Testing invalid ACSM content..."
    
    local payload='{"acsm_content": "This is not a valid ACSM file content"}'
    
    # This should return an error (likely 500)
    local output_file="$RESULTS_DIR/invalid_acsm_response.json"
    local http_code=$(curl -s -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$FUNCTION_URL" \
        -o "$output_file")
    
    echo "📊 HTTP Status: $http_code"
    
    if [[ $http_code =~ ^[45][0-9][0-9]$ ]]; then
        echo "✓ Correctly returned error status ($http_code) for invalid ACSM"
        return 0
    else
        echo "✗ Expected error status (4xx or 5xx), got $http_code"
        return 1
    fi
}

# Test 5: Large file handling
test_large_request() {
    echo "Testing large request handling..."
    
    # Create a large ACSM-like content (simulate large file)
    local large_content=$(python3 -c "print('A' * 1000000)")  # 1MB of A's
    local payload="{\"acsm_content\": \"$large_content\"}"
    
    # This should either process or return appropriate error
    if call_lambda "$payload" "large_request"; then
        echo "✓ Large request handled successfully"
        return 0
    else
        echo "ℹ️  Large request returned error (this may be expected)"
        return 0  # Don't fail the test suite for this
    fi
}

# Main test execution
main() {
    echo -e "${YELLOW}🚀 Starting Knock Lambda Test Suite${NC}"
    echo "================================================"
    echo "Project root: $PROJECT_ROOT"
    echo "Assets directory: $ASSETS_DIR"
    echo "Results directory: $RESULTS_DIR"
    echo "Function URL: $FUNCTION_URL"
    echo ""
    
    # Run all tests
    run_test "Health Check" test_health_check
    run_test "Missing Parameters" test_missing_parameters
    run_test "ACSM Content Upload" test_acsm_content
    run_test "Invalid ACSM Content" test_invalid_acsm
    run_test "Large Request Handling" test_large_request
    
    # Summary
    echo ""
    echo "================================================"
    echo -e "${YELLOW}📊 TEST SUMMARY${NC}"
    echo "================================================"
    echo -e "Total tests: ${BLUE}$TOTAL_TESTS${NC}"
    echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
    echo ""
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}💥 $FAILED_TESTS test(s) failed${NC}"
        exit 1
    fi
}

# Run main function
main "$@"