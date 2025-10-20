# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

knock-lambda is a serverless AWS Lambda function that converts Adobe ACSM files to DRM-free PDF/EPUB ebooks. It packages the Knock ACSM converter (C++) as a container-based Lambda function with automated deployment via Pulumi.

**Key Features:**
- Container-based AWS Lambda function with HTTP API endpoint
- Automated build via AWS CodeBuild (no local Docker required)
- Infrastructure as Code with Pulumi
- S3 storage for output files and device credentials
- Comprehensive pytest-based test suite

## Architecture

### Components

- **knock**: Main C++ application that converts ACSM files (in `knock/` directory)
- **libgourou**: Core Adobe ADEPT DRM processing library (in `deps/libgourou/`)
- **uPDFParser**: PDF parsing library, dependency of libgourou (in `deps/uPDFParser/`)
- **Lambda Handler**: Python handler that invokes Knock binary (in `infrastructure/lambda/handler.py`)
- **Infrastructure**: Pulumi code for AWS deployment (in `infrastructure/__main__.py`)

### Deployment Flow

```
Local Source → S3 Bucket → CodeBuild → ECR → Lambda Function
                              ↓
                         Docker Build
                         (CMake + C++)
```

## Build System Commands

### Local Build (for testing)

**Primary Build Command:**
```bash
python3 build_container.py
```
- Uses local dependencies from `deps/` directory (no network required)
- Builds Knock binary using CMake
- Outputs to `./build-output/knock`
- Dynamic linking for Lambda container compatibility

**Legacy Build (for standalone binaries):**
```bash
python3 build.py
```
- Clones dependencies from git (requires network)
- Builds static binary at `./knock/knock`
- Use for creating portable standalone binaries

### Container Build (for Lambda deployment)

**Via Pulumi (recommended):**
```bash
cd infrastructure
pulumi up
```
- Automatically uploads source to S3
- Triggers CodeBuild to build Docker image
- Deploys Lambda function with new image
- No local Docker required

**Local Docker Build (for testing):**
```bash
docker build -f infrastructure/lambda/Dockerfile -t knock-lambda .
```
- Builds the Lambda container locally
- Useful for testing before deployment
- Requires Docker installed

### Clean Build
```bash
# Remove local build artifacts
rm -rf ~build build-output
```

## Key Build Configuration

- **Linking**: 
  - Static linking by default (standalone binaries)
  - Dynamic linking for Lambda containers (set via `-DBUILD_STATIC=OFF`)
- **Version tracking**: Knock version 79 (3.0.79)
- **Install location**: `./build-output/knock` (via `build_container.py`)
- **Upstream fork**: Uses Alvin-He's fork since original BentonEdmondson repo is offline
- **Dependencies**: Pre-extracted in `deps/` directory (committed to git)

## Dependencies

### Build-time Dependencies
- build-essential (gcc, g++, make)
- cmake (≥3.14)
- libssl-dev, libcurl4-openssl-dev, zlib1g-dev

### Python Dependencies (for infrastructure)
- pulumi (≥3.0.0)
- pulumi-aws (≥7.0.0)
- pulumi-command (≥1.0.0)
- pytest (for testing)

### AWS Resources (created by Pulumi)
- ECR repository (container images)
- CodeBuild project (builds Docker images)
- Lambda function (processes ACSM files)
- S3 buckets (source, output, device credentials)
- IAM roles and policies

## Project Structure

```
knock-lambda/
├── infrastructure/               # Pulumi infrastructure code
│   ├── __main__.py              # Main infrastructure definition
│   ├── config.py                # Configuration constants
│   ├── lambda/                  # Lambda function
│   │   ├── handler.py           # Python handler
│   │   ├── Dockerfile           # Container definition
│   │   └── requirements.txt     # Lambda Python deps
│   └── README.md
├── deps/                         # Local C++ dependencies (committed)
│   ├── libgourou/               # Adobe DRM library
│   │   ├── CMakeLists.txt       # Build config
│   │   ├── include/, src/
│   │   └── utils/
│   └── uPDFParser/              # PDF parser
│       ├── CMakeLists.txt       # Build config
│       └── include/, src/
├── knock/                        # Knock application
│   ├── src/knock.cpp            # Main C++ code
│   └── CMakeLists.txt
├── config/                       # Legacy CMake configs (for reference)
├── assets/                       # Source tarballs
│   └── sources/
│       ├── libgourou.tar.gz
│       └── uPDFParser.tar.gz
├── tests/                        # Test suite
│   ├── test_lambda.py           # Main pytest tests
│   ├── test_advanced.py         # Advanced tests
│   ├── conftest.py              # Pytest fixtures
│   └── shell/                   # Legacy shell tests
├── docs/                         # Additional documentation
├── build_container.py            # Local build script (new)
├── build.py                      # Legacy build script
├── CMakeLists.txt               # Top-level CMake config
├── pyproject.toml               # Python dependencies
└── README.md
```

