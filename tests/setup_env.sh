#!/bin/bash
# Setup environment for testing

echo "🔧 Setting up test environment..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load existing .env if available
if [ -f ".env" ]; then
    echo "📁 Loading existing .env file..."
    set -a
    source .env
    set +a
fi

# Check if passphrase is set
if [ -z "${PULUMI_CONFIG_PASSPHRASE:-}" ]; then
    echo "⚠️  PULUMI_CONFIG_PASSPHRASE not set"
    echo "   You can set it in .env file or run:"
    echo "   export PULUMI_CONFIG_PASSPHRASE='your_passphrase'"
    echo ""
fi

# Check if stack is deployed
if ./pumi stack ls 2>/dev/null | grep -q "dev"; then
    echo "✅ Pulumi stack 'dev' found"
    
    # Try to get the function URL
    echo "🔍 Getting function URL..."
    FUNCTION_URL=$(./pumi stack output function_url 2>/dev/null | grep -E "^https://" || echo "")
    
    if [ -n "$FUNCTION_URL" ]; then
        echo "✅ Function URL retrieved: $FUNCTION_URL"
        
        # Update .env file with function URL
        if [ -f ".env" ]; then
            # Remove existing FUNCTION_URL line and add new one
            grep -v "^FUNCTION_URL=" .env > .env.tmp && mv .env.tmp .env
        fi
        echo "FUNCTION_URL='$FUNCTION_URL'" >> .env
        
        # Also save to tests/.env for local testing
        echo "export FUNCTION_URL='$FUNCTION_URL'" > "$SCRIPT_DIR/.env"
        
        echo "📁 Updated .env files with function URL"
        echo ""
        echo "✅ Environment setup complete!"
        echo ""
        echo "You can now run tests:"
        echo "  ./tests/run_tests.sh"
        echo "  ./tests/manual_test.sh basic"
        echo "  ./tests/advanced_tests.sh"
    else
        echo "❌ Could not retrieve function URL"
        echo "   This might be due to:"
        echo "   1. Missing PULUMI_CONFIG_PASSPHRASE"
        echo "   2. Stack needs redeployment: ./pumi up"
        echo ""
        echo "💡 To fix passphrase issue:"
        echo "   1. Edit .env file and uncomment PULUMI_CONFIG_PASSPHRASE"
        echo "   2. Set your actual passphrase"
        echo "   3. Run this script again"
    fi
else
    echo "❌ Pulumi stack 'dev' not found"
    echo "Deploy the stack first: ./pumi up"
fi