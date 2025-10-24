# GitHub Actions CI/CD Setup for Pulumi

This document explains the Pulumi deployment workflow and how to access deployment outputs.

## Deployment Strategy

### Release-Based Deployments

The workflow triggers on **GitHub Releases** (not on every push):

- **Production (`main` stack)**: Create a release from the `main` branch
- **Development (`dev` stack)**: Create a release from the `dev` branch
- **Manual**: Use "Run workflow" button in GitHub Actions for ad-hoc deployments

**Why release-based?**

- Controlled, intentional deployments
- Semantic versioning integration
- Clear deployment history
- Prevents accidental infrastructure changes

### Creating a Release

```bash
# Via GitHub CLI
gh release create v1.0.0 --target main --title "Production v1.0.0" --notes "Release notes here"

# Or via GitHub UI
# Go to: Releases → Draft a new release → Choose tag and target branch → Publish
```

## Accessing Deployment Outputs

### Repository Variables (Recommended)

After each deployment, key outputs are saved as GitHub **repository variables** with branch prefixes:

**Naming Convention:**

- Main stack: `MAIN_FUNCTION_URL`, `MAIN_CODEBUILD_PROJECT_NAME`, etc.
- Dev stack: `DEV_FUNCTION_URL`, `DEV_CODEBUILD_PROJECT_NAME`, etc.

**Available variables:**

- `{BRANCH}_FUNCTION_URL` - Lambda function URL
- `{BRANCH}_CODEBUILD_PROJECT_NAME` - CodeBuild project name
- `{BRANCH}_LAMBDA_FUNCTION_NAME` - Lambda function name
- `{BRANCH}_ECR_REPOSITORY_URL` - ECR repository URL

**Access in workflows:**

```yaml
jobs:
  use-outputs:
    runs-on: ubuntu-latest
    steps:
      - name: Use main outputs
        run: |
          echo "Function URL: ${{ vars.MAIN_FUNCTION_URL }}"
          echo "CodeBuild: ${{ vars.MAIN_CODEBUILD_PROJECT_NAME }}"

      - name: Use dev outputs
        run: |
          echo "Function URL: ${{ vars.DEV_FUNCTION_URL }}"
```

**Access via CLI:**

```bash
# List all repository variables
gh variable list

# Get a specific variable
gh variable get MAIN_FUNCTION_URL
gh variable get DEV_FUNCTION_URL

# Use in scripts
FUNCTION_URL=$(gh variable get MAIN_FUNCTION_URL)
curl "$FUNCTION_URL"
```

### Job Summary

Each deployment also creates a detailed Job Summary visible in the Actions run UI with:

- Stack outputs table
- Quick links to Lambda function and Pulumi Console
- Deployment metadata

## Branch-to-Stack Mapping

The workflow automatically maps Git branches to Pulumi stacks:

- `main` branch → `main` stack (production)
- `dev` branch → `dev` stack (development/staging)
- Future branches can have their own stacks as needed

## Required Setup Steps

### 1. Migrate to Pulumi Cloud (Recommended)

**Why?** The current local file backend (`file://~`) doesn't work for CI/CD or team collaboration.

**Steps:**

1. **Create a Pulumi Cloud account** (free tier available)

   - Visit: https://app.pulumi.com
   - Sign up with your GitHub account

2. **Login to Pulumi Cloud locally**

   ```bash
   cd infrastructure
   pulumi login
   ```

3. **Migrate existing stacks**

   For the `dev` stack:

   ```bash
   pulumi stack select dev
   pulumi stack export --file dev-stack.json
   pulumi login  # Login to Pulumi Cloud if not already
   pulumi stack init dev
   pulumi stack import --file dev-stack.json
   ```

   For the `main` stack:

   ```bash
   pulumi stack select main
   pulumi stack export --file main-stack.json
   pulumi stack init main
   pulumi stack import --file main-stack.json
   ```

4. **Clean up local state** (after verifying migration)
   ```bash
   rm -rf ~/.pulumi/stacks
   rm dev-stack.json main-stack.json
   ```

### 2. Alternative: Use AWS S3 Backend

If you prefer to self-host your state:

