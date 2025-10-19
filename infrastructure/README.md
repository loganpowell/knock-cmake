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
├── __main__.py           # Main Pulumi infrastructure code
├── config.py            # Configuration constants
├── README.md           # This file
├── lambda/              # Lambda function package
│   ├── __init__.py      # Package initialization
│   ├── Dockerfile       # Container definition for Lambda
│   ├── handler.py # Lambda handler implementation
│   └── requirements.txt # Python dependencies for Lambda
└── pyproject.toml      # Project configuration (in parent directory)
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

1. **ECR Repository**: Stores container images
2. **S3 Source Bucket**: Stores uploaded source code
3. **CodeBuild Project**: Builds Docker image from `../Dockerfile.lambda`
4. **CodeBuild Build**: Executes the build and pushes to ECR
5. **Lambda Function**: Deploys the container image with proper dependency ordering
6. **S3 Output Bucket**: For temporary file storage
7. **IAM Roles**: Proper permissions for CodeBuild and Lambda execution

### Dependency Management

Pulumi automatically manages resource dependencies:

```
S3 Source Upload → CodeBuild Project → CodeBuild Build → Lambda Function
```

No external scripts, local Docker, or manual coordination required!

## Outputs

After deployment, these values are exported:

- `ecr_repository_url`: ECR repository URL
- `lambda_function_name`: Lambda function name
- `lambda_function_arn`: Lambda function ARN
- `function_url`: HTTP endpoint for the Lambda
- `codebuild_project_name`: CodeBuild project name
- `codebuild_run_id`: CodeBuild build execution ID
- `source_bucket`: S3 bucket for source files
- `output_bucket`: S3 bucket for output files

## Cleanup

Remove all resources:

```bash
pulumi destroy
```

## Benefits of CodeBuild Approach

- **No local Docker required**: Developers don't need Docker installed
- **Consistent build environment**: All builds happen in the same AWS environment
- **Scalable**: AWS handles the build infrastructure
- **Integrated**: Native Pulumi dependency management ensures proper ordering
- **Auditable**: All builds are logged in CloudWatch
