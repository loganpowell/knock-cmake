# Infrastructure Configuration

This document describes the configurable options for the Knock Lambda infrastructure.

## Setting Configuration

Configuration can be set using Pulumi config commands:

```bash
# Set AWS region
pulumi config set aws:region us-east-2

# Set custom configuration values
pulumi config set lambda_timeout 600
pulumi config set lambda_memory 2048
```

## Available Configuration Options

### AWS Configuration

- `aws:region` - AWS region (default: us-east-2)
- `aws_region` - Alternative way to set AWS region

### Lambda Configuration

- `lambda_timeout` - Lambda timeout in seconds (default: 900 = 15 minutes, max: 900)
- `lambda_memory` - Lambda memory in MB (default: 10240 = 10GB, maximum available)
- `lambda_log_retention` - CloudWatch log retention days (default: 14)

### S3 Configuration

- `output_bucket_lifecycle_days` - Days before output files are deleted (default: 1)

### ECR Configuration

- `ecr_image_retention` - Number of container images to keep (default: 5)

### CodeBuild Configuration

- `codebuild_compute_type` - Build instance type (default: BUILD_GENERAL1_MEDIUM)
- `codebuild_image` - Build environment image (default: aws/codebuild/standard:7.0)
- `codebuild_max_retries` - Max retries for build start (default: 10)
- `codebuild_retry_delay` - Seconds between retries (default: 30)
- `codebuild_timeout_minutes` - Max build duration in minutes (default: 30)

## Environment-Specific Configuration

Create stack-specific config files:

- `Pulumi.dev.yaml` - Development environment
- `Pulumi.prod.yaml` - Production environment
- `Pulumi.staging.yaml` - Staging environment

Example `Pulumi.prod.yaml`:

```yaml
config:
  aws:region: us-west-2
  knock-lambda:lambda_timeout: 600  # 10 minutes
  knock-lambda:lambda_memory: 5120  # 5GB
  knock-lambda:lambda_log_retention: 30  # 30 days
  knock-lambda:output_bucket_lifecycle_days: 7  # Keep files for 1 week
  knock-lambda:ecr_image_retention: 10  # Keep 10 images
  knock-lambda:codebuild_timeout_minutes: 60  # 1 hour timeout
```

**Note**: Configuration keys must be prefixed with `knock-lambda:` (the project name).

## Current Configuration

View your current stack configuration:

```bash
pulumi config
```

View all Pulumi outputs:

```bash
pulumi stack output
```

## Regional Considerations

**Important**: Ensure your AWS region is set consistently. The infrastructure creates resources in the configured region, and the CodeBuild process needs to match this region for ECR access.

Current default: `us-east-2` (Ohio)

Common regions:

- `us-east-1` - N. Virginia (default for many AWS services)
- `us-east-2` - Ohio (project default)
- `us-west-2` - Oregon
- `eu-west-1` - Ireland

## Performance Tuning

### Lambda Memory

The Lambda memory setting affects both RAM and CPU allocation:

- **Default (10240 MB)**: Maximum memory, best performance for large ebooks
- **5120 MB (5 GB)**: Good balance of cost and performance
- **3008 MB (3 GB)**: Minimum recommended for ebook processing

### Lambda Timeout

Processing time varies by ebook size and complexity:

- **Default (900s / 15 min)**: Maximum timeout, handles large files
- **600s (10 min)**: Suitable for most ebooks
- **300s (5 min)**: Fast processing, may timeout on large files

### CodeBuild Configuration

- **Compute Type**: `BUILD_GENERAL1_MEDIUM` (default) suitable for most builds
- **Build Timeout**: 30 minutes (default) for C++ compilation
- **Retry Logic**: 10 retries with 30-second delays for eventual consistency
