"""
Knock Lambda Infrastructure with Pulumi

This module provisions AWS infrastructure for the Knock ACSM conversion Lambda service, including:
- ECR repository for container images
- CodeBuild project to build Docker images using infrastructure/lambda/Dockerfile
- Lambda function using the container image with infrastructure/lambda/handler.py
- S3 buckets for temporary file storage
- IAM roles and policies for proper access control
"""

# Read the image digest from the build output
# Use a cross-platform approach to find the temp file
import tempfile
import os
import json
import pulumi
import pulumi_aws as aws
import pulumi_command as command
from infrastructure.utils import (
    get_shell_command,
    get_validated_buildspec,
    get_github_repository,
)

from infrastructure.vars import (
    PROJECT_NAME,
    STACK_NAME,
    AWS_REGION,
    LAMBDA_TIMEOUT,
    LAMBDA_MEMORY,
    LAMBDA_RETENTION_DAYS,
    OUTPUT_BUCKET_LIFECYCLE_DAYS,
    ECR_IMAGE_RETENTION_COUNT,
    CODEBUILD_COMPUTE_TYPE,
    CODEBUILD_IMAGE,
    CODEBUILD_MAX_RETRIES,
    CODEBUILD_RETRY_DELAY,
    CODEBUILD_TIMEOUT_MINUTES,
)

# Infrastructure reads from environment variables (set by GitHub Actions or loaded via gh CLI)
# No local .env files are used for security reasons - all secrets come from GitHub

# Get repository information dynamically using shared utility
GITHUB_REPOSITORY, GITHUB_ORG, GITHUB_REPO = get_github_repository()

pulumi.log.info(f"🏢 GitHub Organization: {GITHUB_ORG}")
pulumi.log.info(f"📦 Repository: {GITHUB_REPO}")
pulumi.log.info(f"🔗 Full Repository: {GITHUB_REPOSITORY}")

# Log configuration for debugging
pulumi.log.info(f"🌍 Deployment Region: {AWS_REGION}")
pulumi.log.info(f"🏗️  Project: {PROJECT_NAME}, Stack: {STACK_NAME}")


# Detect the shell to use at module load time
SHELL_CMD = get_shell_command()


# Configuration imported from config.py
# aws_region, project_name, stack_name, etc. are now available

# Get Docker Hub credentials from environment variables
# These are automatically loaded from GitHub secrets via config.py
# Initialize variables for conditional resources

# =============================================================================
# REFERENCE BASE STACK (Shared Infrastructure)
# =============================================================================

# Reference the base stack to get shared resources (OIDC providers, secrets, etc.)
# Stack name format: organization/project-name/stack-name
base_stack = pulumi.StackReference(f"{GITHUB_ORG}/{PROJECT_NAME}/base")

# Get shared OIDC provider ARNs from base stack
github_oidc_provider_arn = base_stack.get_output("github_oidc_provider_arn")
pulumi_oidc_provider_arn = base_stack.get_output("pulumi_oidc_provider_arn")

# Get shared Docker Hub secret information
docker_hub_secret_name = base_stack.get_output("docker_hub_secret_name")
docker_hub_secret_arn = base_stack.get_output("docker_hub_secret_arn")

# Get current AWS account ID for OIDC configuration
current_identity = aws.get_caller_identity()
account_id = current_identity.account_id

# =============================================================================
# OIDC ROLES (Stack-Specific)
# =============================================================================

# IAM Role for GitHub Actions OIDC authentication
github_actions_role = aws.iam.Role(
    "github-actions-role",
    name=f"{PROJECT_NAME}-github-actions-{STACK_NAME}",
    assume_role_policy=pulumi.Output.all(github_oidc_provider_arn, account_id).apply(
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Federated": args[0]},  # GitHub OIDC provider ARN
                        "Action": "sts:AssumeRoleWithWebIdentity",
                        "Condition": {
                            "StringEquals": {
                                "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                            },
                            "StringLike": {
                                # Allow access from main and dev branches
                                "token.actions.githubusercontent.com:sub": [
                                    f"repo:{GITHUB_REPOSITORY}:ref:refs/heads/main",
                                    f"repo:{GITHUB_REPOSITORY}:ref:refs/heads/dev",
                                    # Allow releases targeting main or dev branches
                                    f"repo:{GITHUB_REPOSITORY}:ref:refs/tags/*",
                                ]
                            },
                        },
                    }
                ],
            }
        )
    ),
)

