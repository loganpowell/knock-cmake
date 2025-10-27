"""Configuration settings for Knock Lambda Infrastructure"""

import os
import pulumi

# Initialize Pulumi config
config = pulumi.Config()
aws_config = pulumi.Config("aws")  # For aws:region

# Core settings
PROJECT_NAME = pulumi.get_project()
STACK_NAME = pulumi.get_stack()

# AWS Configuration - Read from Pulumi config (exposed via ESC pulumiConfig)
# In ESC environment, this is set as:
#   pulumiConfig:
#     aws:region: ${AWS_REGION}
AWS_REGION = aws_config.require("region")

# Docker Hub credentials - Read from Pulumi config (exposed via ESC)
# In ESC environment, these are set as:
#   pulumiConfig:
#     knock-lambda:DOCKER_HUB_USERNAME: ${DOCKER_HUB_USERNAME}
#     knock-lambda:DOCKER_HUB_TOKEN: ${DOCKER_HUB_TOKEN}  (fn::secret)
DOCKER_HUB_USERNAME = config.require("DOCKER_HUB_USERNAME")
pulumi.log.info(f"✅ Docker Hub username: {DOCKER_HUB_USERNAME}")

DOCKER_HUB_TOKEN = config.require_secret("DOCKER_HUB_TOKEN")
pulumi.log.info("✅ Docker Hub token found (secret)")


# Check if credentials are provided (handle Output types)
def check_docker_credentials(username, token):
    """Check if Docker Hub credentials are available."""
    has_username = username is not None
    has_token = token is not None

    if not has_username or not has_token:
        pulumi.log.warn(
            "⚠️  Docker Hub credentials not provided - pull-through cache will not be enabled"
        )
        pulumi.log.warn("   Set with: `uv run setup`")
    else:
        pulumi.log.info(
            "✅ Docker Hub credentials found - pull-through cache will be enabled"
        )

    return has_username and has_token


# Check credentials availability
docker_hub_available = check_docker_credentials(DOCKER_HUB_USERNAME, DOCKER_HUB_TOKEN)

# Lambda Configuration - Use environment variables with fallbacks
LAMBDA_TIMEOUT = int(os.environ.get("LAMBDA_TIMEOUT", "300"))  # 5 minutes
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
