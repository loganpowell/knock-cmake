"""
Base Infrastructure Stack for Knock Lambda

This stack contains shared resources used across all environment stacks (dev, main, etc.):
- OIDC providers for GitHub Actions and Pulumi ESC authentication
- Shared Docker Hub credentials in AWS Secrets Manager
- Public ECR pull-through cache configuration

These resources are protected from deletion and provide stable ARNs/names
that can be referenced by environment-specific stacks.
"""

import os
import json
import pulumi
import pulumi_aws as aws

# Get repository information (same logic as main stack)
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "loganpowell/knock-lambda")
GITHUB_ORG, GITHUB_REPO = GITHUB_REPOSITORY.split("/", 1)

# Configuration
PROJECT_NAME = "knock-lambda"
AWS_REGION = "us-east-2"

pulumi.log.info(f"🏗️  Base Stack - Shared Infrastructure")
pulumi.log.info(f"🏢 GitHub Organization: {GITHUB_ORG}")
pulumi.log.info(f"📦 Repository: {GITHUB_REPO}")

# Get current AWS account ID
current_identity = aws.get_caller_identity()
account_id = current_identity.account_id

# =============================================================================
# OIDC PROVIDERS (Shared across all stacks)
# =============================================================================

# GitHub OIDC Provider for GitHub Actions
# Protected resource - will not be deleted to prevent breaking authentication
github_oidc_provider = aws.iam.OpenIdConnectProvider(
    "github-oidc-provider",
    url="https://token.actions.githubusercontent.com",
    client_id_lists=["sts.amazonaws.com"],
    opts=pulumi.ResourceOptions(
        protect=True,
        delete_before_replace=False,
    ),
)

# Pulumi Cloud OIDC Provider for Pulumi ESC
# Protected resource - will not be deleted to prevent breaking ESC authentication
pulumi_oidc_provider = aws.iam.OpenIdConnectProvider(
    "pulumi-oidc-provider",
    url="https://api.pulumi.com/oidc",
    client_id_lists=["pulumi"],
    opts=pulumi.ResourceOptions(
        protect=True,
        delete_before_replace=False,
    ),
)

# =============================================================================
# SHARED SECRETS
# =============================================================================

# Get Docker Hub credentials from environment
docker_hub_username = os.environ.get("DOCKER_HUB_USERNAME")
docker_hub_token = os.environ.get("DOCKER_HUB_TOKEN")

# Shared Docker Hub credentials secret
# Used by all environment stacks for ECR pull-through cache
docker_hub_secret = aws.secretsmanager.Secret(
    "docker-hub-credentials",
    name=f"{PROJECT_NAME}-docker-hub-credentials",
    description="Docker Hub credentials for ECR pull-through cache (shared across all stacks)",
    opts=pulumi.ResourceOptions(
        protect=True,  # Protect from accidental deletion
    ),
)

# Only set the secret value if credentials are provided
if docker_hub_username and docker_hub_token:
    docker_hub_secret_version = aws.secretsmanager.SecretVersion(
        "docker-hub-credentials-version",
        secret_id=docker_hub_secret.id,
        secret_string=pulumi.Output.secret(
            json.dumps(
                {
                    "username": docker_hub_username,
                    "token": docker_hub_token,
                }
            )
        ),
        opts=pulumi.ResourceOptions(depends_on=[docker_hub_secret]),
    )
    pulumi.log.info("✅ Docker Hub credentials configured")
else:
    pulumi.log.warn(
        "⚠️  Docker Hub credentials not provided - secret created but not populated"
    )
    pulumi.log.warn(
        '   Set via: aws secretsmanager put-secret-value --secret-id knock-lambda-docker-hub-credentials --secret-string \'{"username":"...","token":"..."}\''
    )

# =============================================================================
# SHARED ECR CONFIGURATION
# =============================================================================

# Public ECR pull-through cache rule (shared across all stacks)
public_ecr_cache_rule = aws.ecr.PullThroughCacheRule(
    "public-ecr-cache",
    ecr_repository_prefix="ecr-public",
    upstream_registry_url="public.ecr.aws",
)

# =============================================================================
# EXPORTS
# =============================================================================

# Export OIDC provider ARNs for use in environment stacks
pulumi.export("github_oidc_provider_arn", github_oidc_provider.arn)
pulumi.export("github_oidc_provider_url", github_oidc_provider.url)
pulumi.export("pulumi_oidc_provider_arn", pulumi_oidc_provider.arn)
pulumi.export("pulumi_oidc_provider_url", pulumi_oidc_provider.url)

# Export shared secret information
pulumi.export("docker_hub_secret_name", docker_hub_secret.name)
pulumi.export("docker_hub_secret_arn", docker_hub_secret.arn)

# Export ECR cache configuration
pulumi.export("public_ecr_cache_prefix", public_ecr_cache_rule.ecr_repository_prefix)

# Export account ID for reference
pulumi.export("aws_account_id", account_id)

# Export repository information
pulumi.export("github_repository", GITHUB_REPOSITORY)
pulumi.export("github_org", GITHUB_ORG)
pulumi.export("github_repo", GITHUB_REPO)
