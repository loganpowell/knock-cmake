#!/bin/bash
set -e

# Load platform compatibility layer
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/platform-compat.sh"

log_info "Resetting Device Credentials"
echo "================================="
echo ""
echo "This will clear the existing Adobe device credentials from S3"
echo "and force the Lambda to generate fresh credentials on the next run."
echo ""

# Get the device credentials bucket name from Pulumi
log_info "Getting bucket name from Pulumi..."
BUCKET_NAME=$(cd infrastructure && pulumi stack output device_credentials_bucket 2>/dev/null)

if [ -z "$BUCKET_NAME" ]; then
    echo "❌ Error: Could not get device_credentials_bucket from Pulumi"
    echo "   Make sure you're in the project root directory and Pulumi is configured"
    exit 1
fi

echo "✓ Bucket name: $BUCKET_NAME"
echo ""

# Check if credentials exist in S3
echo "🔍 Checking for existing credentials..."
CREDENTIALS_EXIST=$(aws s3 ls "s3://${BUCKET_NAME}/credentials/" --no-cli-pager 2>/dev/null | wc -l || echo "0")

if [ "$CREDENTIALS_EXIST" -eq 0 ]; then
    echo "ℹ️  No credentials found in S3 - bucket is already empty"
    exit 0
fi

echo "Found existing credentials:"
aws s3 ls "s3://${BUCKET_NAME}/credentials/" --no-cli-pager
echo ""

# Delete the credentials
echo "🗑️  Deleting device credentials from S3..."
aws s3 rm "s3://${BUCKET_NAME}/credentials/" --recursive --no-cli-pager

echo ""
echo "✅ Device credentials cleared successfully!"
echo ""
echo "Next steps:"
echo "1. Run your tests again: ./tests/run_tests.sh"
echo "2. The Lambda will automatically generate fresh credentials on the next invocation"
echo "3. The new credentials will be saved to S3 for future use"