# IAM Role for Pulumi ESC OIDC authentication
pulumi_esc_role = aws.iam.Role(
    "pulumi-esc-role",
    name=f"{PROJECT_NAME}-pulumi-esc",
    assume_role_policy=pulumi.Output.all(pulumi_oidc_provider_arn, account_id).apply(
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Federated": args[0]},  # Pulumi OIDC provider ARN
                        "Action": "sts:AssumeRoleWithWebIdentity",
                        "Condition": {
                            "StringEquals": {
                                "api.pulumi.com/oidc:aud": GITHUB_ORG,
                                # Allow access from your Pulumi organization and this environment
                                "api.pulumi.com/oidc:sub": f"pulumi:environments:org:{GITHUB_ORG}:env:{GITHUB_REPO}-esc",
                            }
                        },
                    }
                ],
            }
        )
    ),
)

# Comprehensive IAM policy for infrastructure management
infrastructure_policy = aws.iam.Policy(
    "infrastructure-policy",
    name=f"{PROJECT_NAME}-infrastructure-{STACK_NAME}",
    description="Policy for GitHub Actions and Pulumi ESC to manage knock-lambda infrastructure",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        # ECR permissions
                        "ecr:*",
                        # CodeBuild permissions
                        "codebuild:*",
                        # Lambda permissions
                        "lambda:*",
                        # S3 permissions
                        "s3:*",
                        # IAM permissions (limited)
                        "iam:GetRole",
                        "iam:GetRolePolicy",
                        "iam:PassRole",
                        "iam:CreateRole",
                        "iam:DeleteRole",
                        "iam:UpdateRole",
                        "iam:AttachRolePolicy",
                        "iam:DetachRolePolicy",
                        "iam:PutRolePolicy",
                        "iam:DeleteRolePolicy",
                        "iam:ListRolePolicies",
                        "iam:ListAttachedRolePolicies",
                        # OIDC Provider permissions
                        "iam:CreateOpenIDConnectProvider",
                        "iam:UpdateOpenIDConnectProviderThumbprint",
                        "iam:DeleteOpenIDConnectProvider",
                        "iam:GetOpenIDConnectProvider",
                        "iam:ListOpenIDConnectProviders",
                        # Secrets Manager permissions
                        "secretsmanager:*",
                        # CloudWatch Logs permissions
                        "logs:*",
                        # CloudFormation (used by Pulumi)
                        "cloudformation:*",
                        # STS (for role assumption)
                        "sts:GetCallerIdentity",
                        "sts:AssumeRole",
                    ],
                    "Resource": "*",
                }
            ],
        }
    ),
)

# Attach policy to both roles
github_actions_policy_attachment = aws.iam.RolePolicyAttachment(
    "github-actions-policy-attachment",
    role=github_actions_role.name,
    policy_arn=infrastructure_policy.arn,
)

pulumi_esc_policy_attachment = aws.iam.RolePolicyAttachment(
    "pulumi-esc-policy-attachment",
    role=pulumi_esc_role.name,
    policy_arn=infrastructure_policy.arn,
)

# =============================================================================
# MAIN INFRASTRUCTURE RESOURCES
# =============================================================================

# Create ECR repository for container images
ecr_repo = aws.ecr.Repository(
    "knock-repo",
    name=f"{PROJECT_NAME}-{STACK_NAME}".lower().replace(
        "_", "-"
    ),  # Ensure valid ECR repo name
    image_tag_mutability="MUTABLE",
    image_scanning_configuration={"scan_on_push": True},
    force_delete=True,  # Allow repository deletion even with images
)

# Note: Public ECR cache rule is now managed in the base stack

# Create ECR lifecycle policy to manage image retention
ecr_lifecycle_policy = aws.ecr.LifecyclePolicy(
    "knock-repo-lifecycle",
    repository=ecr_repo.name,
    policy=json.dumps(
        {
            "rules": [
                {
                    "rulePriority": 1,
                    "description": "Keep last 5 images",
                    "selection": {
                        "tagStatus": "any",
                        "countType": "imageCountMoreThan",
                        "countNumber": ECR_IMAGE_RETENTION_COUNT,
                    },
                    "action": {"type": "expire"},
                }
            ]
        },
        indent=4,
    ),
)

