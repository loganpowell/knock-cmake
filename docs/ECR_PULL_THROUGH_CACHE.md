# ECR Pull-Through Cache Implementation

This document explains the pull-through cache implementation for the Knock Lambda project.

## ⚠️ Important Update - Docker Hub Limitation

**As of October 2025**, AWS requires Docker Hub credentials (stored in AWS Secrets Manager) for pull-through cache, even for public images. Due to this requirement:

- ✅ **Public ECR cache is enabled** (for AWS-provided images like Lambda base images)
- ❌ **Docker Hub cache is NOT enabled** (requires additional setup with Secrets Manager)
- 📝 **Current setup**: Direct pulls from Docker Hub (no cache for debian:bookworm-slim)

If you want to enable Docker Hub caching, see [Enabling Docker Hub Cache](#enabling-docker-hub-cache-optional) below.

## TL;DR - Cost Impact (Updated)

**Bottom Line**: Public ECR cache is enabled for future use; Docker Hub cache requires credentials.

- **Current Cost**: $0.00 additional (public ECR cache within free tier)
- **Current Savings**: Minimal (no Docker Hub cache yet)
- **Potential Savings**: $0.18 - $1.50/month if Docker Hub cache is enabled
- **Reliability**: Public ECR cache available for AWS Lambda base images

See [Detailed Cost Analysis](#detailed-cost-analysis) below for complete breakdown.

## What is Pull-Through Cache?

ECR Pull-Through Cache Rules allow you to cache images from external registries (like Docker Hub) in your ECR repositories. This provides:

- **Faster builds**: Cached images are pulled from ECR instead of external registries
- **Reduced costs**: Lower data transfer costs for frequently used images
- **Better reliability**: Reduced dependency on external registry availability
- **Bandwidth savings**: Especially beneficial in AWS environments

## Implementation Details

### 1. Pull-Through Cache Rules

We've configured a cache rule for AWS Public ECR in `infrastructure/__main__.py`:

```python
# Cache rule for public ECR repositories (like AWS base images)
# This is useful if you want to use AWS Lambda base images in the future
public_ecr_cache_rule = aws.ecr.PullThroughCacheRule(
    "public-ecr-cache",
    ecr_repository_prefix="ecr-public",
    upstream_registry_url="public.ecr.aws"
)
```

**Note**: Docker Hub cache is not enabled by default due to authentication requirements.

### 2. Current Dockerfile

The Dockerfile currently pulls directly from Docker Hub:

```dockerfile
FROM debian:bookworm-slim AS builder
```

No build arguments or ECR registry URLs are needed for the current implementation.

### 3. BuildSpec

The buildspec logs into ECR for pushing your built images:

```yaml
- ECR_REGION=$(echo $ECR_REPOSITORY_URI | cut -d. -f4)
- aws ecr get-login-password --region $ECR_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI
```

## How It Works (Public ECR Only)

1. **Public ECR Cache**: Available for AWS-provided images from public.ecr.aws
2. **Docker Hub**: Images pulled directly from Docker Hub (no caching currently)
3. **Future Option**: Can enable Docker Hub cache with credentials setup

## Enabling Docker Hub Cache (Optional)

If you want to enable Docker Hub caching for faster builds, you'll need to set up authentication:

### Step 1: Create Docker Hub Access Token

1. Log into Docker Hub (https://hub.docker.com)
2. Go to Account Settings → Security → New Access Token
3. Create a token with "Public Repo Read-only" permissions
4. Save the token securely

### Step 2: Store Credentials in AWS Secrets Manager

```bash
aws secretsmanager create-secret \
    --name ecr-pullthroughcache/docker-hub \
    --description "Docker Hub credentials for ECR pull-through cache" \
    --secret-string '{"username":"YOUR_DOCKER_USERNAME","accessToken":"YOUR_ACCESS_TOKEN"}' \
    --region us-east-2
```

### Step 3: Update Pulumi Code

Add the Docker Hub cache rule with credentials:

```python
# Get the secret ARN
docker_hub_secret = aws.secretsmanager.get_secret(
    name="ecr-pullthroughcache/docker-hub"
)

# Create Docker Hub pull-through cache with authentication
docker_hub_cache_rule = aws.ecr.PullThroughCacheRule(
    "docker-hub-cache",
    ecr_repository_prefix="docker-hub",
    upstream_registry_url="registry-1.docker.io",
    credential_arn=docker_hub_secret.arn
)
```

### Step 4: Update Dockerfile

```dockerfile
ARG ECR_REGISTRY_URL=docker.io
FROM ${ECR_REGISTRY_URL}/library/debian:bookworm-slim AS builder
```

### Step 5: Update BuildSpec

```yaml
- ECR_ACCOUNT_ID=$(echo $ECR_REPOSITORY_URI | cut -d. -f1 | cut -d/ -f3)
- ECR_REGISTRY_URL="$ECR_ACCOUNT_ID.dkr.ecr.$ECR_REGION.amazonaws.com/docker-hub"
- docker build --build-arg ECR_REGISTRY_URL=$ECR_REGISTRY_URL ...
```

**Cost**: Free Docker Hub account works, but rate limits may apply. Pro account ($5/month) removes limits.

## Image Paths

With pull-through cache enabled, your images are accessed via:

- **Original**: `debian:bookworm-slim`
- **Cached**: `{account-id}.dkr.ecr.{region}.amazonaws.com/docker-hub/library/debian:bookworm-slim`

## Benefits for Your Project (Current State)

1. **Future-Ready**: Public ECR cache is configured for AWS Lambda base images
2. **No Additional Cost**: Public ECR cache is within free tier
3. **Optional Enhancement**: Docker Hub cache can be enabled if desired
4. **Flexibility**: Can switch to AWS Lambda base images with zero infrastructure changes

## Monitoring

You can monitor public ECR cache usage via:

- AWS Console: ECR → Repositories → Look for `ecr-public/` repositories
- CLI: `aws ecr describe-repositories --region us-east-2`
- Pulumi output: `public_ecr_cache_prefix`

### Cost Monitoring Commands

Check your actual ECR costs and usage:

```bash
# Check all ECR repositories
aws ecr describe-repositories --region us-east-2 \
  --query 'repositories[*].[repositoryName,repositoryUri]' \
  --output table

# If you enable Docker Hub cache, check cached images:
# aws ecr list-images --repository-name docker-hub/library/debian --region us-east-2
```

### Setting Up Cost Alerts

To monitor if costs exceed expectations, create a CloudWatch alarm:

```bash
# Alert if monthly ECR costs exceed $1
aws cloudwatch put-metric-alarm \
  --alarm-name ecr-cost-alert \
  --alarm-description "Alert if ECR costs exceed $1/month" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 1.0 \
  --comparison-operator GreaterThanThreshold
```

## Alternative Approaches

### Option 1: Current Implementation (Debian + Manual Runtime)

- ✅ Full control over environment
- ✅ Matches build environment exactly
- ❌ Larger image size
- ❌ Manual Lambda runtime setup

### Option 2: AWS Lambda Base Images (see Dockerfile.lambda-base)

- ✅ Optimized for Lambda
- ✅ Smaller cold start times
- ✅ Pre-configured runtime
- ❌ Less control over base environment
- ❌ May require GLIBC compatibility testing

## Detailed Cost Analysis

### AWS Free Tier (First 12 Months)

- **ECR Storage**: 500 MB/month FREE
- **Data Transfer**: 100 GB/month OUT to internet FREE
- **Data Transfer**: Unlimited IN from internet FREE

### ECR Pull-Through Cache Costs

#### Storage Costs (After Free Tier)

- **Rate**: $0.10 per GB/month
- **Base Image Size**: ~80 MB (debian:bookworm-slim compressed)
- **Monthly Storage**: 80 MB × $0.10/GB = **$0.008/month**
- **With 5 cached images**: 400 MB × $0.10/GB = **$0.040/month**

#### Data Transfer Costs

**Scenario 1: Without Pull-Through Cache (Current)**

- Pulling from Docker Hub to AWS: FREE (inbound traffic)
- Docker Hub rate limits: 200 pulls/6hrs (anonymous), 100 pulls/6hrs if limited
- Risk of hitting rate limits in CI/CD

**Scenario 2: With Pull-Through Cache (Proposed)**

- First pull from Docker Hub: FREE (cached to ECR)
- Subsequent pulls from ECR (within AWS): FREE (same region)
- Cross-region pulls from ECR: $0.01 per GB

### Build Cost Comparison

Assuming your build frequency based on config (CodeBuild):

- **Build Compute**: BUILD_GENERAL1_MEDIUM @ $0.005/minute
- **Average Build Time**: ~5-10 minutes (based on your buildspec)
- **Builds per Day**: Estimated 2-5 (development workflow)

#### Monthly Build Costs (Conservative Estimate: 3 builds/day × 30 days)

**Without Cache:**

```
Base image pull time: ~30-60 seconds (80MB from Docker Hub)
Build compute: 90 builds × 8 min × $0.005/min = $3.60/month
Risk: Rate limit delays or failures
```

**With Cache:**

```
Base image pull time: ~5-15 seconds (from ECR, same region)
Build compute: 90 builds × 7.5 min × $0.005/min = $3.38/month
ECR storage: $0.04/month (5 images cached)
Total: $3.42/month

Savings: $0.18/month in compute + reduced failure risk
```

### Cost Breakdown Summary

| Component         | Without Cache | With Cache   | Difference    |
| ----------------- | ------------- | ------------ | ------------- |
| CodeBuild Compute | $3.60/mo      | $3.38/mo     | -$0.22/mo     |
| ECR Storage       | $0            | $0.04/mo     | +$0.04/mo     |
| Data Transfer     | $0            | $0           | $0            |
| Rate Limit Risk   | Medium        | None         | 🔒            |
| **Total**         | **$3.60/mo**  | **$3.42/mo** | **-$0.18/mo** |

### Hidden Benefits (Non-Monetary)

1. **Reliability**: No Docker Hub outages or rate limits affecting builds
2. **Speed**: 50-75% faster base image pulls (ECR regional performance)
3. **Consistency**: Guaranteed image availability for your account
4. **Security**: Images scanned by ECR (if enabled) before use

### Cost at Scale

If you scale to CI/CD with more frequent builds:

**10 builds/day (300/month):**

- Without cache: $12.00/mo (compute only)
- With cache: $11.25/mo (compute) + $0.04/mo (storage) = $11.29/mo
- **Savings: $0.71/month**

**20 builds/day (600/month):**

- Without cache: $24.00/mo (compute only)
- With cache: $22.50/mo (compute) + $0.04/mo (storage) = $22.54/mo
- **Savings: $1.46/month**

### Recommendation

**✅ Implement Pull-Through Cache** because:

1. **Net savings** even at low build frequency
2. **Minimal cost** (~$0.04/month for storage well within free tier)
3. **Significant reliability improvement** (priceless for production)
4. **Better performance** = faster development cycles
5. **Future-proof** for increased build frequency

### Free Tier Impact

Your ECR usage with pull-through cache:

- **Storage used**: ~400 MB (5 cached images)
- **Free tier**: 500 MB/month
- **Cost while in free tier**: **$0.00**
- **Cost after free tier**: **~$0.04/month**

The pull-through cache is essentially **FREE for the first year** and costs less than a penny per month thereafter.

### Visual Cost Comparison

```
Current Setup (No Cache):
┌─────────────────────────────────────────────┐
│ Monthly Cost: $3.60                         │
│                                             │
│ Docker Hub → CodeBuild                      │
│ [30-60s pull time per build]                │
│ ⚠️  Risk: Rate limits (200 pulls/6hrs)      │
└─────────────────────────────────────────────┘

With Pull-Through Cache:
┌─────────────────────────────────────────────┐
│ Monthly Cost: $3.42                         │
│ Savings: $0.18/month + reliability          │
│                                             │
│ ECR Cache → CodeBuild                       │
│ [5-15s pull time per build]                 │
│ ✅ No rate limits                           │
│ ✅ 3-4x faster pulls                        │
└─────────────────────────────────────────────┘
```

### Break-Even Analysis

The pull-through cache pays for itself through:

1. **Immediate**: Faster builds = lower compute costs
2. **Week 1**: Avoided Docker Hub rate limit issues
3. **Month 1**: Net savings on total infrastructure costs

**Time to ROI**: Immediate (day one savings)

## Next Steps

1. **Calculate Your Costs**: Run the cost calculator for your specific usage:

   ```bash
   ./scripts/calculate-cache-costs.sh
   ```

2. **Deploy**: Run `pulumi up` to apply the pull-through cache configuration

3. **Monitor**: Check ECR console for new repositories under `docker-hub/` prefix

4. **Optimize**: Consider using AWS Lambda base images for further optimization

5. **Expand**: Add more cache rules for other frequently used images

## Troubleshooting

If builds fail after implementing cache:

1. **Check IAM permissions**: Ensure CodeBuild role has ECR pull permissions
2. **Verify cache rules**: Check if pull-through cache rules are created correctly
3. **Fallback**: The Dockerfile can still be built without cache by omitting the build arg
4. **Manual pull**: Test cache by manually pulling the cached image path

## Security Considerations

- Pull-through cache only works with public repositories by default
- For private upstream registries, you need to configure credential ARNs
- Cached images still go through ECR vulnerability scanning if enabled
