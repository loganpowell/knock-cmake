#!/bin/bash
# Build phase for CodeBuild
# Builds the Docker image for Lambda

set -e

echo "Build started on $(date)"
echo "Building the Lambda Docker image"

echo "Current directory contents"
ls -la

echo "Looking for Dockerfile"
find . -name "Dockerfile*" -type f

echo "Verifying Dockerfile exists"
if [ -f "infrastructure/lambda/Dockerfile" ]; then 
    cat infrastructure/lambda/Dockerfile | head -10
else 
    echo "ERROR - Dockerfile not found at infrastructure/lambda/Dockerfile"
    exit 1
fi

echo "Checking if build_container.py exists"
if [ -f "build_container.py" ]; then 
    echo "build_container.py found"
else 
    echo "ERROR - build_container.py not found"
    exit 1
fi

echo "Starting Docker build with target URI $ECR_REPOSITORY_URI:latest"
docker build -f infrastructure/lambda/Dockerfile -t $ECR_REPOSITORY_URI:latest . \
    --build-arg ECR_REGISTRY_URL=$ECR_REGISTRY_URL \
    --no-cache \
    --progress=plain

BUILD_EXIT_CODE=$?
echo "Docker build exit code was $BUILD_EXIT_CODE"

if [ $BUILD_EXIT_CODE -ne 0 ]; then 
    echo "ERROR - Docker build failed with exit code $BUILD_EXIT_CODE"
    exit $BUILD_EXIT_CODE
fi

echo "Listing all Docker images after build"
docker images

echo "Specifically checking for our image"
docker images | grep $ECR_REPOSITORY_URI || (echo "ERROR - Image not found after build" && exit 1)

echo "Checking image with explicit tag"
docker images $ECR_REPOSITORY_URI:latest || (echo "ERROR - Image with latest tag not found" && exit 1)

echo "Image built and tagged successfully"