# Note: Docker Hub secret is now managed in the base stack
# Reference it via: docker_hub_secret_name, docker_hub_secret_arn (from base stack)

# =============================================================================
# S3 BUCKETS (Stack-Specific Storage)
# =============================================================================

# Create S3 bucket for source code with unique naming
source_bucket = aws.s3.Bucket(
    "knock-source-bucket",
    bucket=f"{PROJECT_NAME}-source-{STACK_NAME}",
    force_destroy=True,
)

# Create S3 bucket for output files (temporary storage)
output_bucket = aws.s3.Bucket(
    "knock-output-bucket",
    bucket=f"{PROJECT_NAME}-output-{STACK_NAME}",
    force_destroy=True,
)

# Create S3 bucket for device credentials (persistent storage)
device_credentials_bucket = aws.s3.Bucket(
    "knock-device-credentials-bucket",
    bucket=f"{PROJECT_NAME}-device-credentials-{STACK_NAME}",
    force_destroy=True,
)

# Create lifecycle configuration for output bucket
output_bucket_lifecycle = aws.s3.BucketLifecycleConfiguration(
    "knock-output-bucket-lifecycle",
    bucket=output_bucket.id,
    rules=[
        aws.s3.BucketLifecycleConfigurationRuleArgs(
            id="delete-old-files",
            status="Enabled",
            expiration=aws.s3.BucketLifecycleConfigurationRuleExpirationArgs(
                days=OUTPUT_BUCKET_LIFECYCLE_DAYS  # Delete files after configured days
            ),
        )
    ],
)


# Create CodeBuild service role
codebuild_role = aws.iam.Role(
    "codebuild-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "codebuild.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    ),
)


# Attach policies to CodeBuild role
codebuild_policy = aws.iam.RolePolicy(
    "codebuild-policy",
    role=codebuild_role.id,
    policy=pulumi.Output.all(
        ecr_repo.arn,
        source_bucket.arn,
    ).apply(
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                        ],
                        "Resource": "arn:aws:logs:*:*:*",
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ecr:GetAuthorizationToken",
                        ],
                        "Resource": "*",  # This action requires wildcard
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:BatchGetImage",
                            "ecr:PutImage",
                            "ecr:InitiateLayerUpload",
                            "ecr:UploadLayerPart",
                            "ecr:CompleteLayerUpload",
                            "ecr:DescribeRepositories",
                            "ecr:DescribeImages",
                            "ecr:CreateRepository",  # Needed for pull-through cache to create repos on-demand
                            "ecr:BatchImportUpstreamImage",  # Needed for pull-through cache to import images
                            "ecr:DescribePullThroughCacheRules",  # Needed to verify cache rules
                        ],
                        "Resource": "*",  # Pull-through cache creates dynamic repositories
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:GetObjectVersion",
                            "s3:ListBucket",
                            "s3:ListBucketVersions",
                        ],
                        "Resource": [args[1], f"{args[1]}/*"],  # Source bucket ARN
                    },
                ],
            }
        )
    ),
)

# CodeBuild Approach - Build and push Docker image using AWS CodeBuild
# This approach doesn't require Docker on the local machine

# Upload source code to S3 (include project root directory)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
source_object = aws.s3.BucketObject(
    "source-code",
    bucket=source_bucket.bucket,
    key="source.zip",
    source=pulumi.FileArchive(project_root),  # Use absolute path to project root
    opts=pulumi.ResourceOptions(depends_on=[source_bucket]),
)

# Upload Dockerfile separately to track its changes
# This is used to trigger rebuilds when the Dockerfile changes (actual application code)
dockerfile_object = aws.s3.BucketObject(
    "dockerfile",
    bucket=source_bucket.bucket,
    key="infrastructure/lambda/Dockerfile",
    source=pulumi.FileAsset("lambda/Dockerfile"),
    opts=pulumi.ResourceOptions(depends_on=[source_bucket]),
)

# Upload Lambda handler separately to track application code changes
# This is used to trigger rebuilds when the actual Lambda code changes
lambda_handler_object = aws.s3.BucketObject(
    "lambda-handler",
    bucket=source_bucket.bucket,
    key="infrastructure/lambda/handler.py",
    source=pulumi.FileAsset("lambda/handler.py"),
    opts=pulumi.ResourceOptions(depends_on=[source_bucket]),
)

