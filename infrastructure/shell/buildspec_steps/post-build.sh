#!/bin/bash
# Post-build phase for CodeBuild
# Pushes image to ECR and gets digest

set -e

echo "Build completed on $(date)"

echo "Verifying image exists before push"
docker images $ECR_REPOSITORY_URI:latest

echo "Pushing the Docker image"
docker push $ECR_REPOSITORY_URI:latest
echo "Image pushed successfully"

echo "Getting image digest after push"
echo "Waiting 10 seconds for ECR to update image metadata..."
sleep 10

export REPO_NAME=$(echo $ECR_REPOSITORY_URI | cut -d'/' -f2)
echo "Repository name:" $REPO_NAME

chmod +x infrastructure/shell/buildspec_steps/get-image-digest.sh
./infrastructure/shell/buildspec_steps/get-image-digest.sh

echo "POST_BUILD phase completed successfully with fallback handling"
echo "Image URI with digest saved to /tmp/image_uri_digest.txt"