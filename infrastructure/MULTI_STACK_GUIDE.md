# Multi-Stack Deployment Guide

This project uses a **unified Pulumi project** with multiple stacks to eliminate resource duplication and improve maintainability.

## Stack Architecture

All stacks share the same `Pulumi.yaml` but execute different code paths based on the stack name.

### Base Stack (`knock-lambda/base`)

**Purpose**: Shared infrastructure used across all environments

**Resources**:

- OIDC Providers (GitHub Actions, Pulumi ESC) - Protected from deletion
- Docker Hub credentials secret (AWS Secrets Manager)
- Public ECR pull-through cache configuration

**Code Location**: `infrastructure/base_stack.py`

### Environment Stacks (`knock-lambda/dev`, `knock-lambda/main`)

**Purpose**: Environment-specific resources

**Resources**:

- ECR repositories (one per environment)
- Lambda functions and configurations
- S3 buckets (source, output, device credentials)
- CodeBuild projects
- IAM roles (GitHub Actions, Pulumi ESC) - environment-specific
- CloudWatch log groups

**Code Location**: `infrastructure/environment_stack.py`

## Deployment Order

### Initial Setup (One-Time)

1. **Deploy the base stack first**:

   ```bash
   cd infrastructure

   # Create and select the base stack (if not exists)
   pulumi stack init loganpowell/knock-lambda/base
   pulumi stack select loganpowell/knock-lambda/base

   # Set Docker Hub credentials (if available)
   export DOCKER_HUB_USERNAME="your-username"
   export DOCKER_HUB_TOKEN="your-token"

   # Deploy base infrastructure
   pulumi up

   # Verify outputs
   pulumi stack output github_oidc_provider_arn
   pulumi stack output pulumi_oidc_provider_arn
   pulumi stack output docker_hub_secret_name
   ```

2. **Deploy environment stacks** (dev, main):

   ```bash
   # Deploy dev stack
   pulumi stack select loganpowell/knock-lambda/dev
   pulumi up

   # Deploy main stack
   pulumi stack select loganpowell/knock-lambda/main
   pulumi up
   ```

### Normal Workflow

After initial setup, you typically only work with environment stacks:

```bash
# Make changes to application code or infrastructure
# Deploy to dev for testing
pulumi stack select loganpowell/knock-lambda/dev
pulumi up

# Deploy to main for production
pulumi stack select loganpowell/knock-lambda/main
pulumi up
```

### Base Stack Updates

Only update the base stack when you need to modify shared resources:

```bash
pulumi stack select loganpowell/knock-lambda/base
pulumi up
```

**⚠️ Warning**: Changes to the base stack affect ALL environment stacks!

## Stack Dependencies

Environment stacks reference the base stack using `StackReference`:

```python
base_stack = pulumi.StackReference(f"{GITHUB_ORG}/{PROJECT_NAME}/base")
github_oidc_provider_arn = base_stack.get_output("github_oidc_provider_arn")
```

## How It Works

The `infrastructure/__main__.py` file detects the stack name and routes to the appropriate code:

```python
# If stack name contains 'base' -> loads infrastructure/base_stack.py
# Otherwise -> loads infrastructure/environment_stack.py
if "base" in stack_name.lower():
    from infrastructure import base_stack
else:
    from infrastructure import environment_stack
```

This allows all stacks to share the same `Pulumi.yaml` configuration.

## Resource Protection

The following resources in the base stack are **protected** from deletion:

- GitHub OIDC Provider
- Pulumi OIDC Provider
- Docker Hub credentials secret

To delete protected resources:

```bash
# Unprotect the resource
pulumi state unprotect 'urn:pulumi:base::knock-lambda-base::aws:iam/openIdConnectProvider:OpenIdConnectProvider::github-oidc-provider'

# Then destroy
pulumi destroy
```

## Benefits of This Architecture

✅ **No Resource Duplication**: OIDC providers, secrets, and cache rules created once
✅ **Stable ARNs**: Shared resources maintain consistent ARNs across deployments
✅ **Independent Environments**: Dev and main can be deployed independently  
✅ **Simplified Maintenance**: Update shared resources in one place
✅ **Cost Optimization**: Fewer duplicate resources = lower AWS costs
✅ **Faster Deployments**: Environment stacks are smaller and deploy faster

## Troubleshooting

### "StackReference not found"

Ensure the base stack is deployed first:

```bash
pulumi stack select loganpowell/knock-lambda/base
pulumi stack
```

### "Cannot delete protected resource"

Unprotect before deletion:

```bash
pulumi state unprotect <resource-urn>
```

### "Outputs not available"

Verify base stack has run successfully:

```bash
pulumi stack select loganpowell/knock-lambda/base
pulumi stack output
```

## File Structure

```
infrastructure/
├── __main__.py              # Unified entry point (routes to base_stack or environment_stack)
├── base_stack.py            # Base stack code (shared resources)
├── environment_stack.py     # Environment stack code (dev, main)
├── config.py                # Shared configuration
├── utils.py                 # Shared utilities
├── Pulumi.loganpowell-knock-lambda-base.yaml  # Base stack config
├── Pulumi.dev.yaml          # Dev stack config
└── Pulumi.main.yaml         # Main stack config
```
