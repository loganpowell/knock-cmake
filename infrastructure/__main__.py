"""
Knock Lambda Infrastructure with Pulumi

This module provisions AWS infrastructure for the Knock ACSM conversion service.
The infrastructure includes:
- ECR repository for container images
- CodeBuild project to build Docker images using infrastructure/lambda/Dockerfile
- Lambda function using the container image with infrastructure/lambda/handler.py
- S3 buckets for temporary file storage
- IAM roles and policies for proper access control
"""

import json
import pulumi
import pulumi_aws as aws
import pulumi_command as command
from config import (
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


# YAML validation function
def validate_buildspec_yaml(buildspec_content):
    """Validate buildspec YAML before using it"""
    try:
        # Try to parse as YAML
        import yaml

        parsed = yaml.safe_load(buildspec_content)

        # Basic structure validation
        if not isinstance(parsed, dict):
            raise ValueError("Buildspec must be a dictionary")

        if "version" not in parsed:
            raise ValueError("Buildspec must have 'version' field")

        if "phases" not in parsed:
            raise ValueError("Buildspec must have 'phases' field")

        # Validate phases structure
        phases = parsed["phases"]
        if not isinstance(phases, dict):
            raise ValueError("'phases' must be a dictionary")

        for phase_name, phase_content in phases.items():
            if not isinstance(phase_content, dict):
                raise ValueError(f"Phase '{phase_name}' must be a dictionary")

            if "commands" in phase_content:
                commands = phase_content["commands"]
                if not isinstance(commands, list):
                    raise ValueError(f"Commands in phase '{phase_name}' must be a list")

                for i, cmd in enumerate(commands):
                    if not isinstance(cmd, str):
                        raise ValueError(
                            f"Command {i} in phase '{phase_name}' must be a string, got {type(cmd)}: {cmd}"
                        )

        print("✅ Buildspec YAML validation passed")
        return True

    except ImportError:
        print("⚠️ PyYAML not available, skipping validation")
        return True
    except Exception as e:
        print(f"❌ Buildspec YAML validation failed: {e}")
        raise e


def get_validated_buildspec():
    """Load and validate the buildspec YAML from file"""
    import os

    # Path to the buildspec file
    buildspec_path = os.path.join(os.path.dirname(__file__), "buildspec.yml")

    try:
        with open(buildspec_path, "r") as f:
            buildspec_content = f.read()

        # Validate the buildspec
        validate_buildspec_yaml(buildspec_content)
        return buildspec_content

    except FileNotFoundError:
        raise FileNotFoundError(f"Buildspec file not found at: {buildspec_path}")
    except Exception as e:
        raise Exception(f"Failed to load buildspec: {e}")


# Configuration imported from config.py
# aws_region, project_name, stack_name, etc. are now available

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

json_ecr_lifecycle_policy = json.dumps(
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
)
# Create ECR lifecycle policy to manage image retention
ecr_lifecycle_policy = aws.ecr.LifecyclePolicy(
    "knock-repo-lifecycle",
    repository=ecr_repo.name,
    policy=json_ecr_lifecycle_policy,
)

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


def codebuild_p_json(args) -> str:
    ecr_repo_arn, source_bucket_arn = args
    return json.dumps(
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
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                        "ecr:GetAuthorizationToken",
                        "ecr:PutImage",
                        "ecr:InitiateLayerUpload",
                        "ecr:UploadLayerPart",
                        "ecr:CompleteLayerUpload",
                        "ecr:DescribeRepositories",
                        "ecr:DescribeImages",
                        "ecr:CreateRepository",
                    ],
                    "Resource": "*",
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:GetObjectVersion",
                        "s3:ListBucket",
                        "s3:ListBucketVersions",
                    ],
                    "Resource": [source_bucket_arn, f"{source_bucket_arn}/*"],
                },
            ],
        }
    )


