#!/bin/bash
# Sync Docker Hub credentials from Pulumi config to GitHub repository secrets

set -e

# Ensure Homebrew is in PATH (for VS Code terminal compatibility)
if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -f /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
fi

echo "=== Sync Pulumi Config to GitHub Secrets ==="
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed"
    echo "   Install it from: https://cli.github.com/"
    echo "   Or run: brew install gh"
    exit 1
fi

# Check if user is logged in to gh
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not logged in to GitHub CLI"
    echo "   Run: gh auth login"
    exit 1
fi

# Get credentials from Pulumi config
echo "Reading Docker Hub credentials from Pulumi config..."
DOCKER_HUB_USERNAME=$(pulumi config get dockerHubUsername 2>/dev/null || echo "")
DOCKER_HUB_TOKEN=$(pulumi config get dockerHubToken 2>/dev/null || echo "")

if [ -z "$DOCKER_HUB_USERNAME" ] || [ -z "$DOCKER_HUB_TOKEN" ]; then
    echo ""
    echo "❌ Error: Docker Hub credentials not found in Pulumi config"
    echo ""
    echo "Please set them first:"
    echo "  pulumi config set dockerHubUsername your_username"
    echo "  pulumi config set --secret dockerHubToken your_token"
    echo ""
    exit 1
fi

# Sync to GitHub secrets
echo "Syncing to GitHub repository secrets..."
echo ""

echo "Setting DOCKER_HUB_USERNAME..."
echo "$DOCKER_HUB_USERNAME" | gh secret set DOCKER_HUB_USERNAME
echo "✅ DOCKER_HUB_USERNAME set"

echo "Setting DOCKER_HUB_TOKEN..."
echo "$DOCKER_HUB_TOKEN" | gh secret set DOCKER_HUB_TOKEN
echo "✅ DOCKER_HUB_TOKEN set"

echo ""
echo "=== Sync Complete ==="
echo ""
echo "✅ GitHub secrets have been updated from Pulumi config"
echo "✅ Your GitHub Actions workflows will use these credentials"
echo ""
echo "Verify GitHub secrets:"
echo "  gh secret list"
echo ""

