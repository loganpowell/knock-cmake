#!/bin/bash

# CodeBuild runner with image digest capture
# Runs CodeBuild and captures the resulting image digest

set -e

# Ensure Homebrew is in PATH (for VS Code terminal and Pulumi compatibility)
if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -f /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
fi

# Load platform compatibility layer
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$PROJECT_ROOT/scripts/platform-compat.sh"

# Print debug commands for developer to run
print_debug_commands() {
    local build_id="$1"
    local project_name="$2"
    local region="$3"
    
    echo ""
    echo "� DEBUG COMMANDS:"
    echo "=================="
    echo "# Get build details:"
    echo "aws codebuild batch-get-builds --ids '$build_id' --region $region"
    echo ""
    echo "# View logs (if available):"
    echo "aws logs tail /aws/codebuild/$project_name --region $region --follow"
    echo ""
    echo "# Get build phases:"
    echo "aws codebuild batch-get-builds --ids '$build_id' --region $region --query 'builds[0].phases'"
    echo ""
}

PROJECT_NAME="$1"
AWS_REGION="$2"
MAX_RETRIES="$3"
RETRY_DELAY="$4"
TIMEOUT_MINUTES="$5"

if [ -z "$PROJECT_NAME" ] || [ -z "$AWS_REGION" ]; then
    echo "❌ Error: PROJECT_NAME and AWS_REGION are required"
    echo "Usage: $0 <project-name> <aws-region> [max-retries] [retry-delay] [timeout-minutes]"
    exit 1
fi

# Set defaults
MAX_RETRIES=${MAX_RETRIES:-3}
RETRY_DELAY=${RETRY_DELAY:-30}
TIMEOUT_MINUTES=${TIMEOUT_MINUTES:-30}

echo "🚀 Starting CodeBuild project: $PROJECT_NAME"
echo "Region: $AWS_REGION"
echo "Max retries: $MAX_RETRIES"
echo "Retry delay: ${RETRY_DELAY}s"
echo "Timeout: ${TIMEOUT_MINUTES}m"

# Add retry logic for project availability
for i in $(seq_compat 1 $MAX_RETRIES); do
    echo "Attempt $i to start build..."
    if BUILD_ID=$(aws codebuild start-build --project-name "$PROJECT_NAME" --region "$AWS_REGION" --query 'build.id' --output text 2>/dev/null); then
        echo "Build started with ID: $BUILD_ID"
        break
    else
        if [ $i -eq $MAX_RETRIES ]; then
            echo "Failed to start build after $MAX_RETRIES attempts"
            exit 1
        fi
        echo "Project not yet available, waiting $RETRY_DELAY seconds..."
        sleep $RETRY_DELAY
    fi
done

if [ -z "$BUILD_ID" ] || [ "$BUILD_ID" = "None" ]; then
    echo "❌ Failed to start CodeBuild project"
    exit 1
fi

echo "📋 Build ID: $BUILD_ID"

# Wait for build completion
echo "⏳ Waiting for build to complete..."
START_TIME=$(date_seconds)
TIMEOUT_SECONDS=$((TIMEOUT_MINUTES * 60))
WAIT_COUNT=0

while true; do
    CURRENT_TIME=$(date_seconds)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    ELAPSED_MIN=$((ELAPSED / 60))
    
    if [ $ELAPSED -gt $TIMEOUT_SECONDS ]; then
        echo "❌ Build timed out after ${TIMEOUT_MINUTES} minutes"
        echo "Attempting to stop the build..."
        aws codebuild stop-build --id "$BUILD_ID" --region "$AWS_REGION" || echo "Could not stop build"
        exit 1
    fi
    
    BUILD_STATUS=$(aws codebuild batch-get-builds \
        --ids "$BUILD_ID" \
        --region "$AWS_REGION" \
        --query 'builds[0].buildStatus' \
        --output text)
    
    WAIT_COUNT=$((WAIT_COUNT + 1))
    echo "[$ELAPSED_MIN min] Build status: $BUILD_STATUS (check #$WAIT_COUNT)"
    
    case "$BUILD_STATUS" in
        "SUCCEEDED")
            echo "✅ Build completed successfully!"
            echo "=================== BUILD SUMMARY ==================="
            aws codebuild batch-get-builds --ids "$BUILD_ID" --region "$AWS_REGION" --query 'builds[0].{Status:buildStatus,Duration:buildComplete-buildStartTime,Phase:currentPhase}' --output table 2>/dev/null || echo "Build successful but could not retrieve summary"
            echo "====================================================="
            break
            ;;
        "FAILED"|"FAULT"|"STOPPED"|"TIMED_OUT")
            echo "❌ Build failed with status: $BUILD_STATUS"
            print_debug_commands "$BUILD_ID" "$PROJECT_NAME" "$AWS_REGION"
            exit 1
            ;;
        "IN_PROGRESS"|"QUEUED")
            echo "Build still in progress, waiting 30 seconds..."
            sleep 30
            ;;
        *)
            echo "Unknown status '$BUILD_STATUS', waiting 30 seconds..."
            sleep 30
            ;;
    esac
done

# Get the image digest directly from ECR
echo "📜 Getting image digest from ECR..."
sleep 5

ECR_REPO_NAME=$(aws codebuild batch-get-projects \
    --names "$PROJECT_NAME" \
    --region "$AWS_REGION" \
    --query 'projects[0].environment.environmentVariables[?name==`ECR_REPOSITORY_URI`].value' \
    --output text | cut -d'/' -f2)

if [ -n "$ECR_REPO_NAME" ]; then
    IMAGE_DIGEST=$(aws ecr describe-images \
        --repository-name "$ECR_REPO_NAME" \
        --region "$AWS_REGION" \
        --image-ids imageTag=latest \
        --query 'imageDetails[0].imageDigest' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$IMAGE_DIGEST" ] && [ "$IMAGE_DIGEST" != "None" ] && [ "$IMAGE_DIGEST" != "null" ]; then
        ECR_REPO_URI=$(aws codebuild batch-get-projects \
            --names "$PROJECT_NAME" \
            --region "$AWS_REGION" \
            --query 'projects[0].environment.environmentVariables[?name==`ECR_REPOSITORY_URI`].value' \
            --output text)
        
        IMAGE_URI_WITH_DIGEST="$ECR_REPO_URI@$IMAGE_DIGEST"
        echo "✅ Image URI: $IMAGE_URI_WITH_DIGEST"
        
        # Use platform-safe temp file path
        TEMP_DIR=$(get_temp_dir)
        OUTPUT_FILE=$(safe_file_path "$TEMP_DIR/image_uri_digest.txt")
        echo "$IMAGE_URI_WITH_DIGEST" > "$OUTPUT_FILE"
        log_success "Image URI saved to $OUTPUT_FILE"
    else
        echo "⚠️ Could not get image digest"
        echo ""
        echo "🔧 DEBUG COMMAND:"
        echo "aws ecr describe-images --repository-name $ECR_REPO_NAME --region $AWS_REGION"
    fi
else
    echo "❌ Could not determine ECR repository name"
    echo ""
    echo "� DEBUG COMMAND:"
    echo "aws codebuild batch-get-projects --names $PROJECT_NAME --region $AWS_REGION"
fi

echo "🎉 CodeBuild completed successfully!"