#!/bin/bash
# Pre-build phase for CodeBuild
# Sets up environment, ECR login, and pull-through cache

set -e

echo "Starting pre-build phase"
echo "ECR Repository URI is $ECR_REPOSITORY_URI"
echo "AWS Region is $AWS_DEFAULT_REGION"

echo "Checking network connectivity"
ping -c 3 google.com || echo "No internet connectivity"

echo "Listing directory contents"
ls -la

echo "Available memory and disk space"
free -h && df -h

echo "Checking AWS credentials"
aws sts get-caller-identity

echo "Extracting ECR region and account from URI"
export ECR_REGION=$(echo $ECR_REPOSITORY_URI | cut -d. -f4)
export ECR_ACCOUNT_ID=$(echo $ECR_REPOSITORY_URI | cut -d. -f1 | cut -d/ -f3)
export ECR_REGISTRY_URL="$ECR_ACCOUNT_ID.dkr.ecr.$ECR_REGION.amazonaws.com"
echo "ECR Region is $ECR_REGION, Account ID is $ECR_ACCOUNT_ID"
echo "ECR Registry URL is $ECR_REGISTRY_URL"

echo "Verifying pull-through cache rules are available"
aws ecr describe-pull-through-cache-rules --region $ECR_REGION || echo "Warning - Could not verify pull-through cache rules"

echo "Getting ECR login using ECR region"
aws ecr get-login-password --region $ECR_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY_URL
echo "Successfully logged in to ECR"

# Temporarily disable base image caching to debug build issues
echo "⚠️ Base image caching temporarily disabled for debugging"
# chmod +x infrastructure/shell/buildspec_steps/cache-base-image.sh || true
# ./infrastructure/shell/buildspec_steps/cache-base-image.sh || echo "⚠️ Base image caching skipped, but continuing build..."

echo "Pre-build phase complete"