# Attach policies to CodeBuild role
codebuild_policy = aws.iam.RolePolicy(
    "codebuild-policy",
    role=codebuild_role.id,
    policy=pulumi.Output.all(ecr_repo.arn, source_bucket.arn).apply(codebuild_p_json),
)

# CodeBuild Approach - Build and push Docker image using AWS CodeBuild
# This approach doesn't require Docker on the local machine

# Upload source code to S3 (include project root directory)
source_object = aws.s3.BucketObject(
    "source-code",
    bucket=source_bucket.bucket,
    key="source.zip",
    source=pulumi.FileArchive(
        ".."
    ),  # Include the project root directory (parent of infrastructure/)
    opts=pulumi.ResourceOptions(depends_on=[source_bucket]),
)

# Upload Dockerfile separately to track its changes
dockerfile_object = aws.s3.BucketObject(
    "dockerfile",
    bucket=source_bucket.bucket,
    key="infrastructure/lambda/Dockerfile",
    source=pulumi.FileAsset("lambda/Dockerfile"),
    opts=pulumi.ResourceOptions(depends_on=[source_bucket]),
)

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
        ],
    ),
    source=aws.codebuild.ProjectSourceArgs(
        type="S3",
        location=pulumi.Output.concat(source_bucket.bucket, "/source.zip"),
        buildspec=get_validated_buildspec(),
    ),
    opts=pulumi.ResourceOptions(depends_on=[ecr_repo, codebuild_policy, source_bucket]),
)

# Create IAM role for Lambda
lambda_role = aws.iam.Role(
    "knock-lambda-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                }
            }
        ]
    }""",
)

# Attach basic Lambda execution policy
lambda_policy_attachment = aws.iam.RolePolicyAttachment(
    "knock-lambda-policy",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
)

# Add S3 permissions for Lambda to access output bucket
lambda_s3_policy = aws.iam.RolePolicy(
    "knock-lambda-s3-policy",
    role=lambda_role.id,
    policy=output_bucket.arn.apply(
        lambda bucket_arn: json.dumps(
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
                        "Resource": f"{bucket_arn}/*",
                    },
                    {
                        "Effect": "Allow",
                        "Action": "s3:ListBucket",
                        "Resource": bucket_arn,
                    },
                ],
            }
        )
    ),
)

# Trigger CodeBuild to build and push the Docker image
build_command = command.local.Command(
    "knock-lambda-build-run",
    create=pulumi.Output.concat(codebuild_project.name).apply(
        lambda project_name: f"bash codebuild-runner-with-digest.sh '{project_name}' '{AWS_REGION}' '{CODEBUILD_MAX_RETRIES}' '{CODEBUILD_RETRY_DELAY}' '{CODEBUILD_TIMEOUT_MINUTES}'"
    ),
    triggers=[
        source_object.version_id,
        dockerfile_object.version_id,
    ],  # Re-run when source code or Dockerfile changes
    opts=pulumi.ResourceOptions(
        depends_on=[codebuild_project, source_object, dockerfile_object]
    ),
)

# Read the image digest from the build output
image_digest_command = command.local.Command(
    "get-image-digest",
    create="cat /tmp/image_uri_digest.txt 2>/dev/null || echo 'digest-not-found'",
    triggers=[
        source_object.version_id,
        dockerfile_object.version_id,
    ],  # Re-run when source code or Dockerfile changes
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
    environment={
        "variables": {
            "PYTHONPATH": "/var/task",
            "OUTPUT_BUCKET": output_bucket.bucket,
        }
    },
    opts=pulumi.ResourceOptions(
        depends_on=[lambda_policy_attachment, lambda_s3_policy, image_digest_command]
    ),
)

# Wait for Lambda function to be active and updated
lambda_wait_command = command.local.Command(
    "lambda-wait-active",
    create=pulumi.Output.concat(lambda_function.name).apply(
        lambda function_name: f"bash lambda-wait.sh '{function_name}' '{AWS_REGION}'"
    ),
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
pulumi.export("codebuild_project_name", codebuild_project.name)
pulumi.export("codebuild_run_id", build_command.id)
