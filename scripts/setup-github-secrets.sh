#!/usr/bin/env bash
#
# setup-github-secrets.sh
#
# This script helps you set up GitHub secrets for Pulumi CI/CD.
# It generates the commands you need to run to add secrets via GitHub CLI.
#

set -e

REPO="loganpowell/knock-lambda"

echo "🔐 GitHub Secrets Setup for Pulumi CI/CD"
echo "=========================================="
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI (gh) is not installed."
    echo ""
    echo "📋 Manual Setup Instructions:"
    echo "----------------------------"
    echo "Go to: https://github.com/$REPO/settings/secrets/actions"
    echo ""
    echo "Add these 3 secrets:"
    echo ""
    echo "1. PULUMI_ACCESS_TOKEN"
    echo "   Value: [Your Pulumi Access Token]"
    echo ""
    echo "2. AWS_ACCESS_KEY_ID"
    echo "   Value: [Your AWS Access Key ID]"
    echo ""
    echo "3. AWS_SECRET_ACCESS_KEY"
    echo "   Value: [Your AWS Secret Access Key]"
    echo ""
    exit 0
fi

# GitHub CLI is installed, offer to set secrets automatically
echo "✅ GitHub CLI detected!"
echo ""

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "⚠️  Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

echo "Current secrets:"
gh secret list -R "$REPO" 2>/dev/null || echo "(No secrets set yet)"
echo ""

# Check if .env file exists
if [ -f "../.env" ]; then
    echo "📁 Found .env file with PULUMI_ACCESS_TOKEN"
    source ../.env
fi

# Set PULUMI_ACCESS_TOKEN
if [ -n "$PULUMI_ACCESS_TOKEN" ]; then
    echo "Setting PULUMI_ACCESS_TOKEN..."
    echo "$PULUMI_ACCESS_TOKEN" | gh secret set PULUMI_ACCESS_TOKEN -R "$REPO"
    echo "✅ PULUMI_ACCESS_TOKEN set"
else
    echo "⚠️  PULUMI_ACCESS_TOKEN not found in .env"
    echo "Set it manually: gh secret set PULUMI_ACCESS_TOKEN -R $REPO"
fi

echo ""
echo "⚠️  AWS Credentials needed:"
echo "----------------------------"
echo "You need to set these manually with your AWS credentials:"
echo ""
echo "# Option 1: Interactive"
echo "gh secret set AWS_ACCESS_KEY_ID -R $REPO"
echo "gh secret set AWS_SECRET_ACCESS_KEY -R $REPO"
echo ""
echo "# Option 2: From command"
echo "echo 'YOUR_ACCESS_KEY' | gh secret set AWS_ACCESS_KEY_ID -R $REPO"
echo "echo 'YOUR_SECRET_KEY' | gh secret set AWS_SECRET_ACCESS_KEY -R $REPO"
echo ""
echo "🔒 Security Best Practice:"
echo "Create a dedicated IAM user for GitHub Actions with minimal permissions."
echo ""

# Prompt for AWS credentials
read -p "Do you want to set AWS credentials now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Enter AWS_ACCESS_KEY_ID:"
    gh secret set AWS_ACCESS_KEY_ID -R "$REPO"
    
    echo "Enter AWS_SECRET_ACCESS_KEY:"
    gh secret set AWS_SECRET_ACCESS_KEY -R "$REPO"
    
    echo "✅ AWS credentials set"
fi

echo ""
echo "📋 Current secrets:"
gh secret list -R "$REPO"
echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Next steps:"
echo "1. Commit and push your workflow file"
echo "2. Create a test PR to verify 'pulumi preview' works"
echo "3. Merge to main/dev to test 'pulumi up' deployment"
