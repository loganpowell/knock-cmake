#!/bin/bash
set -euo pipefail

# Cache Debian base image in private ECR during CodeBuild
# This runs as part of the CodeBuild pre-build phase to cache the base image
# we're about to use anyway, avoiding duplicate pulls in subsequent builds

echo "=== CACHING DEBIAN BASE IMAGE ==="

# Get the current digest for debian:bookworm-slim
echo "Getting current Debian digest..."

# First try to get the digest directly from a pull
echo "Pulling debian:bookworm-slim to get digest..."
docker pull debian:bookworm-slim >/dev/null 2>&1 || true

# Get the digest from the local image
DEBIAN_DIGEST=$(docker inspect debian:bookworm-slim --format='{{range .RepoDigests}}{{.}}{{end}}' 2>/dev/null | head -1 | cut -d'@' -f2)

# If that fails, try manifest inspect with simpler parsing
if [ -z "$DEBIAN_DIGEST" ] || [ "$DEBIAN_DIGEST" = "null" ]; then
    echo "Trying docker manifest inspect..."
    # Try to get manifest and parse more robustly
    MANIFEST_OUTPUT=$(docker manifest inspect debian:bookworm-slim --verbose 2>/dev/null || echo "")
    if [ -n "$MANIFEST_OUTPUT" ]; then
        # Try different parsing approaches
        DEBIAN_DIGEST=$(echo "$MANIFEST_OUTPUT" | jq -r '.manifests[]? | select(.platform.architecture=="amd64" and .platform.os=="linux") | .digest' 2>/dev/null | head -1)
        if [ -z "$DEBIAN_DIGEST" ] || [ "$DEBIAN_DIGEST" = "null" ]; then
            DEBIAN_DIGEST=$(echo "$MANIFEST_OUTPUT" | jq -r '.Descriptor.digest // empty' 2>/dev/null)
        fi
    fi
fi

# Final fallback - use latest tag
if [ -z "$DEBIAN_DIGEST" ] || [ "$DEBIAN_DIGEST" = "null" ]; then
    echo "Could not determine specific digest, using latest tag"
    DEBIAN_DIGEST="latest"
fi

if [ -z "$DEBIAN_DIGEST" ] || [ "$DEBIAN_DIGEST" = "null" ] || [ "$DEBIAN_DIGEST" = "latest" ]; then
    echo "Warning: Could not determine specific Debian digest, skipping base image cache"
    echo "Will use debian:bookworm-slim directly during build"
    exit 0
fi

# Handle both actual digest and latest tag
if [ "$DEBIAN_DIGEST" = "latest" ]; then
    SOURCE_IMAGE="debian:bookworm-slim"
    SHORT_DIGEST="latest"
else
    SOURCE_IMAGE="debian:bookworm-slim@${DEBIAN_DIGEST}"
    SHORT_DIGEST="${DEBIAN_DIGEST##*:}"
    SHORT_DIGEST="${SHORT_DIGEST:0:12}"
fi

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