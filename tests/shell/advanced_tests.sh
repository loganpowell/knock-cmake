#!/bin/bash
# Advanced test scenarios for the Knock Lambda function

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$SCRIPT_DIR/results"

# Get function URL
cd "$PROJECT_ROOT"
FUNCTION_URL=$(./pumi stack output function_url 2>/dev/null | grep -E "^https://" || echo "")

if [ -z "$FUNCTION_URL" ]; then
    echo -e "${RED}❌ Could not get function URL${NC}"
    exit 1
fi

echo -e "${BLUE}🔧 Running advanced tests...${NC}"
echo "Function URL: $FUNCTION_URL"

# Test 1: Concurrent requests
test_concurrent_requests() {
    echo -e "\n${BLUE}Testing concurrent requests...${NC}"
    
    local acsm_file="$PROJECT_ROOT/assets/The_Chemical_Muse-epub.acsm"
    if [ ! -f "$acsm_file" ]; then
        echo "❌ ACSM file not found"
        return 1
    fi
    
    local acsm_content=$(cat "$acsm_file" | jq -R -s '.')
    local payload="{\"acsm_content\": $acsm_content}"
    
    echo "🚀 Launching 3 concurrent requests..."
    
    # Launch 3 requests in background
    for i in {1..3}; do
        {
            echo "🔄 Request $i starting..."
            local http_code=$(curl -s -w "%{http_code}" \
                -X POST \
                -H "Content-Type: application/json" \
                -d "$payload" \
                "$FUNCTION_URL" \
                -o "$RESULTS_DIR/concurrent_${i}_response.json")
            echo "✅ Request $i completed with status: $http_code"
        } &
    done
    
    # Wait for all background jobs
    wait
    echo "✅ All concurrent requests completed"
}

# Test 2: Response time measurement
test_response_time() {
    echo -e "\n${BLUE}Testing response time...${NC}"
    
    local payload='{"test": "timing"}'
    local start_time=$(date +%s.%N)
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$FUNCTION_URL" \
        -o "$RESULTS_DIR/timing_response.json"
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)
    
    echo "⏱️  Response time: ${duration}s"
    
    # Check if response time is reasonable (under 30 seconds for cold start)
    if (( $(echo "$duration < 30" | bc -l) )); then
        echo "✅ Response time is acceptable"
    else
        echo "⚠️  Response time is slow (may be cold start)"
    fi
}

# Test 3: Memory and error handling
test_memory_stress() {
    echo -e "\n${BLUE}Testing memory stress...${NC}"
    
    # Create a very large payload to test memory limits
    echo "Creating large payload..."
    local large_content=$(python3 -c "print('X' * 5000000)")  # 5MB payload
    local payload="{\"acsm_content\": \"$large_content\"}"
    
    echo "📡 Sending large payload..."
    local http_code=$(curl -s -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$FUNCTION_URL" \
        -o "$RESULTS_DIR/memory_stress_response.json" \
        --max-time 30)
    
    echo "📊 Status: $http_code"
    
    if [[ $http_code =~ ^[234][0-9][0-9]$ ]]; then
        echo "✅ Large payload handled successfully"
    else
        echo "ℹ️  Large payload rejected (expected for memory protection)"
    fi
}

# Test 4: Malformed JSON
test_malformed_json() {
    echo -e "\n${BLUE}Testing malformed JSON handling...${NC}"
    
    local malformed_payloads=(
        '{"incomplete": '
        '{"invalid": "json"'
        'not json at all'
        '{"acsm_content": "test", "extra_comma": ,}'
    )
    
    for i in "${!malformed_payloads[@]}"; do
        local payload="${malformed_payloads[$i]}"
        echo "🧪 Testing malformed JSON $((i+1)): $payload"
        
        local http_code=$(curl -s -w "%{http_code}" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "$FUNCTION_URL" \
            -o "$RESULTS_DIR/malformed_${i}_response.json" \
            2>/dev/null)
        
        if [[ $http_code =~ ^4[0-9][0-9]$ ]]; then
            echo "✅ Correctly rejected malformed JSON with status $http_code"
        else
            echo "⚠️  Unexpected status $http_code for malformed JSON"
        fi
    done
}

# Test 5: Different HTTP methods
test_http_methods() {
    echo -e "\n${BLUE}Testing different HTTP methods...${NC}"
    
    local methods=("GET" "PUT" "DELETE" "PATCH")
    
    for method in "${methods[@]}"; do
        echo "🌐 Testing $method method..."
        
        local http_code=$(curl -s -w "%{http_code}" \
            -X "$method" \
            -H "Content-Type: application/json" \
            "$FUNCTION_URL" \
            -o "$RESULTS_DIR/method_${method}_response.json" \
            2>/dev/null)
        
        echo "📊 $method returned status: $http_code"
        
        # Most Lambda functions only accept POST, so we expect 4xx for others
        if [[ $method == "POST" ]] && [[ $http_code =~ ^[234][0-9][0-9]$ ]]; then
            echo "✅ POST method works correctly"
        elif [[ $method != "POST" ]] && [[ $http_code =~ ^4[0-9][0-9]$ ]]; then
            echo "✅ $method correctly rejected"
        else
            echo "ℹ️  $method returned unexpected status $http_code"
        fi
    done
}

# Main execution
main() {
    echo -e "${YELLOW}🔬 Advanced Knock Lambda Tests${NC}"
    echo "=================================="
    
    mkdir -p "$RESULTS_DIR"
    
    test_concurrent_requests
    test_response_time
    test_memory_stress
    test_malformed_json
    test_http_methods
    
    echo -e "\n${GREEN}🏁 Advanced testing completed!${NC}"
    echo "📁 Results saved in: $RESULTS_DIR"
}

main "$@"