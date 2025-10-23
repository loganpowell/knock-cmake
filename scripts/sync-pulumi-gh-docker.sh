#!/bin/bash
# Setup Docker Hub credentials for ECR Pull-Through Cache
# This script:
# 1. Reads Docker Hub credentials from Pulumi config
# 2. Creates/updates AWS Secrets Manager secret (for ECR pull-through cache)
# 3. Syncs credentials to GitHub repository secrets (for GitHub Actions)

set -e

# Ensure Homebrew is in PATH (for VS Code terminal compatibility)
if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -f /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
fi

echo "🔐 Docker Hub Credentials Setup"
echo "=================================="
echo ""
echo "This script will:"
echo "  1️⃣  Read credentials from Pulumi config"
echo "  2️⃣  Create/update AWS Secrets Manager secret (for ECR)"
echo "  3️⃣  Sync credentials to GitHub Secrets (for CI/CD)"
echo ""

# Get credentials from Pulumi config
echo "📦 Reading Docker Hub credentials from Pulumi config..."
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

echo "✅ Credentials found in Pulumi config"
echo "   Username: $DOCKER_HUB_USERNAME"
echo ""

# ============================================
# Step 1: Setup AWS Secrets Manager Secret
# ============================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  AWS Secrets Manager Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "⚠️  AWS CLI not found - skipping AWS Secrets Manager setup"
    echo "   Install AWS CLI to enable ECR pull-through cache"
    echo ""
else
    SECRET_NAME="ecr-pullthroughcache/docker-hub"
    AWS_REGION="${AWS_REGION:-us-east-2}"
    
    # Create secret JSON
    SECRET_JSON=$(cat <<EOF
{
  "username": "$DOCKER_HUB_USERNAME",
  "accessToken": "$DOCKER_HUB_TOKEN"
}
EOF
)
    
    echo "🔍 Checking if AWS secret exists..."
    
    # Check if secret exists
    if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" &> /dev/null; then
        echo "⚠️  Secret '$SECRET_NAME' already exists"
        echo "🔄 Updating secret with current credentials..."
        
        aws secretsmanager update-secret \
            --secret-id "$SECRET_NAME" \
            --secret-string "$SECRET_JSON" \
            --region "$AWS_REGION" > /dev/null
        
        echo "✅ AWS secret updated successfully"
    else
        echo "📝 Creating new AWS secret..."
        
        SECRET_ARN=$(aws secretsmanager create-secret \
            --name "$SECRET_NAME" \
            --description "Docker Hub credentials for ECR pull-through cache" \
            --secret-string "$SECRET_JSON" \
            --region "$AWS_REGION" \
            --query 'ARN' \
            --output text)
        
        echo "✅ AWS secret created successfully"
        echo "   ARN: $SECRET_ARN"
        
        # Add resource policy to allow ECR to read the secret
        echo "🔒 Adding resource policy for ECR access..."
        
        aws secretsmanager put-resource-policy \
            --secret-id "$SECRET_NAME" \
            --resource-policy "{
                \"Version\": \"2012-10-17\",
                \"Statement\": [
                    {
                        \"Effect\": \"Allow\",
                        \"Principal\": {
                            \"Service\": \"ecr.amazonaws.com\"
                        },
                        \"Action\": \"secretsmanager:GetSecretValue\",
                        \"Resource\": \"$SECRET_ARN\"
                    }
                ]
            }" \
            --region "$AWS_REGION" > /dev/null
        
        echo "✅ Resource policy added"
    fi
    
    # Create pull-through cache rule
    echo ""
    echo "🔍 Checking if pull-through cache rule exists..."
    
    # Get the secret ARN (whether we just created it or it already existed)
    if [ -z "$SECRET_ARN" ]; then
        SECRET_ARN=$(aws secretsmanager describe-secret \
            --secret-id "$SECRET_NAME" \
            --region "$AWS_REGION" \
            --query 'ARN' \
            --output text)
    fi
    
    # Check if pull-through cache rule exists
    if aws ecr describe-pull-through-cache-rules \
        --region "$AWS_REGION" \
        --ecr-repository-prefixes docker-hub 2>/dev/null | grep -q "docker-hub"; then
        echo "✅ Pull-through cache rule 'docker-hub' already exists"
    else
        echo "📝 Creating pull-through cache rule..."
        
        aws ecr create-pull-through-cache-rule \
            --ecr-repository-prefix docker-hub \
            --upstream-registry-url registry-1.docker.io \
            --credential-arn "$SECRET_ARN" \
            --region "$AWS_REGION" > /dev/null
        
        echo "✅ Pull-through cache rule created successfully"
    fi
    echo ""
fi

# ============================================
# Step 2: Sync to GitHub Secrets
# ============================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  GitHub Secrets Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI (gh) not found - skipping GitHub Secrets sync"
    echo "   Install from: https://cli.github.com/ or run: brew install gh"
    echo ""
else
    # Check if user is logged in to gh
    if ! gh auth status &> /dev/null; then
        echo "⚠️  Not logged in to GitHub CLI - skipping GitHub Secrets sync"
        echo "   Run: gh auth login"
        echo ""
    else
        echo "📤 Syncing to GitHub repository secrets..."
        
        echo "   Setting DOCKER_HUB_USERNAME..."
        echo "$DOCKER_HUB_USERNAME" | gh secret set DOCKER_HUB_USERNAME
        
        echo "   Setting DOCKER_HUB_TOKEN..."
        echo "$DOCKER_HUB_TOKEN" | gh secret set DOCKER_HUB_TOKEN
        
        echo "✅ GitHub secrets updated successfully"
        echo ""
    fi
fi

# ============================================
# Summary
# ============================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Summary:"
echo "  ✅ Pulumi config: Credentials stored locally"

if command -v aws &> /dev/null; then
    echo "  ✅ AWS Secrets Manager: ECR pull-through cache configured"
else
    echo "  ⚠️  AWS Secrets Manager: Skipped (AWS CLI not found)"
fi

if command -v gh &> /dev/null && gh auth status &> /dev/null 2>&1; then
    echo "  ✅ GitHub Secrets: CI/CD workflows configured"
else
    echo "  ⚠️  GitHub Secrets: Skipped (gh CLI not found or not authenticated)"
fi

echo ""
echo "Next steps:"
echo "  • Run 'pulumi up' to deploy with pull-through cache enabled"
echo "  • Or push to GitHub to trigger CI/CD deployment"
echo ""
echo "Verify setup:"
echo "  • GitHub secrets: gh secret list"
echo "  • AWS secret: aws secretsmanager describe-secret --secret-id ecr-pullthroughcache/docker-hub --region us-east-2"
echo ""

