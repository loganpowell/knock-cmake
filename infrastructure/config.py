"""Configuration settings for Knock Lambda Infrastructure"""

import pulumi

__all__ = [
    "PROJECT_NAME",
    "STACK_NAME",
    "AWS_REGION",
    "LAMBDA_TIMEOUT",
    "LAMBDA_MEMORY",
    "LAMBDA_RETENTION_DAYS",
    "OUTPUT_BUCKET_LIFECYCLE_DAYS",
    "ECR_IMAGE_RETENTION_COUNT",
    "CODEBUILD_COMPUTE_TYPE",
    "CODEBUILD_IMAGE",
    "CODEBUILD_MAX_RETRIES",
    "CODEBUILD_RETRY_DELAY",
    "CODEBUILD_TIMEOUT_MINUTES",
]

# Get configuration
config = pulumi.Config()
aws_config = pulumi.Config("aws")

# Core settings
PROJECT_NAME = pulumi.get_project()
STACK_NAME = pulumi.get_stack()

# AWS Configuration
AWS_REGION = aws_config.get("region") or config.get("aws_region") or "us-east-2"

# Lambda Configuration
LAMBDA_TIMEOUT = config.get_int("lambda_timeout") or 900  # 15 minutes
LAMBDA_MEMORY = config.get_int("lambda_memory") or 3008  # Maximum memory
LAMBDA_RETENTION_DAYS = config.get_int("lambda_log_retention") or 14

# S3 Configuration
OUTPUT_BUCKET_LIFECYCLE_DAYS = config.get_int("output_bucket_lifecycle_days") or 1

# ECR Configuration
ECR_IMAGE_RETENTION_COUNT = config.get_int("ecr_image_retention") or 5

# CodeBuild Configuration
CODEBUILD_COMPUTE_TYPE = config.get("codebuild_compute_type") or "BUILD_GENERAL1_MEDIUM"
CODEBUILD_IMAGE = config.get("codebuild_image") or "aws/codebuild/standard:7.0"

# Build and retry configuration
CODEBUILD_MAX_RETRIES = config.get_int("codebuild_max_retries") or 10
CODEBUILD_RETRY_DELAY = config.get_int("codebuild_retry_delay") or 30  # seconds
CODEBUILD_TIMEOUT_MINUTES = config.get_int("codebuild_timeout_minutes") or 30  # minutes
