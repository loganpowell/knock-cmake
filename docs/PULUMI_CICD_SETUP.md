# Pulumi CI/CD Setup Summary

## ✅ What's Been Created

### 1. GitHub Actions Workflow

- **File**: `.github/workflows/pulumi.yml`
- **Features**:
  - Runs `pulumi preview` on pull requests
  - Runs `pulumi up` on pushes to `main` or `dev`
  - Automatically maps branches to stacks (`main` branch → `main` stack, `dev` branch → `dev` stack)
  - Uses Python 3.11 and `uv` for dependency management

### 2. Pulumi Stacks

- ✅ `main` stack created (for production deployments from `main` branch)
- ✅ `dev` stack exists (for development deployments from `dev` branch)

### 3. Migration Scripts

- **`scripts/migrate-to-pulumi-cloud.sh`**: Migrate to Pulumi Cloud (recommended)
- **`scripts/migrate-to-s3-backend.sh`**: Migrate to AWS S3 backend (self-hosted)

### 4. Documentation

- **`.github/workflows/README.md`**: Complete setup instructions and troubleshooting

## 🚀 Quick Start - Choose Your Path

### Option A: Pulumi Cloud (Recommended)

**Pros:**

- Free tier available
- Built-in secrets management
- State history and rollback
- Easiest to set up
- Team collaboration features

**Steps:**

1. Create account at https://app.pulumi.com
2. Run the migration script:
   ```bash
   ./scripts/migrate-to-pulumi-cloud.sh
   ```
3. Create a Pulumi access token at https://app.pulumi.com/account/tokens
4. Add secrets to GitHub:
   - `PULUMI_ACCESS_TOKEN` (from Pulumi Cloud)
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

### Option B: AWS S3 Backend

**Pros:**

- Self-hosted in your AWS account
- Full control over state data
- No external dependencies

**Steps:**

1. Run the migration script:
   ```bash
   ./scripts/migrate-to-s3-backend.sh
   ```
2. Update `.github/workflows/pulumi.yml` to add S3 login:
   ```yaml
   - name: Login to S3 Backend
     run: pulumi login s3://knock-lambda-pulumi-state
   ```
3. Add secrets to GitHub:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
4. Team members login with:
   ```bash
   pulumi login s3://knock-lambda-pulumi-state
   ```

## 📋 Current State

- ✅ Branch-based stack structure ready
- ✅ GitHub Actions workflow created
- ⏳ Backend migration needed (choose Pulumi Cloud or S3)
- ⏳ GitHub secrets configuration needed

## 🎯 Next Steps

1. **Choose your backend** (Pulumi Cloud or S3)
2. **Run the migration script**
3. **Configure GitHub secrets**
4. **Test the workflow** with a PR

## 🔧 How It Works

### Branch to Stack Mapping

```
git branch → pulumi stack
─────────────────────────
main       → main (production)
dev        → dev (development)
feature/*  → custom stacks (optional)
```

### Deployment Flow

```
PR opened → pulumi preview (show changes)
    ↓
PR merged → pulumi up (deploy changes)
    ↓
Resources created/updated in AWS
```

### Example Workflow

1. **Developer creates feature branch:**

   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/new-lambda-setting
   ```

2. **Developer makes changes:**

   ```bash
   cd infrastructure
   # Update code or config
   git add .
   git commit -m "feat: increase lambda memory"
   git push origin feature/new-lambda-setting
   ```

3. **Developer opens PR to `dev` branch:**

   - GitHub Actions runs `pulumi preview` against `dev` stack
   - Shows what changes would be made
   - Reviewer can see infrastructure changes

4. **PR is merged:**

   - GitHub Actions runs `pulumi up` on `dev` stack
   - Changes are deployed to development environment

5. **When ready for production:**
   - Open PR from `dev` to `main`
   - GitHub Actions runs `pulumi preview` against `main` stack
   - Merge PR to deploy to production

## 🔒 Security Notes

- Never commit `PULUMI_ACCESS_TOKEN` or AWS credentials
- Use GitHub secrets for all sensitive values
- Consider using OIDC for AWS authentication (more secure than access keys)
- The `encryptionsalt` in `Pulumi.*.yaml` files is safe to commit (it's not the passphrase)

## 🐛 Troubleshooting

See `.github/workflows/README.md` for detailed troubleshooting steps.

## 📚 Resources

- [Pulumi GitHub Actions Guide](https://www.pulumi.com/docs/iac/guides/continuous-delivery/github-actions/)
- [Pulumi State Backends](https://www.pulumi.com/docs/iac/concepts/state-and-backends/)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

## 🤝 Team Onboarding

When a new developer joins:

**If using Pulumi Cloud:**

```bash
pulumi login
cd infrastructure
pulumi stack ls  # Should see main and dev stacks
```

**If using S3:**

```bash
pulumi login s3://knock-lambda-pulumi-state
cd infrastructure
pulumi stack ls  # Should see main and dev stacks
```

## 📞 Need Help?

- Check `.github/workflows/README.md` for detailed instructions
- Review the migration scripts for step-by-step automation
- Test locally before pushing to ensure everything works

# Getting your PULUMI_CLOUD_ACCESS_TOKEN

Step-by-Step Guide

1. Create a Pulumi Cloud Account (if you don't have one)
   Go to: https://app.pulumi.com
   Sign up using your GitHub account (easiest) or email
   It's free for individuals and small teams
2. Create an Access Token
   Once logged in, go to: https://app.pulumi.com/account/tokens
   Or navigate: Click your profile → Settings → Access Tokens
   Click "Create token"
   Give it a descriptive name like GitHub Actions - knock-lambda
   Copy the token immediately (you won't be able to see it again!)
3. Add to GitHub Secrets
   Go to your repository: https://github.com/loganpowell/knock-lambda/settings/secrets/actions
   Click "New repository secret"
   Name: PULUMI_ACCESS_TOKEN
   Value: Paste the token you just copied
   Click "Add secret"

## Visual Path

```
1. https://app.pulumi.com
   ↓
2. Sign up/Login (use GitHub for easy SSO)
   ↓
3. Click your profile picture (top right)
   ↓
4. Settings → Access Tokens
   ↓
5. Create token → Copy immediately
   ↓
6. Go to GitHub repo → Settings → Secrets and variables → Actions
   ↓
7. New repository secret → Name: PULUMI_ACCESS_TOKEN
```

## Important Notes

- ⚠️ Save the token immediately - you can only see it once!
- 🔒 Never commit the token to your repository
- 🔄 You can create multiple tokens (e.g., one for CI/CD, one for local use)
- 🗑️ You can revoke tokens at any time from the same page

### Then Run Migration

After creating your account:

```bash
cd /Users/logan.powell/Documents/projects/logan/knock-lambda
./scripts/migrate-to-pulumi-cloud.sh
```

The script will:

Prompt you to login to Pulumi Cloud (opens browser)
Export your existing dev and main stacks
Import them into Pulumi Cloud
Verify the migration
Need any help with the migration process?
