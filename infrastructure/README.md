# Knock Lambda Infrastructure

This directory contains the Pulumi infrastructure code for deploying the Knock Lambda function to AWS.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) - Python package manager
- [Pulumi](https://www.pulumi.com/docs/get-started/install/) - Infrastructure as Code
- AWS CLI configured with appropriate credentials

**Note**: Docker is **not** required locally - the infrastructure uses AWS CodeBuild to build container images in the cloud.

## File Structure

```
infrastructure/
├── __main__.py                        # Main Pulumi infrastructure definition
├── config.py                          # Configuration constants and defaults
├── buildspec.yml                      # AWS CodeBuild build specification
├── codebuild-runner-with-digest.sh    # CodeBuild execution script with error reporting
├── lambda-wait.sh                     # Wait for Lambda deployment to complete
├── deploy.sh                          # One-command deployment wrapper
├── platform-compat.sh                 # Cross-platform shell script utilities
├── Pulumi.yaml                        # Pulumi project configuration
├── Pulumi.dev.yaml                    # Development stack configuration
├── CONFIG.md                          # Configuration options documentation
├── PLATFORM_COMPAT.md                 # Platform compatibility documentation
├── README.md                          # This file
└── lambda/                            # Lambda function package
    ├── __init__.py                    # Package initialization
    ├── Dockerfile                     # Container definition for Lambda
    ├── handler.py                     # Python Lambda handler implementation
    ├── requirements.txt               # Python dependencies for Lambda
    └── README.md                      # Lambda API documentation
```

## Setup

1. **Install dependencies using uv:**

   ```bash
   # Run from the project root directory (where pyproject.toml is located)
   uv sync
   ```

2. **Activate the virtual environment:**

   ```bash
   uv shell
   ```

3. **Navigate to infrastructure directory for deployment:**

   ```bash
   cd infrastructure
   ```

4. **Configure Pulumi:**

   ```bash
   # Set your AWS region
   pulumi config set aws:region us-east-1

   # Review the Pulumi configuration
   pulumi config
   ```

## Deployment

Deploy the infrastructure:

```bash
# Preview changes
pulumi preview

# Deploy
pulumi up
```

This will:

1. Create an ECR repository for container images
2. Upload your source code to S3
3. Create a CodeBuild project to build and push your Docker image
4. Execute the CodeBuild to build the container image
5. Create Lambda function, IAM roles, and supporting resources
6. Set up S3 buckets for temporary file storage
7. Create a Lambda function URL for HTTP access

```
ECR Repository ─┐
Source Bucket ──┼─→ CodeBuild Project ─→ CodeBuild Build ─→ Lambda Function
CodeBuild Role ─┘
```

**No local Docker required** - all container building happens in AWS CodeBuild.

## Development

### Adding Dependencies

Add new Python dependencies:

```bash
# Add to main dependencies
uv add package-name

# Add to dev dependencies
uv add --dev package-name
```

### Code Formatting

Format code with the included dev tools:

```bash
# Format with black
uv run black .

# Lint with ruff
uv run ruff check .
```

### Testing

Run tests:

```bash
uv run pytest
```

## Architecture

The infrastructure uses **AWS CodeBuild** for building and deploying containers (no local Docker required):

### Core Resources

1. **ECR Repository** (`ecr_repo`): Stores container images with lifecycle policy
2. **S3 Buckets**:
   - **Source Bucket**: Stores uploaded project source code (as ZIP)
   - **Output Bucket**: Temporary storage for converted ebooks (1-day expiration)
   - **Device Credentials Bucket**: Persistent storage for Adobe device credentials
3. **CodeBuild Project** (`codebuild_project`): Builds Docker image from `lambda/Dockerfile`
4. **Lambda Function** (`lambda_function`): Container-based function that processes ACSM files
5. **Lambda Function URL**: Public HTTP endpoint (no authentication required)
6. **IAM Roles**: Separate roles for CodeBuild and Lambda with appropriate permissions
7. **CloudWatch Log Group**: Lambda execution logs with configurable retention

### Build & Deploy Flow

```
┌─────────────────┐
│  Local Source   │
└────────┬────────┘
         │ FileArchive
         ▼
┌─────────────────┐
│  S3 Source      │
│  Bucket         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│  CodeBuild      │─────▶│  ECR Repository │
│  Project        │      │  (Docker Image) │
└────────┬────────┘      └────────┬────────┘
         │                        │
         │ codebuild-runner-      │
         │ with-digest.sh         │
         ▼                        │
┌─────────────────┐              │
│  Build          │              │
│  Execution      │              │
└────────┬────────┘              │
         │                        │
         │ Captures image digest  │
         ▼                        │
┌─────────────────┐              │
│  Lambda         │◀─────────────┘
│  Function       │   Uses image@digest
└────────┬────────┘
         │ lambda-wait.sh
         ▼
┌─────────────────┐
│  Active &       │
│  Ready          │
└─────────────────┘
```

### Deployment Scripts

- **`codebuild-runner-with-digest.sh`**: Orchestrates CodeBuild execution, waits for completion, captures image digest, provides detailed error reporting
- **`lambda-wait.sh`**: Waits for Lambda to become active and verifies correct image deployment
- **`deploy.sh`**: One-command deployment that runs `pulumi up` and tests the Lambda
- **`buildspec.yml`**: Defines CodeBuild phases (pre_build, build, post_build) for Docker image creation
- **`platform-compat.sh`**: Cross-platform shell utilities (macOS/Linux) sourced by other scripts

### Dependency Management

Pulumi automatically manages resource dependencies with explicit ordering:

```
ECR Repo ──┐
            ├─▶ CodeBuild Project ──▶ CodeBuild Build ──▶ Lambda Function ──▶ Lambda Wait ──▶ Function URL
            │                                    │                    │
S3 Source ─┘                                    │                    │
                                                 │                    │
                                    Captures image digest      Verifies deployment
```

No external scripts, local Docker, or manual coordination required for resource creation!

## Outputs

After deployment, these values are exported:

- `ecr_repository_url`: ECR repository URL
- `lambda_function_name`: Lambda function name
- `lambda_function_arn`: Lambda function ARN
- `function_url`: HTTP endpoint for the Lambda (public, no auth required)
- `source_bucket`: S3 bucket for source files
- `output_bucket`: S3 bucket for converted ebook files (1-day expiration)
- `device_credentials_bucket`: S3 bucket for Adobe device credentials
- `codebuild_project_name`: CodeBuild project name
- `codebuild_run_id`: CodeBuild build execution ID

View all outputs:
```bash
pulumi stack output
```

Get specific output:
```bash
pulumi stack output function_url
```

## Cleanup

Remove all resources:

```bash
pulumi destroy
```

## Deployment Options

### Option 1: Standard Pulumi Deployment

```bash
cd infrastructure
pulumi up
```

### Option 2: One-Command Deployment (with testing)

```bash
cd infrastructure
./deploy.sh
```

The `deploy.sh` script:
- Checks prerequisites (Pulumi, AWS CLI, credentials)
- Runs `pulumi up`
- Retrieves function URL
- Tests Lambda with a real ACSM file (if available)
- Provides deployment summary

### Option 3: Auto-approve Deployment

```bash
cd infrastructure
./deploy.sh --yes
# or
pulumi up --yes
```

## Benefits of CodeBuild Approach

- **No local Docker required**: Developers don't need Docker installed
- **Consistent build environment**: All builds happen in the same AWS environment
- **Scalable**: AWS handles the build infrastructure
- **Integrated**: Native Pulumi dependency management ensures proper ordering
- **Auditable**: All builds are logged in CloudWatch
- **Automatic digest capture**: Image digest ensures Lambda updates correctly
- **Enhanced error reporting**: Detailed error analysis in `codebuild-runner-with-digest.sh`

## Troubleshooting

### CodeBuild Failures

If CodeBuild fails, the `codebuild-runner-with-digest.sh` script provides:
- Key error summary extraction
- Docker-specific error analysis
- Dependency and package error detection
- Build phase failure identification
- Actionable fix suggestions
- Manual log analysis commands

View CloudWatch logs:
```bash
PROJECT=$(pulumi stack output codebuild_project_name)
aws logs tail "/aws/codebuild/$PROJECT" --follow --no-cli-pager
```

### Lambda Not Updating

If Lambda doesn't update after deployment:
1. Check if image digest was captured: `cat /tmp/image_uri_digest.txt`
2. Verify Lambda is using new image: `aws lambda get-function --function-name $(pulumi stack output lambda_function_name) --query 'Code.ImageUri' --no-cli-pager`
3. Force rebuild: `pulumi up --replace urn:pulumi:...:lambda:Function::knock-lambda`

### Device Credential Issues

If hitting Adobe device limits:
```bash
BUCKET=$(pulumi stack output device_credentials_bucket)
aws s3 rm s3://$BUCKET/credentials/ --recursive --no-cli-pager
```

See [docs/ACSM_DEVICE_LIMITS.md](../docs/ACSM_DEVICE_LIMITS.md) for details.
