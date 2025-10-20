#!/bin/bash

# Knock Lambda Deployment Script
# One-command deployment that ensures everything is ready for testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load platform compatibility layer
source "$SCRIPT_DIR/shell_scripts/platform-compat.sh"

cd "$SCRIPT_DIR"

echo "🚀 Starting Knock Lambda deployment..."
echo "================================================"

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v pulumi &> /dev/null; then
    echo "❌ Error: pulumi is not installed"
    echo "   Install from: https://www.pulumi.com/docs/get-started/install/"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ Error: aws CLI is not installed"
    exit 1
fi

# Verify AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Error: AWS credentials not configured"
    exit 1
fi

echo "✅ Prerequisites OK"
echo ""

# Run pulumi up
echo "🔨 Deploying infrastructure with Pulumi..."
echo "================================================"

if [ "$1" = "--yes" ] || [ "$1" = "-y" ]; then
    pulumi up --yes
else
    pulumi up
fi

# Get the function URL
echo ""
echo "🔍 Retrieving deployment information..."
FUNCTION_URL=$(pulumi stack output function_url 2>/dev/null || echo "")
FUNCTION_NAME=$(pulumi stack output lambda_function_name 2>/dev/null || echo "")

if [ -z "$FUNCTION_URL" ]; then
    echo "⚠️  Could not retrieve function URL from Pulumi outputs"
    echo "Check 'pulumi stack output' for deployment details"
    exit 1
fi

echo ""
echo "✅ Deployment complete!"
echo "================================================"
echo ""
echo "📊 Deployment Summary:"
echo "  Function Name: $FUNCTION_NAME"
echo "  Function URL:  $FUNCTION_URL"
echo ""

# Find ACSM file for testing
ACSM_FILE="$PROJECT_ROOT/assets/Princes_of_the_Yen-epub.acsm"

if [ ! -f "$ACSM_FILE" ]; then
    echo "⚠️  ACSM test file not found at: $ACSM_FILE"
    echo "Skipping functional test, but Lambda is deployed."
    echo ""
    echo "To run the full test suite:"
    echo "  cd ../tests && ./run_tests.sh"
    exit 0
fi

echo "🧪 Testing Lambda with real ACSM file..."
echo "  Test file: $(basename "$ACSM_FILE")"

# Read ACSM content
ACSM_CONTENT=$(cat "$ACSM_FILE" | jq -Rs .)

# Test with actual ACSM content
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "{\"acsm_content\": $ACSM_CONTENT}" \
    "$FUNCTION_URL" 2>&1 || echo "error\n000")

# Use platform-compatible functions
HTTP_CODE=$(echo "$RESPONSE" | get_last_line)
BODY=$(echo "$RESPONSE" | all_but_last_line)

echo ""
echo "Response: HTTP $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Lambda successfully processed ACSM file!"
    echo ""
    # Try to pretty-print JSON response
    if echo "$BODY" | jq . &> /dev/null; then
        echo "Response preview:"
        echo "$BODY" | jq -C '.' | head -20
    fi
    echo ""
    echo "🎉 Ready for production use!"
elif [ "$HTTP_CODE" = "500" ]; then
    echo "❌ Lambda returned an error"
    echo ""
    if echo "$BODY" | jq . &> /dev/null; then
        echo "Error details:"
        echo "$BODY" | jq -C '.'
        
        # Check for the shared library error we're trying to fix
        if echo "$BODY" | grep -q "libcrypto.so.3"; then
            echo ""
            echo "⚠️  SHARED LIBRARY ERROR DETECTED"
            echo "The build still has dynamic linking issues."
            echo "Run another build cycle with:"
            echo "  cd $SCRIPT_DIR && bash shell_scripts/codebuild-runner-with-digest.sh \"knock-lambda-build-dev\" \"us-east-2\" \"3\" \"10\" \"60\""
        fi
    else
        echo "Error response: $BODY"
    fi
    exit 1
else
    echo "⚠️  Unexpected response (HTTP $HTTP_CODE)"
    echo "Response: $BODY"
    echo ""
    echo "Lambda may still be initializing. To retry:"
    echo "  cd ../tests && ./run_tests.sh"
fi

echo ""
echo "To run the full test suite:"
echo "  cd ../tests && ./run_tests.sh"
echo ""
