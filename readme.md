# Knock Lambda

**A serverless AWS Lambda function for converting Adobe ACSM files to DRM-free PDF/EPUB ebooks.**

This project packages the [Knock](https://github.com/BentonEdmondson/knock) ACSM-to-ebook converter as a container-based AWS Lambda function with automated deployment via Pulumi. It provides an HTTP API endpoint for converting ACSM files without requiring local installation of Adobe Digital Editions or Wine.

## 🚀 What It Does

- **Input**: ACSM file (Adobe Content Server Message) via HTTP POST request
- **Output**: DRM-free PDF or EPUB file stored in S3 with a pre-signed download URL
- **Runtime**: Serverless AWS Lambda with container image deployment
- **Build**: Automated via AWS CodeBuild (no local Docker required)

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Documentation](#-documentation)
- [Project Structure](#-project-structure)
- [Development](#-development)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [License](#-license)

## 🎯 Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) - Python package manager
- [Pulumi](https://www.pulumi.com/docs/get-started/install/) - Infrastructure as Code
- AWS CLI configured with appropriate credentials
- **Note**: Docker is NOT required locally - builds happen in AWS CodeBuild

### Deploy to AWS

```bash
# 1. Clone the repository
git clone <repo-url>
cd knock-lambda

# 2. Install dependencies
uv sync

# 3. Activate environment
uv shell

# 4. Navigate to infrastructure and deploy
cd infrastructure
pulumi up
```

After deployment, you'll receive a Lambda function URL for making conversion requests.

### Use the API

```bash
# Convert an ACSM file
curl -X POST https://random-lambda-uid.lambda-url.us-east-1.on.aws/ \
  -H "Content-Type: application/json" \
  -d '{"acsm_content": "<ACSM file content>"}'

# Response includes presigned S3 download URL for converted file (valid for 1 hour)
```

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

- **[SIMPLIFIED_BUILD.md](SIMPLIFIED_BUILD.md)** - Overview of the simplified local dependency build system
- **[build_container.py](build_container.py)** - Python script for building Knock binary locally
- **[CMakeLists.txt](CMakeLists.txt)** - Top-level CMake build configuration

### Testing

- **[tests/INTERACTIVE_CLI.md](tests/INTERACTIVE_CLI.md)** - Interactive test CLI with menu-driven ACSM file selection (`uv run itest`)
- **[tests/QUICK_START.md](tests/QUICK_START.md)** - Run tests in under 1 minute
- **[tests/TEST_GUIDE.md](tests/TEST_GUIDE.md)** - Complete pytest testing guide
- **[tests/README.md](tests/README.md)** - Legacy shell-based test documentation

### Dependencies

- **[deps/libgourou/README.md](deps/libgourou/README.md)** - Adobe ADEPT DRM processing library
- **[deps/uPDFParser/README.md](deps/uPDFParser/README.md)** - PDF parsing library

### Troubleshooting

- **[docs/ACSM_DEVICE_LIMITS.md](docs/ACSM_DEVICE_LIMITS.md)** - Understanding and resolving device limit errors

### Project Planning

- **[instructions.md](instructions.md)** - Original project architecture and planning notes (archived)
- **[WARP.md](WARP.md)** - AI assistant context and development guidelines

## 🛠 Development

### Local Build

Build the Knock binary locally for testing:

```bash
# Build using the container build script
python3 build_container.py

# Binary output location
./build-output/knock
```

See [SIMPLIFIED_BUILD.md](SIMPLIFIED_BUILD.md) for build system details.

### Docker Build

Test the Lambda container locally:

```bash
# Build container image
docker build -f infrastructure/lambda/Dockerfile -t knock-lambda .

# Run container locally (basic test)
docker run --rm knock-lambda
```

### Infrastructure Updates

```bash
cd infrastructure

# Preview changes
pulumi preview

# Deploy changes
pulumi up

# View outputs
pulumi stack output
```

### Testing

```bash
# Install test dependencies
uv pip install -e ".[dev]"

# Run safe tests (no real ACSM processing)
pytest tests/ -m "not real_acsm"

# Run all tests
pytest tests/
```

See [tests/QUICK_START.md](tests/QUICK_START.md) for testing guide.

## 🧪 Testing

This project includes comprehensive pytest-based tests:

- **Basic Tests**: Health checks, connectivity, parameter validation
- **ACSM Processing**: Actual file conversion (marked with `@pytest.mark.real_acsm`)
- **Load Tests**: Concurrent requests, memory stress, performance
- **Error Handling**: Invalid inputs, malformed JSON, HTTP methods

**Quick Test:**

```bash
# Run all tests except real ACSM processing (recommended)
pytest tests/ -m "not real_acsm"
```

⚠️ **ACSM files have limited downloads per device.** Most tests use dummy data to preserve your download quota.

See complete testing documentation:

- [tests/QUICK_START.md](tests/QUICK_START.md) - Get started in 1 minute
- [tests/TEST_GUIDE.md](tests/TEST_GUIDE.md) - Complete pytest guide
- [tests/README.md](tests/README.md) - Shell script tests (legacy)

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
