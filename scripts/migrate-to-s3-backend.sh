#!/usr/bin/env bash
#
# migrate-to-s3-backend.sh
#
# This script helps migrate your Pulumi stacks from local file backend to AWS S3.
# It will create an S3 bucket, export your current stacks, login to S3 backend, and import them.
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INFRA_DIR="$SCRIPT_DIR/../infrastructure"

# Configuration
BUCKET_NAME="${PULUMI_S3_BUCKET:-knock-lambda-pulumi-state}"
AWS_REGION="${AWS_REGION:-us-east-2}"

cd "$INFRA_DIR"

echo "🚀 Pulumi S3 Backend Migration Script"
echo "======================================"
echo ""
echo "S3 Bucket: $BUCKET_NAME"
echo "AWS Region: $AWS_REGION"
echo ""

# Check if bucket exists
if aws s3 ls "s3://$BUCKET_NAME" 2>/dev/null; then
    echo "✅ S3 bucket already exists: $BUCKET_NAME"
else
    echo "📦 Creating S3 bucket: $BUCKET_NAME"
    aws s3 mb "s3://$BUCKET_NAME" --region "$AWS_REGION"
    
    # Enable versioning for state history
    echo "🔄 Enabling versioning on bucket..."
    aws s3api put-bucket-versioning \
        --bucket "$BUCKET_NAME" \
        --versioning-configuration Status=Enabled
    
    # Enable server-side encryption
    echo "🔒 Enabling encryption on bucket..."
    aws s3api put-bucket-encryption \
        --bucket "$BUCKET_NAME" \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }'
    
    # Block public access
    echo "🛡️  Blocking public access..."
    aws s3api put-public-access-block \
        --bucket "$BUCKET_NAME" \
        --public-access-block-configuration \
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    
    echo "✅ S3 bucket created and configured"
fi

echo ""
echo "📦 Exporting existing stacks..."
mkdir -p .migration-backup

for stack in dev main; do
    echo "  Exporting $stack stack..."
    if pulumi stack select $stack 2>/dev/null; then
        pulumi stack export --file ".migration-backup/${stack}-stack.json"
        echo "  ✅ $stack stack exported"
    else
        echo "  ⚠️  $stack stack not found, skipping"
    fi
done

echo ""
echo "🔄 Logging into S3 backend..."
pulumi login "s3://$BUCKET_NAME"

if [ $? -ne 0 ]; then
    echo "❌ Failed to login to S3 backend"
    exit 1
fi

echo ""
echo "Current backend: $(pulumi whoami -v | grep 'Backend URL')"
echo ""

echo "🔄 Migrating stacks to S3 backend..."

for stack in dev main; do
    if [ -f ".migration-backup/${stack}-stack.json" ]; then
        echo "  Importing $stack stack..."
        
        # Try to create the stack (it might already exist)
        pulumi stack init $stack 2>/dev/null || pulumi stack select $stack
        
        # Import the state
        pulumi stack import --file ".migration-backup/${stack}-stack.json"
        
        echo "  ✅ $stack stack migrated"
    fi
done

echo ""
echo "✅ Migration complete!"
echo ""
echo "📋 Next steps:"
echo "1. Verify your stacks: pulumi stack ls"
echo "2. Test a deployment: pulumi preview"
echo "3. Update GitHub Actions workflow to use S3:"
echo "   - Remove PULUMI_ACCESS_TOKEN from workflow"
echo "   - Add login step: pulumi login s3://$BUCKET_NAME"
echo "4. Make sure GitHub Actions has AWS credentials with S3 access"
echo ""
echo "🗑️  After verifying everything works, you can delete the backup:"
echo "   rm -rf .migration-backup"
echo ""
echo "📝 Team members should run:"
echo "   cd infrastructure"
echo "   pulumi login s3://$BUCKET_NAME"
echo ""
