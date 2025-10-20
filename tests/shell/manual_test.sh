#!/bin/bash
# Simple manual testing helper for Knock Lambda

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables from .env files
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Get function URL
cd "$PROJECT_ROOT"
FUNCTION_URL=$(./pumi stack output function_url 2>/dev/null | grep -E "^https://" || echo "")

if [ -z "$FUNCTION_URL" ]; then
    echo "❌ Could not get function URL from Pulumi stack"
    echo "Make sure the stack is deployed with: ./pumi up"
    exit 1
fi

echo "🚀 Knock Lambda Manual Tester"
echo "=============================="
echo "Function URL: $FUNCTION_URL"
echo ""

# Function to test with ACSM file
test_acsm_file() {
    local acsm_file="$1"
    
    if [ ! -f "$acsm_file" ]; then
        echo "❌ File not found: $acsm_file"
        return 1
    fi
    
    echo "📂 Processing ACSM file: $acsm_file"
    
    # Read and prepare ACSM content
    local acsm_content=$(cat "$acsm_file" | jq -R -s '.')
    local payload="{\"acsm_content\": $acsm_content}"
    
    echo "📡 Sending request..."
    echo ""
    
    # Make the request with verbose output
    curl -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$FUNCTION_URL" \
        -w "\n\n📊 HTTP Status: %{http_code}\n⏱️  Total time: %{time_total}s\n📦 Response size: %{size_download} bytes\n" | jq . 2>/dev/null || cat
}

# Function to test with custom content
test_custom_content() {
    local content="$1"
    
    echo "📝 Testing with custom content: $content"
    
    local payload="{\"acsm_content\": \"$content\"}"
    
    echo "📡 Sending request..."
    echo ""
    
    curl -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$FUNCTION_URL" \
        -w "\n\n📊 HTTP Status: %{http_code}\n⏱️  Total time: %{time_total}s\n" | jq . 2>/dev/null || cat
}

# Function to test basic connectivity
test_basic() {
    echo "🔌 Testing basic connectivity..."
    
    local payload='{"test": "basic_connectivity"}'
    
    curl -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$FUNCTION_URL" \
        -w "\n\n📊 HTTP Status: %{http_code}\n⏱️  Total time: %{time_total}s\n" | jq . 2>/dev/null || cat
}

# Show usage
show_usage() {
    echo "Usage: $0 [option] [argument]"
    echo ""
    echo "Options:"
    echo "  basic                    - Test basic connectivity"
    echo "  file <path>             - Test with ACSM file"
    echo "  content <text>          - Test with custom content"
    echo "  asset                   - Test with bundled asset file"
    echo ""
    echo "Examples:"
    echo "  $0 basic"
    echo "  $0 file /path/to/file.acsm"
    echo "  $0 content 'Some test content'"
    echo "  $0 asset"
}

# Main logic
case "${1:-}" in
    "basic")
        test_basic
        ;;
    "file")
        if [ -z "$2" ]; then
            echo "❌ Please provide file path"
            show_usage
            exit 1
        fi
        test_acsm_file "$2"
        ;;
    "content")
        if [ -z "$2" ]; then
            echo "❌ Please provide content string"
            show_usage
            exit 1
        fi
        test_custom_content "$2"
        ;;
    "asset")
        asset_file="$PROJECT_ROOT/assets/The_Chemical_Muse-epub.acsm"
        if [ -f "$asset_file" ]; then
            test_acsm_file "$asset_file"
        else
            echo "❌ Asset file not found: $asset_file"
            exit 1
        fi
        ;;
    *)
        show_usage
        exit 1
        ;;
esac