# Build dependency list for CodeBuild project
codebuild_dependencies = [
    ecr_repo,
    codebuild_policy,
    source_bucket,
    # Note: public_ecr_cache_rule is now in base stack, no dependency needed here
]

# Create CodeBuild project
codebuild_project = aws.codebuild.Project(
    "knock-lambda-build",
    name=f"knock-lambda-build-{STACK_NAME}",
    service_role=codebuild_role.arn,
    artifacts=aws.codebuild.ProjectArtifactsArgs(type="NO_ARTIFACTS"),
    environment=aws.codebuild.ProjectEnvironmentArgs(
        compute_type=CODEBUILD_COMPUTE_TYPE,
        image=CODEBUILD_IMAGE,
        type="LINUX_CONTAINER",
        privileged_mode=True,  # Required for Docker builds
        environment_variables=[
            aws.codebuild.ProjectEnvironmentEnvironmentVariableArgs(
                name="ECR_REPOSITORY_URI", value=ecr_repo.repository_url
            ),
            aws.codebuild.ProjectEnvironmentEnvironmentVariableArgs(
                name="AWS_DEFAULT_REGION", value=AWS_REGION
            ),
            aws.codebuild.ProjectEnvironmentEnvironmentVariableArgs(
                name="ECR_REGISTRY_URL",
                value=ecr_repo.repository_url.apply(lambda url: url.split("/")[0]),
            ),
        ],
    ),
    source=aws.codebuild.ProjectSourceArgs(
        type="S3",
        location=pulumi.Output.concat(source_bucket.bucket, "/source.zip"),
        buildspec=get_validated_buildspec(),
    ),
    opts=pulumi.ResourceOptions(depends_on=codebuild_dependencies),
)

# Create IAM role for Lambda
lambda_role = aws.iam.Role(
    "knock-lambda-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                }
            ],
        },
        indent=4,
    ),
)

# Attach basic Lambda execution policy
lambda_policy_attachment = aws.iam.RolePolicyAttachment(
    "knock-lambda-policy",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
)

# Add S3 permissions for Lambda to access output bucket and device credentials bucket
lambda_s3_policy = aws.iam.RolePolicy(
    "knock-lambda-s3-policy",
    role=lambda_role.id,
    policy=pulumi.Output.all(output_bucket.arn, device_credentials_bucket.arn).apply(
        lambda arns: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:PutObject",
                            "s3:PutObjectAcl",
                            "s3:GetObject",
                            "s3:DeleteObject",
                        ],
                        "Resource": [f"{arns[0]}/*", f"{arns[1]}/*"],
                    },
                    {
                        "Effect": "Allow",
                        "Action": "s3:ListBucket",
                        "Resource": [arns[0], arns[1]],
                    },
                ],
            }
        )
    ),
)

# Build dependency list for build command
# Dependencies: Must wait for CodeBuild project (cache rules are in base stack)
build_command_dependencies = [codebuild_project, source_object]

# Trigger CodeBuild to build and push the Docker image
# IMPORTANT: Only trigger on actual application code changes (Dockerfile, handler.py)
# NOT on infrastructure changes (buildspec, __main__.py, etc.)
build_command = command.local.Command(
    "knock-lambda-build-run",
    create=pulumi.Output.concat(codebuild_project.name).apply(
        lambda project_name: f"{SHELL_CMD} shell/codebuild-runner-with-digest.sh '{project_name}' '{AWS_REGION}' '{CODEBUILD_MAX_RETRIES}' '{CODEBUILD_RETRY_DELAY}' '{CODEBUILD_TIMEOUT_MINUTES}'"
    ),
    triggers=[
        dockerfile_object.version_id,  # Rebuild when Dockerfile changes
        lambda_handler_object.version_id,  # Rebuild when Lambda handler changes
    ],  # Do NOT include source_object to avoid rebuilds on infrastructure changes
    opts=pulumi.ResourceOptions(depends_on=build_command_dependencies),
)


def get_temp_file_path():
    """Get the cross-platform path to the image digest file"""
    temp_dir = tempfile.gettempdir()
    return os.path.join(temp_dir, "image_uri_digest.txt")


