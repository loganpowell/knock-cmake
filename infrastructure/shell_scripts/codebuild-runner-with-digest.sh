#!/bin/bash

# CodeBuild runner with image digest capture and enhanced error reporting
# Runs CodeBuild and captures the resulting image digest

set -e

# Function to extract and highlight key error information from logs
extract_key_errors() {
    local log_messages="$1"
    
    echo ""
    echo "🔍 KEY ERROR SUMMARY:"
    echo "========================"
    
    # Look for file not found errors (like our recent Dockerfile issue)
    if echo "$log_messages" | grep -q "not found"; then
        echo "📁 FILE NOT FOUND ERRORS:"
        echo "$log_messages" | grep -E "(not found|No such file)" | sed 's/^/   ❌ /'
        echo ""
    fi
    
    # Look for Docker build failures
    if echo "$log_messages" | grep -q -E "(failed to (solve|compute|calculate)|ERROR.*dockerfile)"; then
        echo "🐳 DOCKER BUILD ERRORS:"
        echo "$log_messages" | grep -i -E "(failed to (solve|compute|calculate)|ERROR.*dockerfile)" | sed 's/^/   ❌ /'
        echo ""
    fi
    
    # Look for exit code failures
    if echo "$log_messages" | grep -q "exit status [1-9]"; then
        echo "💥 COMMAND FAILURES:"
        echo "$log_messages" | grep -B1 "exit status [1-9]" | sed 's/^/   ❌ /'
        echo ""
    fi
    
    # Look for permission or authentication issues
    if echo "$log_messages" | grep -q -E "(permission denied|access denied|unauthorized|forbidden)"; then
        echo "🔒 PERMISSION/AUTH ERRORS:"
        echo "$log_messages" | grep -i -E "(permission denied|access denied|unauthorized|forbidden)" | sed 's/^/   ❌ /'
        echo ""
    fi
}

