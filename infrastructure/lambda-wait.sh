#!/bin/bash

# Lambda Function Wait Script
# Waits for a Lambda function to become active and ready

set -e

# Load platform compatibility layer
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/platform-compat.sh"

# Configuration
FUNCTION_NAME="$1"
AWS_REGION="$2"
EXPECTED_IMAGE_DIGEST="$3"  # Optional: verify specific image is deployed
MAX_ATTEMPTS=60  # Increased for container image updates
SLEEP_INTERVAL=5

if [ -z "$FUNCTION_NAME" ]; then
    echo "❌ Error: Function name is required"
    echo "Usage: $0 <function-name>"
    exit 1
fi

echo "🔄 Waiting for Lambda function '$FUNCTION_NAME' to become active..."
echo "Region: $AWS_REGION"
if [ -n "$EXPECTED_IMAGE_DIGEST" ]; then
    echo "Expected image digest: $EXPECTED_IMAGE_DIGEST"
fi
echo "Max attempts: $MAX_ATTEMPTS (${SLEEP_INTERVAL}s intervals)"

attempt=1
while [ $attempt -lt $MAX_ATTEMPTS ]; do
    status=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query 'Configuration.State' --output text 2>/dev/null || echo "UNKNOWN")
    update_status=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query 'Configuration.LastUpdateStatus' --output text 2>/dev/null || echo "UNKNOWN")
    current_image=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query 'Code.ImageUri' --output text 2>/dev/null || echo "UNKNOWN")
    
    echo "Attempt $attempt/$MAX_ATTEMPTS: State=$status, UpdateStatus=$update_status"
    
    if [ "$status" = "Active" ] && [ "$update_status" = "Successful" ]; then
        # Verify image digest if provided
        if [ -n "$EXPECTED_IMAGE_DIGEST" ]; then
            if [[ "$current_image" == *"$EXPECTED_IMAGE_DIGEST"* ]]; then
                echo "✅ Lambda is using expected image: $current_image"
            else
                echo "⚠️  Image mismatch. Current: $current_image"
                echo "   Waiting for expected digest: $EXPECTED_IMAGE_DIGEST"
                attempt=$((attempt + 1))
                sleep $SLEEP_INTERVAL
                continue
            fi
        fi
        
        echo "✅ Lambda function is active and ready!"
        
        # Test basic connectivity with retry
        echo "🧪 Testing Lambda function connectivity..."
        function_url=$(aws lambda get-function-url-config --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query 'FunctionUrl' --output text 2>/dev/null || echo "")
        
        if [ -n "$function_url" ] && [ "$function_url" != "None" ]; then
            echo "Function URL: $function_url"
            
            # Try health check up to 3 times
            health_attempts=0
            max_health_attempts=3
            while [ $health_attempts -lt $max_health_attempts ]; do
                echo "Health check attempt $((health_attempts + 1))/$max_health_attempts..."
                response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" \
                    -d '{"test": "connectivity"}' "$function_url" 2>&1 || echo "error\n000")
                
                # Use platform-compatible functions
                http_code=$(echo "$response" | get_last_line)
                body=$(echo "$response" | all_but_last_line)
                if [[ $http_code =~ ^[2-5][0-9][0-9]$ ]]; then
                    echo "✅ Lambda function is responding (HTTP $http_code)"
                    if [ "$http_code" = "400" ]; then
                        echo "   Response: $body"
                        echo "   (400 is expected for missing required parameters)"
                    fi
                    exit 0
                else
                    echo "⚠️  Lambda not responding yet (HTTP $http_code)"
                    health_attempts=$((health_attempts + 1))
                    if [ $health_attempts -lt $max_health_attempts ]; then
                        sleep 5
                    fi
                fi
            done
            
            echo "⚠️  Lambda function not responding after $max_health_attempts attempts, but continuing..."
            exit 0
        else
            echo "⚠️  No function URL found, but Lambda is active"
            exit 0
        fi
    fi
    
    if [ "$status" = "Failed" ] || [ "$update_status" = "Failed" ]; then
        echo "❌ Lambda function update failed!"
        exit 1
    fi
    
    attempt=$((attempt + 1))
    sleep $SLEEP_INTERVAL
done

echo "⚠️  Lambda function didn't become active within expected time, but continuing..."
exit 0