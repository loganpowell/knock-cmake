# Docker Hub Pull-Through Cache Setup Guide

This guide explains how to set up Docker Hub credentials for ECR pull-through cache.

## Why Use Pull-Through Cache?

ECR pull-through cache with Docker Hub credentials provides:

- **Faster builds**: 50-75% faster base image pulls (from ECR instead of Docker Hub)
- **Cost savings**: Reduced build time = lower CodeBuild costs
- **Reliability**: No Docker Hub rate limits or outages
- **Security**: Cached images scanned by ECR

## Prerequisites

1. **Docker Hub Account** (free tier works)

   - Sign up at https://hub.docker.com if you don't have one

2. **GitHub CLI** (for syncing secrets)
   ```bash
   brew install gh
   gh auth login
   ```

## Setup Steps

### Step 1: Create Docker Hub Access Token

1. Log into Docker Hub: https://hub.docker.com
2. Go to **Account Settings** → **Security**
3. Click **New Access Token**
4. Settings:
   - **Description**: `ECR Pull-Through Cache`
   - **Access permissions**: **Public Repo Read-only**
5. Click **Generate** and copy the token (you'll only see it once!)

### Step 2: Add Credentials to Local .env

Add these lines to your `.env` file (create it from `.env.example` if needed):

```bash
DOCKER_HUB_USERNAME=your_dockerhub_username
DOCKER_HUB_TOKEN=dckr_pat_your_access_token_here
```

### Step 3: Sync to GitHub Repository Secrets

Run the sync script to push your credentials to GitHub:

```bash
chmod +x scripts/setup-docker-credentials.sh
./scripts/setup-docker-credentials.sh
```

This will set:

- `DOCKER_HUB_USERNAME` secret in your GitHub repository
- `DOCKER_HUB_TOKEN` secret in your GitHub repository

**Verify it worked:**

```bash
gh secret list
```

You should see both `DOCKER_HUB_USERNAME` and `DOCKER_HUB_TOKEN` listed.

### Step 4: Deploy Infrastructure

Now deploy with Pulumi:

```bash
# Local deployment (uses .env)
pulumi up

# Or via GitHub Actions (uses secrets automatically)
git push origin main
```

## How It Works

### Local Development

When you run `pulumi up` locally:

1. Pulumi reads `DOCKER_HUB_USERNAME` and `DOCKER_HUB_TOKEN` from your `.env` file
2. Creates an AWS Secrets Manager secret with these credentials
3. Creates an ECR pull-through cache rule pointing to Docker Hub
4. Updates Dockerfile and buildspec to use cached images

### GitHub Actions

When GitHub Actions deploys:

1. Workflow passes GitHub Secrets as environment variables
2. Pulumi reads them and creates the same infrastructure
3. CodeBuild pulls `debian:bookworm-slim` through ECR cache

## Verification

After deployment, verify the cache is working:

```bash
# Check if pull-through cache rule was created
aws ecr describe-pull-through-cache-rules --region us-east-2

# Check for the cached repository (after first build)
aws ecr describe-repositories \
  --repository-names docker-hub/library/debian \
  --region us-east-2
```

## Cost Impact

With Docker Hub caching enabled:

- **Storage**: ~$0.04/month (400 MB across 5 cached images)
- **Savings**: $0.18 - $1.50/month (faster builds = less CodeBuild time)
- **Net benefit**: Positive ROI from day one

Within AWS free tier (first year): effectively **$0.00** additional cost

## Troubleshooting

### Credentials Not Working

If pull-through cache isn't created:

```bash
# Check if env vars are set
echo $DOCKER_HUB_USERNAME
echo $DOCKER_HUB_TOKEN

# Check Pulumi outputs
pulumi stack output docker_hub_cache_prefix

# Check AWS Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id ecr-pullthroughcache/docker-hub \
  --region us-east-2
```

### Removing Pull-Through Cache

To disable caching:

1. Remove or comment out credentials from `.env`
2. Run `pulumi up` - cache resources will be removed
3. Builds will fall back to pulling directly from Docker Hub

### Updating Credentials

To rotate your Docker Hub token:

1. Create new token in Docker Hub
2. Update `.env` file with new token
3. Run `./scripts/setup-docker-credentials.sh` to sync to GitHub
4. Run `pulumi up` to update AWS Secrets Manager

## Security Notes

- `.env` file is gitignored - never commit it
- Docker Hub tokens should have **read-only** permissions
- GitHub Secrets are encrypted and only accessible to workflows
- AWS Secrets Manager encrypts credentials at rest
- Free Docker Hub accounts work but have rate limits (no issue when authenticated)

## Optional: GitHub Secrets Management

### List all secrets

```bash
gh secret list
```

### Set secrets manually

```bash
gh secret set DOCKER_HUB_USERNAME
gh secret set DOCKER_HUB_TOKEN
```

### Delete secrets

```bash
gh secret delete DOCKER_HUB_USERNAME
gh secret delete DOCKER_HUB_TOKEN
```

## Next Steps

After setup is complete:

1. Monitor build times in CodeBuild console
2. Check ECR console for cached images
3. Review cost savings in AWS Cost Explorer
4. Consider using for other base images (python, node, etc.)

## Additional Resources

- [AWS ECR Pull Through Cache Documentation](https://docs.aws.amazon.com/AmazonECR/latest/userguide/pull-through-cache.html)
- [Docker Hub Access Tokens](https://docs.docker.com/security/for-developers/access-tokens/)
- [GitHub CLI Secrets](https://cli.github.com/manual/gh_secret)
