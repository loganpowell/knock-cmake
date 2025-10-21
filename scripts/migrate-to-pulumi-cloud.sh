#!/usr/bin/env bash
#
# migrate-to-pulumi-cloud.sh
#
# This script helps migrate your Pulumi stacks from local file backend to Pulumi Cloud.
# It will export your current stacks, login to Pulumi Cloud, and import them.
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INFRA_DIR="$SCRIPT_DIR/../infrastructure"

cd "$INFRA_DIR"

echo "🚀 Pulumi Cloud Migration Script"
echo "================================="
echo ""

# Check if already logged into Pulumi Cloud
if pulumi whoami | grep -q "pulumi.com"; then
    echo "✅ Already logged into Pulumi Cloud"
else
    echo "⚠️  Not logged into Pulumi Cloud"
    echo "Please visit https://app.pulumi.com to create a free account"
    echo ""
    read -p "Press Enter when you're ready to login to Pulumi Cloud..."
    
    pulumi login
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to login to Pulumi Cloud"
        exit 1
    fi
fi

echo ""
echo "Current backend: $(pulumi whoami -v | grep 'Backend URL')"
echo ""

# Export existing stacks
echo "📦 Exporting existing stacks..."
mkdir -p .migration-backup

for stack in dev main; do
    echo "  Exporting $stack stack..."
    if pulumi stack select $stack 2>/dev/null; then
        pulumi stack export --file ".migration-backup/${stack}-stack.json"
        echo "  ✅ $stack stack exported"
    else
        echo "  ⚠️  $stack stack not found, skipping"
    fi
done

echo ""
echo "🔄 Migrating stacks to Pulumi Cloud..."

# Now we're logged into Pulumi Cloud, reimport the stacks
for stack in dev main; do
    if [ -f ".migration-backup/${stack}-stack.json" ]; then
        echo "  Importing $stack stack..."
        
        # Try to create the stack (it might already exist)
        pulumi stack init $stack 2>/dev/null || pulumi stack select $stack
        
        # Import the state
        pulumi stack import --file ".migration-backup/${stack}-stack.json"
        
        echo "  ✅ $stack stack migrated"
    fi
done

echo ""
echo "✅ Migration complete!"
echo ""
echo "📋 Next steps:"
echo "1. Verify your stacks: pulumi stack ls"
echo "2. Test a deployment: pulumi preview"
echo "3. Add PULUMI_ACCESS_TOKEN to GitHub secrets"
echo "   - Go to: https://app.pulumi.com/account/tokens"
echo "   - Create a new token"
echo "   - Add it to: https://github.com/loganpowell/knock-lambda/settings/secrets/actions"
echo ""
echo "🗑️  After verifying everything works, you can delete the backup:"
echo "   rm -rf .migration-backup"
echo ""
