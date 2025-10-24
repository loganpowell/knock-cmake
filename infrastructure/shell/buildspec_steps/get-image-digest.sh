#!/bin/bash
# Get ECR image digest and save to file
# This script retrieves the image digest from ECR and saves the full URI with digest

set -e  # Exit on any error (except where we handle errors explicitly)

echo "Attempting to get image digest from ECR..."

# Use a subshell to handle errors without exiting main script
(
  IMAGE_DIGEST=$(aws ecr describe-images --repository-name $REPO_NAME --region $AWS_DEFAULT_REGION --image-ids imageTag=latest --query "imageDetails[0].imageDigest" --output text 2>&1)
  DESCRIBE_EXIT_CODE=$?
  echo "ECR describe-images exit code: $DESCRIBE_EXIT_CODE"
  
  if [ $DESCRIBE_EXIT_CODE -eq 0 ] && [ "$IMAGE_DIGEST" != "None" ] && [ -n "$IMAGE_DIGEST" ]; then
    echo "✅ Successfully retrieved image digest: $IMAGE_DIGEST"
    IMAGE_URI_WITH_DIGEST="$ECR_REPOSITORY_URI@$IMAGE_DIGEST"
    echo "Full image URI with digest: $IMAGE_URI_WITH_DIGEST"
    echo "$IMAGE_URI_WITH_DIGEST" > /tmp/image_uri_digest.txt
    echo "✅ Image URI with digest saved successfully"
  else
    echo "⚠️ Failed to get image digest (exit code: $DESCRIBE_EXIT_CODE)"
    echo "Error output: $IMAGE_DIGEST"
    echo "🔄 Falling back to latest tag..."
    FALLBACK_URI="$ECR_REPOSITORY_URI:latest"
    echo "Fallback image URI: $FALLBACK_URI"
    echo "$FALLBACK_URI" > /tmp/image_uri_digest.txt
    echo "⚠️ Using fallback URI - Lambda may not update automatically on next build"
  fi
  echo "Image URI written to /tmp/image_uri_digest.txt"
) || true