## Development Notes

### Local Development

1. **Install Python dependencies:**
   ```bash
   uv sync
   uv shell
   ```

2. **Build locally:**
   ```bash
   python3 build_container.py
   ```

3. **Test locally:**
   ```bash
   pytest tests/ -m "not real_acsm"
   ```

4. **Deploy to AWS:**
   ```bash
   cd infrastructure
   pulumi up
   ```

### Important Paths

- **Dependencies**: `deps/libgourou/` and `deps/uPDFParser/` (not `~checkout/`)
- **Build output**: `build-output/knock` (not `knock/knock`)
- **Lambda handler**: `infrastructure/lambda/handler.py`
- **Dockerfile**: `infrastructure/lambda/Dockerfile`

### CMake Configurations

- Top-level `CMakeLists.txt` references `deps/` directory
- Each dependency has its own `CMakeLists.txt` in its directory
- Static vs dynamic linking controlled by `BUILD_STATIC` flag
- Build artifacts isolated in `~build/` (gitignored)

### Testing Strategy

- **Unit tests**: Use pytest with fixtures in `conftest.py`
- **Real ACSM tests**: Marked with `@pytest.mark.real_acsm` to avoid download limits
- **Safe tests**: Use `dummy_acsm_content` fixture
- **Integration tests**: Test deployed Lambda via HTTP API

## Common Issues & Solutions

### "Source directory not found"

**Problem**: `deps/` directory missing or incomplete

**Solution**:
```bash
mkdir -p deps
tar -xzf assets/sources/libgourou.tar.gz -C deps/
tar -xzf assets/sources/uPDFParser.tar.gz -C deps/
cp config/libgourou/CMakeLists.txt deps/libgourou/
cp config/uPDFParser/CMakeLists.txt deps/uPDFParser/
```

### "E_GOOGLE_DEVICE_LIMIT_REACHED"

**Problem**: Adobe device activation limit reached or ACSM file expired

**Solution**:
1. Get a fresh ACSM file from Google Books or Internet Archive
2. Reset device credentials:
   ```bash
   BUCKET=$(cd infrastructure && pulumi stack output device_credentials_bucket)
   aws s3 rm s3://$BUCKET/credentials/ --recursive --no-cli-pager
   ```

See [docs/ACSM_DEVICE_LIMITS.md](docs/ACSM_DEVICE_LIMITS.md) for details.

### "Lambda function not found"

**Problem**: Stack not deployed or deployment failed

**Solution**:
```bash
cd infrastructure
pulumi up
```

### "CodeBuild failed"

**Problem**: Build errors in AWS CodeBuild

**Solution**:
1. Check CloudWatch logs: `pulumi stack output codebuild_project_name`
2. Test build locally: `python3 build_container.py`
3. Verify `deps/` directory is committed to git

## Testing Commands

### Run Tests

```bash
# Install test dependencies
uv pip install -e ".[dev]"

# Run safe tests (recommended)
pytest tests/ -m "not real_acsm"

# Run specific test
pytest tests/test_lambda.py::TestLambdaBasic::test_health_check -v

# Run all tests (WARNING: uses real ACSM)
pytest tests/
```

### Manual Testing

```bash
# Test basic connectivity
python tests/manual_test.py basic

# Test with ACSM file
python tests/manual_test.py asset
```

## AWS Configuration

### Required AWS Permissions

- ECR: Create/manage repositories
- Lambda: Create/update functions
- S3: Create/manage buckets
- IAM: Create roles and policies
- CodeBuild: Create/run build projects
- CloudWatch: Create log groups

### Pulumi Configuration

```bash
# Set AWS region
pulumi config set aws:region us-east-1

# Set custom timeout (optional)
pulumi config set lambda_timeout 600

# View all config
pulumi config
```

See [infrastructure/CONFIG.md](infrastructure/CONFIG.md) for all options.

## Reference Documentation

- **[README.md](README.md)** - Project overview and quick start
- **[SIMPLIFIED_BUILD.md](SIMPLIFIED_BUILD.md)** - Build system details
- **[infrastructure/README.md](infrastructure/README.md)** - Deployment guide
- **[tests/QUICK_START.md](tests/QUICK_START.md)** - Testing quick start
- **[docs/ACSM_DEVICE_LIMITS.md](docs/ACSM_DEVICE_LIMITS.md)** - Troubleshooting device limits
