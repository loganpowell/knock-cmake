"""Configuration settings for Knock Lambda Infrastructure"""

import os
import pulumi

# AWS Configuration - Read from environment variables
# Can be set via:
# 1. Pulumi ESC environment (recommended)
# 2. GitHub Actions (automatic)
# 3. Manual environment variables
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")

# Check for required Docker Hub credentials for ECR pull-through cache
docker_hub_username = os.environ.get("DOCKER_HUB_USERNAME")
docker_hub_token = os.environ.get("DOCKER_HUB_TOKEN")

if not docker_hub_username or not docker_hub_token:
    print(
        "⚠️  Docker Hub credentials not provided - pull-through cache will not be enabled"
    )
    print(
        "   Run 'uv run setup' to configure GitHub secrets including Docker Hub credentials"
    )
    print(
        "   Or use Pulumi ESC environment with DOCKER_HUB_USERNAME and DOCKER_HUB_TOKEN"
    )
else:
    print("✅ Docker Hub credentials found - pull-through cache will be enabled")

# Core settings
PROJECT_NAME = pulumi.get_project()
STACK_NAME = pulumi.get_stack()

# Lambda Configuration - Use environment variables with fallbacks
LAMBDA_TIMEOUT = int(os.environ.get("LAMBDA_TIMEOUT", "900"))  # 15 minutes
LAMBDA_MEMORY = int(os.environ.get("LAMBDA_MEMORY", "1024"))  # 1GB
LAMBDA_RETENTION_DAYS = int(os.environ.get("LAMBDA_LOG_RETENTION", "14"))

# S3 Configuration
OUTPUT_BUCKET_LIFECYCLE_DAYS = int(os.environ.get("OUTPUT_BUCKET_LIFECYCLE_DAYS", "1"))

# ECR Configuration
ECR_IMAGE_RETENTION_COUNT = int(os.environ.get("ECR_IMAGE_RETENTION", "5"))

# CodeBuild Configuration
CODEBUILD_COMPUTE_TYPE = os.environ.get(
    "CODEBUILD_COMPUTE_TYPE", "BUILD_GENERAL1_MEDIUM"
)
CODEBUILD_IMAGE = os.environ.get("CODEBUILD_IMAGE", "aws/codebuild/standard:7.0")

# Build and retry configuration
CODEBUILD_MAX_RETRIES = int(os.environ.get("CODEBUILD_MAX_RETRIES", "10"))
CODEBUILD_RETRY_DELAY = int(os.environ.get("CODEBUILD_RETRY_DELAY", "30"))  # seconds
CODEBUILD_TIMEOUT_MINUTES = int(
    os.environ.get("CODEBUILD_TIMEOUT_MINUTES", "30")
)  # minutes
