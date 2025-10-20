# Test Guide

This directory contains pytest-based tests for the Knock Lambda function.

## Setup

Install test dependencies:

```bash
# Using uv (recommended)
uv pip install -e ".[dev]"

# Or using pip
pip install -e ".[dev]"
```

## Running Tests

### Run all tests (excluding real ACSM processing)
```bash
# Skip tests that use real ACSM file (recommended for regular testing)
pytest tests/ -m "not real_acsm"
```

### Run ALL tests including real ACSM processing
```bash
# WARNING: ACSM files have limited downloads per device
pytest tests/
```

### Run ONLY the real ACSM test
```bash
pytest tests/ -m real_acsm
```

### Run specific test files
```bash
# Main tests
pytest tests/test_lambda.py

# Advanced tests
pytest tests/test_advanced.py
```

### Run specific test classes or methods
```bash
# Run a specific test class
pytest tests/test_lambda.py::TestLambdaBasic

# Run a specific test method
pytest tests/test_lambda.py::TestLambdaBasic::test_health_check
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run with output capture disabled (see print statements)
```bash
pytest tests/ -s
```

### Run tests matching a pattern
```bash
# Run all tests with "acsm" in the name
pytest tests/ -k acsm

# Run all tests NOT matching a pattern
pytest tests/ -k "not memory"
```

## Test Structure

### `conftest.py`
Contains shared pytest fixtures:
- `project_root`: Project root directory
- `assets_dir`: Assets directory path
- `results_dir`: Test results directory
- `function_url`: Lambda function URL from Pulumi
- `acsm_file`: Path to test ACSM file
- `acsm_content`: Content of real ACSM file (requires `@pytest.mark.real_acsm`)
- `dummy_acsm_content`: Dummy ACSM-like content for testing without download limits

### `test_lambda.py`
Main test suite covering:
- **TestLambdaBasic**: Health checks and connectivity
- **TestLambdaACSM**: ACSM content processing
- **TestLambdaLoad**: Load and stress tests

### `test_advanced.py`
Advanced test scenarios:
- **TestConcurrency**: Concurrent request handling
- **TestPerformance**: Response time measurements
- **TestMemory**: Memory stress tests
- **TestErrorHandling**: Malformed JSON and HTTP method tests

## Manual Testing

For quick manual tests, use the `manual_test.py` script:

```bash
# Test basic connectivity
python tests/manual_test.py basic

# Test with bundled asset
python tests/manual_test.py asset

# Test with custom file
python tests/manual_test.py file /path/to/file.acsm

# Test with custom content
python tests/manual_test.py content "test content"
```

## Test Results

All test responses are saved to `tests/results/` for inspection.

## Important: ACSM File Download Limits

**WARNING:** The real ACSM file has a limited number of downloads per device. 

To prevent exhausting downloads:
- Most tests use `dummy_acsm_content` fixture for testing
- Only ONE test (`test_acsm_content_upload`) uses the real ACSM file
- This test is marked with `@pytest.mark.real_acsm`
- Run tests with `-m "not real_acsm"` to skip real ACSM processing

### Running tests safely:
```bash
# Regular testing (safe - no real ACSM processing)
pytest tests/ -m "not real_acsm"

# Only when you need to test real ACSM processing
pytest tests/test_lambda.py::TestLambdaACSM::test_acsm_content_upload -v
```

## Environment Variables

Tests automatically load environment variables from `.env` files:
- `{project_root}/.env` - Project-level environment
- `tests/.env` - Test-specific overrides (if present)

Required environment variable:
- `PULUMI_CONFIG_PASSPHRASE` - For accessing Pulumi stack outputs

## Troubleshooting

### Function URL not found
Make sure your stack is deployed:
```bash
./pumi up
```

### ACSM test file not found
Ensure the test asset exists at:
```
assets/The_Chemical_Muse-epub.acsm
```

### Timeout errors
Increase timeout values in test files or use:
```bash
pytest tests/ --timeout=120
```

## Legacy Shell Scripts

The original shell script tests are still available:
- `run_tests.sh` - Main test suite
- `advanced_tests.sh` - Advanced scenarios
- `manual_test.sh` - Manual testing helper

These can be used as a fallback, but pytest is now recommended.