# Read the image digest after the build completes
# Only re-read when application code changes (not infrastructure)
image_digest_command = command.local.Command(
    "get-image-digest",
    create=f"cat '{get_temp_file_path()}' 2>/dev/null || echo 'digest-not-found'",
    triggers=[
        dockerfile_object.version_id,  # Re-read when Dockerfile changes
        lambda_handler_object.version_id,  # Re-read when Lambda handler changes
    ],  # Do NOT include source_object to avoid re-reading on infrastructure changes
    opts=pulumi.ResourceOptions(depends_on=[build_command]),
)

# Create Lambda function using ECR image (after build completes)
lambda_function = aws.lambda_.Function(
    "knock-lambda",
    package_type="Image",
    image_uri=image_digest_command.stdout.apply(
        lambda digest_output: (
            digest_output.strip()
            if digest_output.strip() != "digest-not-found"
            else pulumi.Output.concat(ecr_repo.repository_url, ":latest").apply(
                lambda x: x
            )
        )
    ),
    role=lambda_role.arn,
    timeout=LAMBDA_TIMEOUT,  # Configurable timeout
    memory_size=LAMBDA_MEMORY,  # Configurable memory
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables=pulumi.Output.all(
            image_digest_command.stdout,
            output_bucket.bucket,
            device_credentials_bucket.bucket,
        ).apply(
            lambda args: {
                "PYTHONPATH": "/var/task",
                "OUTPUT_BUCKET": args[1],
                "DEVICE_CREDENTIALS_BUCKET": args[2],
                "IMAGE_DIGEST": args[0].strip(),  # Forces Lambda update on new image
            }
        )
    ),
    opts=pulumi.ResourceOptions(
        depends_on=[lambda_policy_attachment, lambda_s3_policy, image_digest_command]
    ),
)

# Wait for Lambda function to be active and updated with the correct image
lambda_wait_command = command.local.Command(
    "lambda-wait-active",
    create=pulumi.Output.all(lambda_function.name, image_digest_command.stdout).apply(
        lambda args: f"{SHELL_CMD} shell/lambda-wait.sh '{args[0]}' '{AWS_REGION}' '{args[1].strip()}'"
    ),
    triggers=[
        image_digest_command.stdout,
    ],  # Re-run when image changes
    opts=pulumi.ResourceOptions(depends_on=[lambda_function]),
)

# Create Lambda function URL for HTTP access
function_url = aws.lambda_.FunctionUrl(
    "knock-lambda-url",
    function_name=lambda_function.name,
    authorization_type="NONE",  # Change to 'AWS_IAM' for secured access
    cors={
        "allow_credentials": False,
        "allow_headers": ["*"],
        "allow_methods": ["POST", "GET"],
        "allow_origins": ["*"],
        "max_age": 300,
    },
    opts=pulumi.ResourceOptions(depends_on=[lambda_wait_command]),
)

# Create CloudWatch Log Group for Lambda
log_group = aws.cloudwatch.LogGroup(
    "knock-lambda-logs",
    name=pulumi.Output.concat("/aws/lambda/", lambda_function.name),
    retention_in_days=LAMBDA_RETENTION_DAYS,
)

# Export important values
pulumi.export("ecr_repository_url", ecr_repo.repository_url)
pulumi.export("lambda_function_name", lambda_function.name)
pulumi.export("lambda_function_arn", lambda_function.arn)
pulumi.export("function_url", function_url.function_url)
pulumi.export("source_bucket", source_bucket.bucket)
pulumi.export("output_bucket", output_bucket.bucket)
pulumi.export("device_credentials_bucket", device_credentials_bucket.bucket)
pulumi.export("codebuild_project_name", codebuild_project.name)
pulumi.export("codebuild_run_id", build_command.id)

# Export OIDC Role ARNs for authentication configuration
pulumi.export("github_actions_role_arn", github_actions_role.arn)
pulumi.export("pulumi_esc_role_arn", pulumi_esc_role.arn)

# Export shared resource references from base stack (for convenience)
pulumi.export("github_oidc_provider_arn", github_oidc_provider_arn)
pulumi.export("pulumi_oidc_provider_arn", pulumi_oidc_provider_arn)
pulumi.export("docker_hub_secret_name", docker_hub_secret_name)
pulumi.export(
    "public_ecr_cache_prefix", base_stack.get_output("public_ecr_cache_prefix")
)