1. **Create an S3 bucket for Pulumi state**

   ```bash
   aws s3 mb s3://knock-lambda-pulumi-state --region us-east-2
   aws s3api put-bucket-versioning \
     --bucket knock-lambda-pulumi-state \
     --versioning-configuration Status=Enabled
   ```

2. **Login to S3 backend**

   ```bash
   cd infrastructure
   pulumi login s3://knock-lambda-pulumi-state
   ```

3. **Migrate stacks** (same process as Pulumi Cloud above)

### 3. Configure GitHub Secrets

Add these secrets to your GitHub repository:

- Go to: `https://github.com/loganpowell/knock-lambda/settings/secrets/actions`

**Required Secrets:**

1. **`PULUMI_ACCESS_TOKEN`**

   - If using Pulumi Cloud:
     - Go to https://app.pulumi.com/account/tokens
     - Create a new access token
     - Copy the token value
   - If using S3:
     - Set to empty string or omit (you'll use AWS credentials instead)

2. **`AWS_ACCESS_KEY_ID`**

   - Your AWS access key ID
   - Should have permissions to deploy Lambda, ECR, S3, IAM, etc.

3. **`AWS_SECRET_ACCESS_KEY`**
   - Your AWS secret access key

**Security Best Practice:**
Create a dedicated IAM user for GitHub Actions with minimal required permissions.

### 4. Update Stack Configurations

Make sure both stacks have appropriate configurations:

```bash
# For main stack (production)
pulumi stack select main
pulumi config set aws:region us-east-2
pulumi config set lambda_timeout 900
pulumi config set lambda_memory 1024
pulumi config set output_bucket_lifecycle_days 7  # Keep prod outputs longer
pulumi config set ecr_image_retention 10  # Keep more images in prod

# For dev stack (development)
pulumi stack select dev
pulumi config set aws:region us-east-2
pulumi config set lambda_timeout 900
pulumi config set lambda_memory 1024
pulumi config set output_bucket_lifecycle_days 1  # Clean up dev outputs faster
pulumi config set ecr_image_retention 3  # Keep fewer images in dev
```

## How It Works

### On Pull Requests

- Runs `pulumi preview` to show what changes would be made
- Uses the **target branch** as the stack name
- Example: PR targeting `main` → previews `main` stack

### On Pushes to main/dev

- Runs `pulumi up` to deploy changes
- Uses the **current branch** as the stack name
- Example: Push to `main` → deploys `main` stack

### Workflow Features

- ✅ Automatic Python 3.11 setup
- ✅ Uses `uv` for fast dependency installation
- ✅ Configures AWS credentials
- ✅ Branch-based stack selection
- ✅ Preview on PRs, deploy on merge

## Testing the Workflow

After completing the setup:

1. **Create a test branch**

   ```bash
   git checkout -b test-ci
   ```

2. **Make a small change** (e.g., update a config value)

   ```bash
   cd infrastructure
   pulumi config set lambda_memory 2048
   git add Pulumi.dev.yaml
   git commit -m "test: increase lambda memory"
   git push origin test-ci
   ```

3. **Create a PR to `dev`**

   - The workflow will run `pulumi preview`
   - Check the Actions tab to see the preview

4. **Merge the PR**
   - The workflow will run `pulumi up`
   - Changes will be deployed to the `dev` stack

## Troubleshooting

### "error: could not detect current project"

- Make sure `work-dir: infrastructure` is set in the workflow
- The workflow needs to run from the `infrastructure` directory

### "error: failed to decrypt"

- Remove the `encryptionsalt` from `Pulumi.*.yaml` files
- Or set `PULUMI_CONFIG_PASSPHRASE` as a GitHub secret

### "No configured provider for aws"

- Ensure AWS credentials are properly configured in GitHub secrets
- Check that the IAM user has required permissions

## Next Steps

1. Complete the backend migration (Pulumi Cloud or S3)
2. Configure GitHub secrets
3. Test the workflow with a small PR
4. Document your specific deployment process for the team

## Resources

- [Pulumi GitHub Actions Guide](https://www.pulumi.com/docs/iac/guides/continuous-delivery/github-actions/)
- [Pulumi Cloud Console](https://app.pulumi.com)
- [Pulumi State Backends](https://www.pulumi.com/docs/iac/concepts/state-and-backends/)
