#!/bin/bash
set -euo pipefail

# Cache Debian base image in private ECR during CodeBuild
# This runs as part of the CodeBuild pre-build phase to cache the base image
# we're about to use anyway, avoiding duplicate pulls in subsequent builds

echo "=== CACHING DEBIAN BASE IMAGE ==="

# Get the current digest for debian:bookworm-slim
echo "Getting current Debian digest..."
DEBIAN_DIGEST=$(docker manifest inspect debian:bookworm-slim --verbose 2>/dev/null | \
    jq -r '.Descriptor.digest // .manifests[] | select(.platform.architecture=="amd64" and .platform.os=="linux") | .digest' | \
    head -1)

if [ -z "$DEBIAN_DIGEST" ] || [ "$DEBIAN_DIGEST" = "null" ]; then
    echo "Could not get digest from manifest, falling back to docker pull..."
    docker pull debian:bookworm-slim >/dev/null 2>&1
    DEBIAN_DIGEST=$(docker inspect debian:bookworm-slim --format='{{index .RepoDigests 0}}' | cut -d'@' -f2)
fi

if [ -z "$DEBIAN_DIGEST" ] || [ "$DEBIAN_DIGEST" = "null" ]; then
    echo "Warning: Could not determine Debian digest, skipping base image cache"
    exit 0
fi

SOURCE_IMAGE="debian:bookworm-slim@${DEBIAN_DIGEST}"
SHORT_DIGEST="${DEBIAN_DIGEST##*:}"
SHORT_DIGEST="${SHORT_DIGEST:0:12}"

# Use environment variables set by CodeBuild
BASE_IMAGE_TAG="knock-base:debian-bookworm-slim"
BASE_IMAGE_TAG_WITH_DIGEST="knock-base:debian-bookworm-${SHORT_DIGEST}"
FULL_BASE_IMAGE_URL="${ECR_REGISTRY_URL}/${BASE_IMAGE_TAG}"
FULL_BASE_IMAGE_URL_WITH_DIGEST="${ECR_REGISTRY_URL}/${BASE_IMAGE_TAG_WITH_DIGEST}"

echo "Debian digest: ${DEBIAN_DIGEST}"
echo "Target: ${FULL_BASE_IMAGE_URL}"
echo "Digest tag: ${FULL_BASE_IMAGE_URL_WITH_DIGEST}"

# Check if this specific digest already exists
DIGEST_TAG="debian-bookworm-${SHORT_DIGEST}"
if aws ecr describe-images --repository-name "knock-base" --image-ids imageTag="${DIGEST_TAG}" --region "$ECR_REGION" >/dev/null 2>&1; then
    echo "✅ Base image with digest ${SHORT_DIGEST} already cached. Skipping."
    exit 0
fi

# Create knock-base repository if needed
echo "Creating knock-base repository if needed..."
aws ecr create-repository --repository-name "knock-base" --region "$ECR_REGION" >/dev/null 2>&1 || true

# Pull the specific digest (CodeBuild will cache this pull for the main build)
echo "Pulling ${SOURCE_IMAGE}..."
docker pull "${SOURCE_IMAGE}"

# Tag for ECR
echo "Tagging for ECR..."
docker tag "${SOURCE_IMAGE}" "${FULL_BASE_IMAGE_URL}"
docker tag "${SOURCE_IMAGE}" "${FULL_BASE_IMAGE_URL_WITH_DIGEST}"

# Push to ECR
echo "Pushing to ECR..."
docker push "${FULL_BASE_IMAGE_URL}"
docker push "${FULL_BASE_IMAGE_URL_WITH_DIGEST}"

echo "✅ Base image cached successfully"
echo "Available at: ${FULL_BASE_IMAGE_URL}"