# Function to provide actionable suggestions based on error patterns
suggest_fixes() {
    local log_messages="$1"
    
    echo "💡 SUGGESTED FIXES:"
    echo "=================="
    
    # File not found suggestions
    if echo "$log_messages" | grep -q -E "COPY.*not found|file.*not found"; then
        echo "   📁 File Missing Issue Detected:"
        echo "      - Check if all files referenced in Dockerfile exist"
        echo "      - Verify file paths are correct relative to build context"
        echo "      - Run 'ls -la' in the directory to confirm file names"
        echo ""
    fi
    
    # Docker build suggestions
    if echo "$log_messages" | grep -q -E "failed to solve|dockerfile.*error"; then
        echo "   🐳 Docker Build Issue Detected:"
        echo "      - Review Dockerfile syntax for errors"
        echo "      - Check if base image exists and is accessible"
        echo "      - Verify all COPY/ADD source files exist"
        echo ""
    fi
    
    # Build phase suggestions
    if echo "$log_messages" | grep -q "Phase complete.*FAILED"; then
        echo "   🔧 Build Phase Failure Detected:"
        echo "      - Check buildspec.yml syntax and commands"
        echo "      - Verify all required environment variables are set"
        echo "      - Review command exit codes in the logs above"
        echo ""
    fi
    
    # Network/dependency suggestions
    if echo "$log_messages" | grep -q -E "(timeout|network|connection.*failed|unable to connect)"; then
        echo "   🌐 Network/Connectivity Issue Detected:"
        echo "      - Check internet connectivity in build environment"
        echo "      - Verify repository URLs and package sources"
        echo "      - Consider using VPC endpoints if in private subnet"
        echo ""
    fi
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
for i in $(seq 1 $MAX_RETRIES); do
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
START_TIME=$(date +%s)
TIMEOUT_SECONDS=$((TIMEOUT_MINUTES * 60))
WAIT_COUNT=0

while true; do
    CURRENT_TIME=$(date +%s)
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
            echo "Fetching build logs for debugging..."
            
            # Extract the build UUID from BUILD_ID (format: project-name:uuid)
            BUILD_UUID=$(echo "$BUILD_ID" | cut -d: -f2)
            LOG_GROUP_NAME="/aws/codebuild/$PROJECT_NAME"
            
            echo "Build ID: $BUILD_ID"
            echo "Build UUID: $BUILD_UUID"
            echo "Log Group: $LOG_GROUP_NAME"
            echo "AWS Region: $AWS_REGION"
            
            # Wait for logs to be available
            echo "Waiting 15 seconds for logs to be available..."
            sleep 15
            
            echo ""
            echo "🔍 PERFORMING COMPREHENSIVE LOG ANALYSIS..."
            echo "============================================"
            
            # Try automated retrieval
            echo "Attempting automated log retrieval..."
            
            # Check if log group exists
            LOG_GROUP_CHECK=$(aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_NAME" --region "$AWS_REGION" --query 'logGroups[0].logGroupName' --output text 2>/dev/null)
            echo "Log group check result: '$LOG_GROUP_CHECK'"
            
            if [ "$LOG_GROUP_CHECK" != "None" ] && [ "$LOG_GROUP_CHECK" != "null" ] && [ -n "$LOG_GROUP_CHECK" ]; then
                echo "✓ Log group found: $LOG_GROUP_CHECK"
                
                # List all recent log streams for debugging
                echo "Recent log streams:"
                aws logs describe-log-streams --log-group-name "$LOG_GROUP_NAME" --region "$AWS_REGION" --order-by LastEventTime --descending --max-items 10 --query 'logStreams[].[logStreamName,lastEventTimestamp]' --output table 2>/dev/null || echo "Failed to list streams"
                
                # Try to find the exact build log stream
                echo "Looking for log stream: $BUILD_UUID"
                LOG_STREAM=$(aws logs describe-log-streams --log-group-name "$LOG_GROUP_NAME" --region "$AWS_REGION" --order-by LastEventTime --descending --max-items 20 --query "logStreams[?logStreamName=='$BUILD_UUID'].logStreamName | [0]" --output text 2>/dev/null | tr -d '\n' | sed 's/None$//')
                echo "Exact match result: '$LOG_STREAM'"
                
                # If exact match fails, get the most recent stream
                if [ -z "$LOG_STREAM" ] || [ "$LOG_STREAM" = "None" ] || [ "$LOG_STREAM" = "null" ]; then
                    echo "Exact UUID not found, getting most recent stream..."
                    LOG_STREAM=$(aws logs describe-log-streams --log-group-name "$LOG_GROUP_NAME" --region "$AWS_REGION" --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text 2>/dev/null | tr -d '\n')
                    echo "Most recent stream: '$LOG_STREAM'"
                fi
                
                if [ -n "$LOG_STREAM" ] && [ "$LOG_STREAM" != "None" ] && [ "$LOG_STREAM" != "null" ]; then
                    echo ""
                    echo "==================== BUILD LOGS ===================="
                    echo "Retrieving logs from stream: '$LOG_STREAM'"
                    echo "====================================================="
                    
                    # Get logs with detailed error handling
                    LOG_RESULT=$(aws logs get-log-events --log-group-name "$LOG_GROUP_NAME" --log-stream-name "$LOG_STREAM" --region "$AWS_REGION" --output json 2>&1)
                    LOG_EXIT_CODE=$?
                    
                    echo "AWS CLI exit code: $LOG_EXIT_CODE"
                    
                    if [ $LOG_EXIT_CODE -eq 0 ]; then
                        # Parse and display the logs with error highlighting
                        echo "Extracting log messages..."
                        LOG_MESSAGES=$(echo "$LOG_RESULT" | jq -r '.events[]?.message // empty' 2>/dev/null)
                        
                        if [ -n "$LOG_MESSAGES" ]; then
                            # Use our enhanced error extraction function
                            extract_key_errors "$LOG_MESSAGES"
                            
                            echo "📋 RECENT BUILD OUTPUT (LAST 30 LINES):"
                            echo "========================================"
                            echo "$LOG_MESSAGES" | tail -30 | sed 's/^/   /'
                            echo ""
                            
                            echo "🔧 ADDITIONAL ERROR ANALYSIS:"
                            echo "============================="
                            
                            # Run additional error analysis automatically
                            echo "🔍 Searching for Docker-specific errors..."
                            DOCKER_ERRORS=$(echo "$LOG_MESSAGES" | grep -i -E "(dockerfile|docker build|failed to solve|copy.*not found)" || true)
                            if [ -n "$DOCKER_ERRORS" ]; then
                                echo "   Found Docker-related issues:"
                                echo "$DOCKER_ERRORS" | sed 's/^/      ❌ /'
                            else
                                echo "   ✅ No Docker-specific errors detected"
                            fi
                            echo ""
                            
                            echo "🔍 Searching for dependency/package errors..."
                            DEPENDENCY_ERRORS=$(echo "$LOG_MESSAGES" | grep -i -E "(pip.*error|package.*not found|module.*not found|import.*error)" || true)
                            if [ -n "$DEPENDENCY_ERRORS" ]; then
                                echo "   Found dependency issues:"
                                echo "$DEPENDENCY_ERRORS" | sed 's/^/      ❌ /'
                            else
                                echo "   ✅ No dependency errors detected"
                            fi
                            echo ""
                            
                            echo "🔍 Searching for build phase failures..."
                            PHASE_ERRORS=$(echo "$LOG_MESSAGES" | grep -E "Phase complete.*FAILED|entering phase.*failed" || true)
                            if [ -n "$PHASE_ERRORS" ]; then
                                echo "   Found build phase failures:"
                                echo "$PHASE_ERRORS" | sed 's/^/      ❌ /'
                            else
                                echo "   ✅ No build phase failures detected"
                            fi
                            echo ""
                            
                            echo "📊 ERROR FREQUENCY ANALYSIS:"
                            echo "============================"
                            ERROR_COUNT=$(echo "$LOG_MESSAGES" | grep -i -c "error" || echo "0")
                            FAILED_COUNT=$(echo "$LOG_MESSAGES" | grep -i -c "failed" || echo "0")
                            EXCEPTION_COUNT=$(echo "$LOG_MESSAGES" | grep -i -c "exception" || echo "0")
                            echo "   Total 'error' mentions: $ERROR_COUNT"
                            echo "   Total 'failed' mentions: $FAILED_COUNT"
                            echo "   Total 'exception' mentions: $EXCEPTION_COUNT"
                            echo ""
                            
                            # Provide actionable suggestions
                            suggest_fixes "$LOG_MESSAGES"
                            
                            echo "📝 BUILD FAILURE SUMMARY:"
                            echo "========================"
                            FAILED_PHASE=$(echo "$LOG_MESSAGES" | grep "Phase complete.*FAILED" | tail -1 | sed 's/.*Phase complete: \([A-Z_]*\) State: FAILED.*/\1/' || echo "UNKNOWN")
                            echo "   Build failed in phase: $FAILED_PHASE"
                            if [ "$ERROR_COUNT" -gt 0 ] || [ "$FAILED_COUNT" -gt 0 ]; then
                                echo "   Priority: HIGH (Multiple errors detected)"
                            else
                                echo "   Priority: MEDIUM (Clean failure, check specific issues above)"
                            fi
                            echo "   Next steps: Review the suggestions above and fix the identified issues"
                            echo ""
                        else
                            echo "No log messages found in JSON response"
                            echo "Raw response (first 500 chars): $(echo "$LOG_RESULT" | head -c 500)"
                        fi
                    else
                        echo "❌ AWS CLI command failed with exit code: $LOG_EXIT_CODE"
                        echo "Error output: $LOG_RESULT"
                        echo ""
                        echo "🔧 MANUAL ANALYSIS COMMAND:"
                        echo "=========================="
                        echo "Run this to analyze logs manually:"
                        echo "aws logs get-log-events --log-group-name \"$LOG_GROUP_NAME\" --log-stream-name \"$LOG_STREAM\" --region $AWS_REGION | jq -r '.events[].message' | grep -i -E '(error|failed|exception)'"
                        echo ""
                    fi
                    
                    echo "====================================================="
                    echo "End of automated log retrieval."
                else
                    echo "✗ Could not find any log streams for this build"
                    echo "This might mean:"
                    echo "  - The build failed very early (before logging started)"
                    echo "  - There's a delay in log availability"
                    echo "  - The log stream name doesn't match the build UUID"
                fi
            else
                echo "✗ Log group not found: $LOG_GROUP_NAME"
                echo "Available CodeBuild log groups:"
                aws logs describe-log-groups --log-group-name-prefix "/aws/codebuild/" --region "$AWS_REGION" --query 'logGroups[].logGroupName' --output table 2>/dev/null || echo "Failed to list CodeBuild log groups"
            fi
            
            # Get more detailed build information
            echo "=================== BUILD DETAILS ==================="
            echo "Full build information:"
            aws codebuild batch-get-builds --ids "$BUILD_ID" --region "$AWS_REGION" --query 'builds[0].[buildStatus,currentPhase,startTime,endTime]' --output table 2>/dev/null || echo "Failed to retrieve build details"
            
            # Try to get build phases for more insight
            echo "Build phases:"
            aws codebuild batch-get-builds --ids "$BUILD_ID" --region "$AWS_REGION" --query 'builds[0].phases[].[phaseType,phaseStatus,durationInSeconds]' --output table 2>/dev/null || echo "Failed to retrieve build phases"
            echo "====================================================="
            
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
echo "🕐 Waiting 15 seconds for ECR metadata to be fully updated..."
sleep 15

ECR_REPO_NAME=$(aws codebuild batch-get-projects \
    --names "$PROJECT_NAME" \
    --region "$AWS_REGION" \
    --query 'projects[0].environment.environmentVariables[?name==`ECR_REPOSITORY_URI`].value' \
    --output text | cut -d'/' -f2)

if [ -n "$ECR_REPO_NAME" ]; then
    echo "📋 Repository name: $ECR_REPO_NAME"
    echo "🔍 Attempting to get image digest from ECR..."
    
    # Try multiple times with increasing delays to handle ECR propagation
    MAX_ATTEMPTS=3
    for attempt in $(seq 1 $MAX_ATTEMPTS); do
        echo "Attempt $attempt/$MAX_ATTEMPTS to get image digest..."
        
        IMAGE_DIGEST=$(aws ecr describe-images \
            --repository-name "$ECR_REPO_NAME" \
            --region "$AWS_REGION" \
            --image-ids imageTag=latest \
            --query 'imageDetails[0].imageDigest' \
            --output text 2>/dev/null || echo "")
        
        if [ -n "$IMAGE_DIGEST" ] && [ "$IMAGE_DIGEST" != "None" ] && [ "$IMAGE_DIGEST" != "null" ]; then
            echo "✅ Successfully retrieved image digest: $IMAGE_DIGEST"
            break
        else
            echo "⚠️  Attempt $attempt failed to get digest (got: '$IMAGE_DIGEST')"
            if [ $attempt -lt $MAX_ATTEMPTS ]; then
                echo "⏳ Waiting 10 seconds before retry..."
                sleep 10
            fi
        fi
    done
    
    if [ -n "$IMAGE_DIGEST" ] && [ "$IMAGE_DIGEST" != "None" ] && [ "$IMAGE_DIGEST" != "null" ]; then
        ECR_REPO_URI=$(aws codebuild batch-get-projects \
            --names "$PROJECT_NAME" \
            --region "$AWS_REGION" \
            --query 'projects[0].environment.environmentVariables[?name==`ECR_REPOSITORY_URI`].value' \
            --output text)
        
        IMAGE_URI_WITH_DIGEST="$ECR_REPO_URI@$IMAGE_DIGEST"
        echo "✅ Captured image URI with digest: $IMAGE_URI_WITH_DIGEST"
        echo "$IMAGE_URI_WITH_DIGEST" > /tmp/image_uri_digest.txt
        echo "📁 Image URI saved to /tmp/image_uri_digest.txt"
    else
        echo "❌ Could not get image digest from ECR after $MAX_ATTEMPTS attempts"
        echo "🔄 Falling back to latest tag..."
        # Fallback to latest tag
        ECR_REPO_URI=$(aws codebuild batch-get-projects \
            --names "$PROJECT_NAME" \
            --region "$AWS_REGION" \
            --query 'projects[0].environment.environmentVariables[?name==`ECR_REPOSITORY_URI`].value' \
            --output text)
        
        if [ -n "$ECR_REPO_URI" ]; then
            echo "$ECR_REPO_URI:latest" > /tmp/image_uri_digest.txt
            echo "📁 Fallback to latest tag: $ECR_REPO_URI:latest"
            echo "⚠️  Note: Lambda may not update automatically on next build without digest"
        fi
    fi
else
    echo "❌ Could not determine ECR repository name"
    echo "🔧 Manual intervention may be required"
fi

echo "🎉 CodeBuild completed successfully!"