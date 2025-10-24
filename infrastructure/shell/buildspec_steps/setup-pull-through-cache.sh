#!/bin/bash
# Setup pull-through cache repository
# This script ensures the Docker Hub pull-through cache repository exists

set -e  # Exit on any error

echo "Ensuring pull-through cache repository exists"

# Try to describe the repository to see if it exists
if aws ecr describe-repositories --repository-names docker-hub/library/debian --region $ECR_REGION 2>/dev/null; then
  echo "✅ Pull-through cache repository already exists"
else
  echo "📦 Repository doesn't exist yet - creating via pull-through cache"
  # The first pull should trigger automatic repository creation via pull-through cache
  # We need to pull with error handling
  if docker pull $ECR_REGISTRY_URL/docker-hub/library/debian:bookworm-slim 2>&1; then
    echo "✅ Successfully pulled and created repository via pull-through cache"
  else
    echo "⚠️ Initial pull failed - this is normal for first-time cache setup"
    echo "Waiting 5 seconds for AWS to propagate..."
    sleep 5
    # Try once more
    if docker pull $ECR_REGISTRY_URL/docker-hub/library/debian:bookworm-slim 2>&1; then
      echo "✅ Successfully pulled on retry"
    else
      echo "⚠️ Pull-through cache not working - build will fail"
      echo "This may indicate an issue with Docker Hub credentials in Secrets Manager"
    fi
  fi
fi