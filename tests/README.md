# Knock Lambda Test Suite

This directory contains comprehensive tests for the Knock Lambda function that processes ACSM files and converts them to DRM-free PDFs/EPUBs.

## Test Files

### 🧪 `run_tests.sh` - Main Test Suite

The primary test script that validates the core functionality:

- **Health Check**: Basic connectivity and Lambda responsiveness
- **Parameter Validation**: Tests missing required parameters
- **ACSM Processing**: Tests actual ACSM file conversion using assets
- **Error Handling**: Tests invalid ACSM content handling
- **Load Testing**: Tests large request handling

**Usage:**

```bash
./tests/run_tests.sh
```

### 🔬 `advanced_tests.sh` - Advanced Test Scenarios

Extended testing for edge cases and performance:

- **Concurrent Requests**: Tests multiple simultaneous requests
- **Response Time**: Measures and validates response times
- **Memory Stress**: Tests large payload handling
- **Malformed Input**: Tests JSON parsing error handling
- **HTTP Methods**: Tests different HTTP methods (GET, PUT, DELETE, etc.)

**Usage:**

```bash
./tests/advanced_tests.sh
```

### 🛠️ `manual_test.sh` - Manual Testing Helper

Interactive testing tool for development and debugging:

**Usage:**

```bash
# Test basic connectivity
./tests/manual_test.sh basic

# Test with bundled asset file
./tests/manual_test.sh asset

# Test with custom ACSM file
./tests/manual_test.sh file /path/to/your/file.acsm

# Test with custom content
./tests/manual_test.sh content "Your custom ACSM content here"
```

## Test Data

The tests use ACSM files from the `assets/` directory:

- `assets/Princes_of_the_Yen-epub.acsm` - Sample ACSM file for testing

## API Testing

The tests validate the Lambda function API according to the User Workflow documented in `instructions.md`:

### Request Format

```json
{
  "acsm_content": "base64-encoded-acsm-content"
}
```

OR

```json
{
  "acsm_url": "https://example.com/file.acsm"
}
```

### Expected Response Format

**Success (200):**

```json
{
  "message": "Conversion successful",
  "output_files": [
    {
      "filename": "converted_file.pdf",
      "s3_key": "converted/converted_file.pdf",
      "s3_url": "https://bucket.s3.amazonaws.com/converted/converted_file.pdf",
      "size_bytes": 1234567
    }
  ],
  "files_count": 1,
  "stdout": "Knock conversion output..."
}
```

**Error (400/500):**

```json
{
  "error": "Error description",
  "stderr": "Error details...",
  "stdout": "Output details...",
  "return_code": 1
}
```

## Test Results

All test scripts save their results in the `tests/results/` directory:

- Response JSON files for analysis
- HTTP status codes and timing information
- Error logs for debugging

## Prerequisites

Before running tests, ensure:

1. **Lambda is deployed**: Run `./pumi up` from project root
2. **Environment configured**: Set up `.env` file (see below)
3. **Dependencies available**:
   - `curl` - For HTTP requests
   - `jq` - For JSON processing
   - `bc` - For calculations (advanced tests)
4. **Permissions**: Scripts have execute permissions

## Environment Setup

### Option 1: Automated Setup (Recommended)

```bash
# 1. Copy example environment file
cp .env.example .env

# 2. Edit .env and set your PULUMI_CONFIG_PASSPHRASE
nano .env  # or your preferred editor

# 3. Run setup script to get function URL
./tests/setup_env.sh

# 4. Run tests
./tests/run_tests.sh
```

### Option 2: Manual Setup

```bash
# Set passphrase in your shell
export PULUMI_CONFIG_PASSPHRASE='your_passphrase'

# Get function URL
FUNCTION_URL=$(./pumi stack output function_url)

# Run tests with environment
FUNCTION_URL="$FUNCTION_URL" ./tests/run_tests.sh
```

### Option 3: Interactive (will prompt for passphrase)

```bash
# Just run tests, will prompt for passphrase
./tests/run_tests.sh
```

## Environment

The tests automatically discover the Lambda function URL from the Pulumi stack:

```bash
FUNCTION_URL=$(./pumi stack output function_url)
```

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```bash
# Run basic tests
./tests/run_tests.sh

# Run comprehensive tests
./tests/run_tests.sh && ./tests/advanced_tests.sh
```

## Troubleshooting

### Common Issues

1. **"Could not get function URL"**

   - Ensure the stack is deployed: `./pumi up`
   - Check stack outputs: `./pumi stack output`

2. **Connection timeouts**

   - Lambda may be cold starting (first request after deployment)
   - Increase timeout in curl commands if needed

3. **JSON parsing errors**

   - Ensure `jq` is installed: `brew install jq`
   - Check response format in `tests/results/` files

4. **Permission errors**
   - Make scripts executable: `chmod +x tests/*.sh`

### Debug Mode

For verbose output, add debug flags to curl commands:

```bash
curl -v -X POST ...  # Verbose HTTP headers
curl -s -X POST ...  # Silent mode (default in scripts)
```

## Contributing

When adding new tests:

1. Follow the existing naming convention
2. Save results to `tests/results/` directory
3. Use colored output for better readability
4. Include both positive and negative test cases
5. Document the test purpose and expected outcomes
