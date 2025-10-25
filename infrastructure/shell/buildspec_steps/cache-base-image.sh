#!/bin/bash
set -e

# Simplified cache script that doesn't rely on complex digest parsing
# This focuses on just caching the debian:bookworm-slim image to ECR

echo "=== CACHING DEBIAN BASE IMAGE (SIMPLIFIED) ==="

# Use simple approach - cache the latest debian:bookworm-slim
SOURCE_IMAGE="debian:bookworm-slim"
TARGET_TAG="knock-base:debian-bookworm-slim"
FULL_TARGET_URL="${ECR_REGISTRY_URL}/${TARGET_TAG}"

echo "Source: ${SOURCE_IMAGE}"
echo "Target: ${FULL_TARGET_URL}"

# Check if image already exists in ECR
echo "Checking if base image already exists in ECR..."
if aws ecr describe-images --repository-name "knock-base" --image-ids imageTag="debian-bookworm-slim" --region "$ECR_REGION" >/dev/null 2>&1; then
    echo "✅ Base image already cached. Skipping."
    exit 0
fi

# Create repository if needed
echo "Creating knock-base repository if needed..."
aws ecr create-repository --repository-name "knock-base" --region "$ECR_REGION" >/dev/null 2>&1 || echo "Repository might already exist"

# Pull base image
echo "Pulling ${SOURCE_IMAGE}..."
if ! docker pull "${SOURCE_IMAGE}"; then
    echo "⚠️ Failed to pull base image, but continuing build..."
    exit 0  # Don't fail the build if caching fails
fi

# Tag for ECR
echo "Tagging for ECR..."
if ! docker tag "${SOURCE_IMAGE}" "${FULL_TARGET_URL}"; then
    echo "⚠️ Failed to tag image, but continuing build..."
    exit 0
fi

# Push to ECR
echo "Pushing to ECR..."
if ! docker push "${FULL_TARGET_URL}"; then
    echo "⚠️ Failed to push to ECR, but continuing build..."
    exit 0
fi

echo "✅ Base image cached successfully at: ${FULL_TARGET_URL}"