# Docker Hub Credentials Setup

This document explains how Docker Hub credentials are managed for the ECR pull-through cache feature.

## Overview

Docker Hub credentials are used in two places:

1. **AWS Secrets Manager** - Shared secret used by ECR pull-through cache across all stacks
2. **GitHub Secrets** - Repository secrets that pass credentials to GitHub Actions workflows

## Architecture

```
Pulumi Config (local)
    ↓
    ├─→ AWS Secrets Manager (ecr-pullthroughcache/docker-hub)
    │   └─→ Referenced by all Pulumi stacks (main, dev, etc.)
    │       └─→ Used by ECR pull-through cache
    │
    └─→ GitHub Secrets (DOCKER_HUB_USERNAME, DOCKER_HUB_TOKEN)
        └─→ Passed to GitHub Actions as environment variables
            └─→ Pulumi references existing AWS secret
```

## Key Principle

**The AWS Secrets Manager secret is created ONCE and shared across all stacks.**

- ✅ Pulumi **references** the existing secret via `aws.secretsmanager.get_secret()`
- ❌ Pulumi does NOT create/manage the secret (avoiding `ResourceExistsException`)
- 🔄 Each stack creates its own pull-through cache rule pointing to the shared secret

## Setup Instructions

### One-Time Setup

1. **Set credentials in Pulumi config:**
   ```bash
   pulumi config set dockerHubUsername your_username
   pulumi config set --secret dockerHubToken your_token
   ```

2. **Run the setup script:**
   ```bash
   ./scripts/sync-pulumi-gh-docker.sh
   ```

   This script will:
   - ✅ Create/update AWS Secrets Manager secret
   - ✅ Sync credentials to GitHub repository secrets
   - ✅ Set up resource policy for ECR access

### Local Development

```bash
# Credentials come from Pulumi config
pulumi up
```

### GitHub Actions

Credentials are automatically provided via GitHub Secrets:
- `DOCKER_HUB_USERNAME` → `${{ secrets.DOCKER_HUB_USERNAME }}`
- `DOCKER_HUB_TOKEN` → `${{ secrets.DOCKER_HUB_TOKEN }}`

No additional setup needed once the initial sync is done.

## Credential Flow

### Local Deployment
```
Pulumi Config → Environment Variables → Pulumi Code
                                            ↓
                                    References AWS Secret
                                            ↓
                                    Creates Cache Rule
```

### GitHub Actions
```
GitHub Secrets → Workflow env → Pulumi Code
                                     ↓
                             References AWS Secret
                                     ↓
                             Creates Cache Rule
```

## Troubleshooting

### Error: `ResourceExistsException`

**Problem:** Pulumi is trying to create a secret that already exists.

**Solution:** The code has been updated to **reference** the existing secret instead of creating it. Make sure you're using the latest version of `infrastructure/__main__.py`.

### Error: Secret not found

**Problem:** AWS Secrets Manager secret doesn't exist yet.

**Solution:** Run the setup script:
```bash
./scripts/sync-pulumi-gh-docker.sh
```

### GitHub Actions can't find credentials

**Problem:** GitHub Secrets not set.

**Solution:** 
1. Ensure Pulumi config is set locally
2. Run `./scripts/sync-pulumi-gh-docker.sh`
3. Verify with `gh secret list`

## Verification

### Check AWS Secret

```bash
aws secretsmanager describe-secret \
  --secret-id ecr-pullthroughcache/docker-hub \
  --region us-east-2
```

### Check GitHub Secrets

```bash
gh secret list
```

Expected output should include:
- `DOCKER_HUB_USERNAME`
- `DOCKER_HUB_TOKEN`

### Check Pull-Through Cache

```bash
aws ecr describe-pull-through-cache-rules --region us-east-2
```

## Security Notes

- 🔒 AWS secret is encrypted at rest by AWS Secrets Manager
- 🔒 GitHub Secrets are encrypted and only exposed to workflow runs
- 🔒 Pulumi config secrets are encrypted in state files
- 🔐 Resource policy ensures only ECR service can read the AWS secret
- 🔑 Use Docker Hub tokens with read-only permissions for public repos

## Cost

- **AWS Secrets Manager:** $0.40/month per secret
- **GitHub Secrets:** Free
- **Pulumi Config:** Free

Total: **$0.40/month** (justified by build speed improvements and reliability)

## Related Documentation

- [ECR Pull-Through Cache Implementation](./ECR_PULL_THROUGH_CACHE.md)
- [Pulumi Configuration](./CONFIG.md)
