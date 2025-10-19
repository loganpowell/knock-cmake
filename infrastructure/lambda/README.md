# Knock Lambda Function

This directory contains the AWS Lambda function for processing ACSM files using the Knock binary.

## Files

- **`handler.py`**: Main Lambda handler that processes ACSM conversion requests
- **`Dockerfile`**: Container definition for building the Lambda runtime environment
- **`requirements.txt`**: Python dependencies required by the Lambda function
- **`__init__.py`**: Package initialization

## Lambda Function API

### Input Event Format

The Lambda function expects an event with one of the following formats:

#### Option 1: ACSM URL

```json
{
  "acsm_url": "https://example.com/path/to/file.acsm"
}
```

#### Option 2: ACSM Content

```json
{
  "acsm_content": "<ACSM file content as string>"
}
```

### Response Format

#### Success Response

```json
{
  "statusCode": 200,
  "body": {
    "message": "Conversion successful",
    "output_files": [
      {
        "filename": "converted_book.pdf",
        "s3_key": "converted/converted_book.pdf",
        "s3_url": "https://bucket.s3.amazonaws.com/converted/converted_book.pdf",
        "size_bytes": 1234567
      }
    ],
    "files_count": 1,
    "stdout": "Conversion output..."
  }
}
```

#### Error Response

```json
{
  "statusCode": 500,
  "body": {
    "error": "Error description",
    "error_type": "ExceptionType"
  }
}
```

## Environment Variables

- **`OUTPUT_BUCKET`**: S3 bucket name for storing converted files (optional)
- **`LAMBDA_TASK_ROOT`**: Lambda runtime directory (set automatically by AWS)
- **`PYTHONPATH`**: Python module search path (set automatically)

## Dependencies

The Lambda function requires:

- `boto3`: AWS SDK for Python (S3 operations)
- `botocore`: Core AWS SDK functionality

## Build Process

The Docker container build process:

1. Starts with AWS Lambda Python 3.11 base image
2. Installs system dependencies (build tools, libraries)
3. Copies the entire project source
4. Builds the Knock binary using `build.py`
5. Copies Lambda function code and installs Python dependencies
6. Sets the Lambda handler entry point

## Error Handling

The Lambda function includes comprehensive error handling for:

- Invalid input parameters
- Network issues when downloading ACSM files
- Knock binary execution failures
- S3 upload failures
- Timeout scenarios (10-minute limit)

## Logging

All operations are logged with appropriate detail levels for debugging and monitoring in CloudWatch Logs.
