#!/usr/bin/env bash
set -euo pipefail

# Import existing ECR pull-through cache rule into Pulumi state
# This is needed when the rule exists in AWS but not in Pulumi's state

echo "🔍 Importing ECR pull-through cache rule into Pulumi state"
echo "=========================================================="
echo ""

STACK_NAME="${1:-dev}"
REGION="${2:-us-east-2}"

echo "Stack: $STACK_NAME"
echo "Region: $REGION"
echo ""

# Check if the pull-through cache rule exists
echo "Checking if pull-through cache rule exists in AWS..."
if aws ecr describe-pull-through-cache-rules \
    --region "$REGION" \
    --ecr-repository-prefixes docker-hub 2>/dev/null | grep -q "docker-hub"; then
    
    echo "✅ Pull-through cache rule 'docker-hub' exists in AWS"
    echo ""
    echo "Importing into Pulumi stack '$STACK_NAME'..."
    
    # Import the resource into Pulumi state
    # Format: pulumi import <TYPE> <NAME> <ID>
    # For PullThroughCacheRule, the ID is the repository prefix
    pulumi import aws:ecr/pullThroughCacheRule:PullThroughCacheRule docker-hub-cache docker-hub --stack "$STACK_NAME"
    
    echo ""
    echo "✅ Successfully imported pull-through cache rule"
else
    echo "⚠️  Pull-through cache rule 'docker-hub' does not exist in AWS"
    echo "   It will be created on next 'pulumi up'"
fi

echo ""
echo "Done!"
