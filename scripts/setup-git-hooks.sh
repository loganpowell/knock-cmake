#!/usr/bin/env bash
# Setup Git hooks for this repository

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_SOURCE="$REPO_ROOT/scripts/git-hooks"
HOOKS_TARGET="$REPO_ROOT/.git/hooks"

echo "📦 Installing Git hooks..."
echo ""

# Install post-checkout hook
if [ -f "$HOOKS_SOURCE/post-checkout" ]; then
    cp "$HOOKS_SOURCE/post-checkout" "$HOOKS_TARGET/post-checkout"
    chmod +x "$HOOKS_TARGET/post-checkout"
    echo "✅ Installed post-checkout hook (auto-switches Pulumi stack to match branch)"
else
    echo "⚠️  post-checkout hook template not found"
fi

echo ""
echo "🎉 Git hooks installed successfully!"
echo ""
echo "Features enabled:"
echo "  • Auto-switch Pulumi stack when changing branches"
echo ""
