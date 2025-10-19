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

- `lambda_timeout` - Lambda timeout in seconds (default: 900 = 15 minutes)
- `lambda_memory` - Lambda memory in MB (default: 3008 = maximum)
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
  lambda_timeout: 300
  lambda_memory: 1024
  lambda_log_retention: 30
  output_bucket_lifecycle_days: 7
  ecr_image_retention: 10
```

## Regional Considerations

**Important**: Ensure your AWS region is set consistently. The infrastructure creates resources in the configured region, and the CodeBuild process needs to match this region for ECR access.

Common regions:

- `us-east-1` - N. Virginia (default for many AWS services)
- `us-east-2` - Ohio
- `us-west-2` - Oregon
- `eu-west-1` - Ireland
