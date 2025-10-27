# Knock Lambda

**A serverless AWS Lambda function for converting Adobe ACSM files to DRM-free PDF/EPUB ebooks.**

This project packages the [Knock](https://github.com/BentonEdmondson/knock) ACSM-to-ebook converter as a container-based AWS Lambda function with automated deployment via Pulumi. It provides an HTTP API endpoint for converting ACSM files without requiring local installation of Adobe Digital Editions or Wine.

## 🚀 What It Does

- **Input**: ACSM file (Adobe Content Server Message) via HTTP POST request
- **Output**: DRM-free PDF or EPUB file stored in S3 with a pre-signed download URL (**1 hour expiration**)
- **Runtime**: Serverless AWS Lambda with container image deployment
- **Build**: Automated via AWS CodeBuild (no local Docker required)

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Documentation](#-documentation)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [License](#-license)

## 🎯 Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) - Python package manager
- [Pulumi](https://www.pulumi.com/docs/get-started/install/) - Infrastructure as Code
- [Pulumi ESC CLI](https://www.pulumi.com/docs/esc/cli/) - For environment management (`pulumi plugin install esc`)
- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate credentials
- [GitHub CLI](https://cli.github.com/) - For GitHub Actions setup (optional)
- **Note**: Docker is NOT required locally - builds happen in AWS CodeBuild

### Initial Setup

For first-time setup or when onboarding new developers, run the comprehensive setup script:

> Note: Important infrastructure variable definitions are defined in [infrastructure/vars.py](infrastructure/vars.py)

The structure of the Pulumi deployment has three stacks:

1. `base` - for shared resources across environments
2. `main` - for production deployments
3. `dev` - for development/testing deployments

`base` resources are shared between both `main` and `dev` stacks.
`main` and `dev` are meant to correspond to branches in your GitHub repository (e.g., `main` branch uses `main` stack).

```bash
# Clone the repository using HTTPS
git clone https://github.com/loganpowell/knock-lambda.git
# or ssh
git clone git@github.com:loganpowell/knock-lambda.git

cd knock-lambda

# checkout the `dev` branch
git fetch origin dev:dev
git checkout dev

# Install dependencies
uv sync

# Run setup to configure ESC and optionally GitHub Actions
uv run setup
```

This interactive setup script will:

- **Configure Pulumi ESC** for centralized environment management
- **Set up AWS credentials** in ESC environment for local development
- **Configure Docker Hub credentials** in ESC environment
- **Optionally configure GitHub Actions** with repository secrets for CI/CD
- **Install Git hooks** for development workflow

**Security Model**:

- **Local Development**: Uses Pulumi ESC for convenient credential management
- **CI/CD Pipeline**: Uses OIDC authentication for passwordless AWS access + ESC for Docker Hub credentials
- **Pure ESC + OIDC**: No stored AWS credentials, secure token-based authentication

**For Local Development**: After running setup, your ESC environment will be automatically configured. The infrastructure will load credentials from ESC.

**For CI/CD**: GitHub Actions workflow uses OIDC roles for AWS authentication and ESC for Docker Hub credentials. Only `VARIABLE_EDITING_PAT` is stored as a GitHub secret.

### Deploy to AWS the first time

#### After completing `uv run setup`, you'll see the following guidance:

```bash
🔧 ESC Integration Status:
  • ESC Environment: default/knock-lambda-esc
  • Stack Architecture:
    - base:  Shared resources (OIDC, secrets, ECR cache)
    - dev:   Development environment
    - main:  Production environment

🎯 Stack Creation & Deployment:

  # First, create all three stacks (one-time setup):
---
pulumi stack init base
pulumi stack init dev
pulumi stack init main
---

# Then deploy in order:
# 1. Deploy base stack FIRST (uses local AWS credentials)
---
pulumi stack select base
esc run default/knock-lambda-esc -- pulumi up
---

# 2. Deploy environment stacks (esc inferred from Pulumi.<stack>.yaml 'environment')
---
pulumi stack select dev
pulumi up
---

---
pulumi stack select main
pulumi up
---

💡 Note: Base stack must be deployed before dev/main stacks

4️⃣ Git Hooks Setup
✅ Installed post-checkout hook (auto-switches Pulumi stack on branch change)
📋 Hook behavior:
  • git checkout dev  → pulumi stack select dev
  • git checkout main → pulumi stack select main
💡 Base stack: manually select with 'pulumi stack select base'

============================================================
🎉 Setup Complete!
============================================================

Summary of what was configured:
✅ Pulumi ESC environment set up
✅ Environment variables configured in ESC
✅ Pulumi integration with ESC verified
✅ Git hooks for development workflow

🔒 Security Benefits:
• All configuration centralized in Pulumi ESC
• No local credential files
• Access controlled through Pulumi Cloud
• Infrastructure automatically loads config from ESC
• Easy to share configuration with team members

�️  Multi-Stack Architecture:
• base:  Shared resources (OIDC providers, secrets, ECR cache)
• dev:   Development environment (references base stack)
• main:  Production environment (references base stack)

🚀 Next steps:

🏗️  First-time setup: Create the three stacks
  ---
  pulumi stack init base
  pulumi stack init dev
  pulumi stack init main
  ---

📦 Step 1: Deploy base stack (shared infrastructure)
  ---
  pulumi stack select base
  esc run default/knock-lambda-esc -- pulumi up --yes
  ---

🌍 Step 2: Deploy dev stack
  ---
  pulumi stack select dev
  pulumi up
  ---

🌐 Step 3: Deploy main stack
  ---
  pulumi stack select main
  pulumi up
  ---

💡 Pro Tips:
• Base stack must be deployed FIRST and only needs to be deployed once
• Dev/main stacks reference base stack outputs via StackReference
• Update shared resources by updating base stack only
• ESC environment is forker-friendly - no GitHub secrets needed!
• Update configuration anytime with: esc env edit
• Share configuration with team via Pulumi Cloud permissions

```

After deployment, you'll receive a Lambda function URL for making conversion requests.

---

You will need to add a single Github Action Secret for `PULUMI_ACCESS_TOKEN` to enable CI/CD deployments.

---

### Testing

#### Local Testing

```bash
# Run interactive E2E tests
uv run test
```

⚠️ **ACSM files have limited downloads per device.** Most tests use dummy data to preserve your download quota, but when you convert a real ACSM file, keep it because you may not be able to re-download it if you exceed your device limit.

#### Use the API

You can get the Lambda Function URL from Pulumi outputs:

```bash
# from either dev or main stack
pulumi stack output lambda_function_url
```

```bash
# Convert an ACSM file
curl -X POST <lambda_function_url> \
  -H "Content-Type: application/json" \
  -d '{"acsm_content": "<ACSM file content>"}'
```

## Trigger Github Actions Deployment

The github action configured for this project is set to trigger on releases and manual dispatches.

```bash
# for prereleases
gh release create v0.0.1-dev \
  --target dev \
  --title "Dev Release v0.0.1" \
  --notes "Testing new features" \
  --prerelease

# for production releases
gh release create v0.0.1 \
  --target main \
  --title "Production Release v0.0.1" \
  --notes "New features and bug fixes"
```

⚠️ The response includes presigned S3 download URL for converted file (valid for 1 hour). **You must download the file before the URL expires.**

## 📁 Project Structure

```
knock-lambda/
├── infrastructure/          # Pulumi infrastructure code
│   ├── __main__.py         # Main infrastructure definition
│   ├── lambda/             # Lambda function code
│   │   ├── handler.py      # Python Lambda handler
│   │   └── Dockerfile      # Container image definition
│   ├── README.md           # Deployment documentation
│   └── CONFIG.md           # Configuration options
├── deps/                    # Local C++ dependencies (committed)
│   ├── libgourou/          # Adobe DRM library
│   └── uPDFParser/         # PDF parser
├── knock/                   # Knock application source
│   ├── src/knock.cpp       # Main C++ implementation
│   └── CMakeLists.txt
├── config/                  # CMake build configurations
├── assets/                  # Source tarballs for dependencies
├── tests/                   # Test suite (pytest + shell scripts)
├── docs/                    # Additional documentation
├── build_container.py       # Local build script
├── CMakeLists.txt          # Top-level CMake config
├── pyproject.toml          # Python project configuration
└── README.md               # This file
```

## 🏗 Architecture

```
Build & Deployment Pipeline (CI/CD):
┌────────────────────────────────────────────────────────┐
│                    Build Pipeline                      │
│                                                        │
│ ┌─────────────┐    ┌─────────────┐    ┌──────────────┐ │
│ │   Source    │---▶│  CodeBuild  │---▶│     ECR      │ │
│ │   Bucket    │    │   Project   │    │  Repository  │ │
│ │ (S3 + Code) │    │             │    │              │ │
│ └─────────────┘    └─────────────┘    └──────────────┘ │
│        ▲                  │                            │
│        │                  ▼                            │
│ ┌─────────────┐    ┌─────────────┐                     │
│ │Pull-Through │    │  CloudWatch │                     │
│ │    Cache    │    │   (Logs)    │                     │
│ │(Docker Hub) │    │             │                     │
│ └─────────────┘    └─────────────┘                     │
└────────────────────────────────────────────────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │   Pulumi    │
                     │   (IaaC)    │
                     └─────────────┘
                            │
                            ▼
                 Updates Lambda Function
                 with new container image

Runtime Flow (User Requests):
 ┌──────────┐     ┌──────────────────┐     ┌─────────────┐
 │  Client  │----▶│  Lambda Function │----▶│  S3 Output  │
 │  (HTTP)  │     │    (Container)   │     │   Bucket    │
 └──────────┘     └──────────────────┘     └─────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │   Knock C++ +    │
                  │ Python Handler   │
                  └──────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │ S3 Device Credentials │
                │        Bucket         │
                └───────────────────────┘
```

See [infrastructure/lambda/README.md](infrastructure/lambda/README.md) for complete API documentation.

**Key Components:**

### Runtime Infrastructure

- **AWS Lambda**: Container-based function with Knock binary and Python handler
- **Lambda Function URL**: Public HTTP endpoint with CORS support
- **S3 Output Bucket**: Temporary storage for converted files with lifecycle policies
- **S3 Device Credentials Bucket**: Persistent storage for Adobe device credentials
- **CloudWatch Logs**: Lambda execution logs with configurable retention

### Build Pipeline

- **AWS CodeBuild**: Builds Docker images from source (no local Docker needed)
- **AWS ECR**: Private container registry with image lifecycle policies
- **S3 Source Bucket**: Stores application source code for CodeBuild
- **ECR Pull-Through Cache**: Caches public images (Docker Hub, AWS ECR Public)
- **Docker Hub Integration**: Optional credentials for private image access

### Security & Access

- **IAM Roles**: Least-privilege access for Lambda and CodeBuild
- **Secrets Manager**: Secure storage for Docker Hub credentials
- **S3 Bucket Policies**: Fine-grained access control for file operations

### Infrastructure Management

- **Pulumi**: Infrastructure as Code for automated deployment and updates
- **Cross-platform Scripts**: Shell utilities for build and deployment automation

**Build Process:**

1. **Local Development**: C++ dependencies (libgourou, uPDFParser) are pre-extracted in `deps/` directory
2. **Source Upload**: Pulumi uploads source code and tracks changes to trigger rebuilds
3. **Container Build**: CodeBuild uses CMake to build static Knock binary and packages with Lambda Python runtime
4. **Image Deployment**: Built image is pushed to ECR with digest-based versioning
5. **Lambda Update**: Function is updated with new container image and waits for deployment completion
6. **Monitoring**: CloudWatch logs capture execution details and errors

## 📚 Documentation

### Infrastructure & Deployment

- **[infrastructure/README.md](infrastructure/README.md)** - Complete deployment guide with Pulumi setup
- **[infrastructure/CONFIG.md](docs/CONFIG.md)** - Configuration options (timeouts, memory, regions)
- **[infrastructure/lambda/README.md](infrastructure/lambda/README.md)** - Lambda API reference and handler details
- **[infrastructure/PLATFORM_COMPAT.md](docs/PLATFORM_COMPAT.md)** - Cross-platform shell scripting utilities

### Build System

- **[build_container.py](build_container.py)** - Python script for building Knock binary locally
- **[CMakeLists.txt](CMakeLists.txt)** - Top-level CMake build configuration

### Dependencies

- **[deps/libgourou/README.md](deps/libgourou/README.md)** - Adobe ADEPT DRM processing library
- **[deps/uPDFParser/README.md](deps/uPDFParser/README.md)** - PDF parsing library

### Troubleshooting ACSM Errors

- **[docs/ACSM_DEVICE_LIMITS.md](docs/ACSM_DEVICE_LIMITS.md)** - Understanding and resolving device limit errors

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the test suite
5. Submit a pull request

**Development Guidelines:**

- Follow existing code style (Black for Python, comments for C++)
- Update documentation for user-facing changes
- Add tests for bug fixes and new features
- Test on both macOS and Linux when possible

## 📄 License

This project is licensed under GPLv3. The Knock application and its dependencies have the following licenses:

- **knock**: GPLv3
- **libgourou**: LGPL v3 or later
- **uPDFParser**: LGPL v3 or later

## 🙏 Credits

- **[Knock](https://github.com/BentonEdmondson/knock)** by Benton Edmondson - Original ACSM converter
- **[libgourou](https://forge.soutade.fr/soutade/libgourou)** by Grégory Soutadé - Adobe ADEPT implementation
- **[uPDFParser](https://forge.soutade.fr/soutade/uPDFParser)** by Grégory Soutadé - PDF parsing library
- **[knock-cmake](https://github.com/Alvin-He/knock-cmake)** by Alvin He - CMake build system

## 🔗 Links

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Pulumi Documentation](https://www.pulumi.com/docs/)
- [Knock Original Repository](https://github.com/BentonEdmondson/knock) (currently offline)
- [Adobe ADEPT Protocol](https://www.adobe.com/solutions/ebook/digital-editions.html)
