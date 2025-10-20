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
curl -X POST https://your-lambda-url.lambda-url.us-east-1.on.aws/ \
  -H "Content-Type: application/json" \
  -d '{"acsm_content": "<ACSM file content>"}'

# Response includes S3 download URL for converted file
```

See [infrastructure/lambda/README.md](infrastructure/lambda/README.md) for complete API documentation.

## 🏗 Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│    Lambda    │────▶│  S3 Output  │
│  (HTTP)     │     │  (Container) │     │   Bucket    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Knock C++  │
                    │    Binary    │
                    └──────────────┘
```

**Key Components:**

- **AWS Lambda**: Container-based function with Knock binary and Python handler
- **AWS CodeBuild**: Builds Docker images from source (no local Docker needed)
- **AWS ECR**: Stores container images
- **AWS S3**: Storage for output files and device credentials
- **Pulumi**: Infrastructure as Code for automated deployment

**Build Process:**

1. C++ dependencies (libgourou, uPDFParser) are pre-extracted in `deps/` directory
2. CMake builds static Knock binary from source
3. Docker packages binary with Lambda Python runtime
4. CodeBuild pushes image to ECR
5. Lambda function deployed with container image

## 📚 Documentation

### Infrastructure & Deployment

- **[infrastructure/README.md](infrastructure/README.md)** - Complete deployment guide with Pulumi setup
- **[infrastructure/CONFIG.md](infrastructure/CONFIG.md)** - Configuration options (timeouts, memory, regions)
- **[infrastructure/lambda/README.md](infrastructure/lambda/README.md)** - Lambda API reference and handler details
- **[infrastructure/PLATFORM_COMPAT.md](infrastructure/PLATFORM_COMPAT.md)** - Cross-platform shell scripting utilities

### Build System

- **[SIMPLIFIED_BUILD.md](SIMPLIFIED_BUILD.md)** - Overview of the simplified local dependency build system
- **[build_container.py](build_container.py)** - Python script for building Knock binary locally
- **[CMakeLists.txt](CMakeLists.txt)** - Top-level CMake build configuration

### Testing

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

