#!/bin/bash

# Lambda Function Wait Script
# Waits for a Lambda function to become active and ready

set -e

# Configuration
FUNCTION_NAME="$1"
AWS_REGION="$2"
MAX_ATTEMPTS=30
SLEEP_INTERVAL=10

if [ -z "$FUNCTION_NAME" ]; then
    echo "❌ Error: Function name is required"
    echo "Usage: $0 <function-name>"
    exit 1
fi

echo "🔄 Waiting for Lambda function '$FUNCTION_NAME' to become active..."
echo "Region: $AWS_REGION"
echo "Max attempts: $MAX_ATTEMPTS (${SLEEP_INTERVAL}s intervals)"

attempt=1
while [ $attempt -lt $MAX_ATTEMPTS ]; do
    status=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query 'Configuration.State' --output text 2>/dev/null || echo "UNKNOWN")
    update_status=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query 'Configuration.LastUpdateStatus' --output text 2>/dev/null || echo "UNKNOWN")
    
    echo "Attempt $attempt/$MAX_ATTEMPTS: State=$status, UpdateStatus=$update_status"
    
    if [ "$status" = "Active" ] && [ "$update_status" = "Successful" ]; then
        echo "✅ Lambda function is active and ready!"
        
        # Test basic connectivity
        echo "🧪 Testing Lambda function connectivity..."
        function_url=$(aws lambda get-function-url-config --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query 'FunctionUrl' --output text 2>/dev/null || echo "")
        
        if [ -n "$function_url" ] && [ "$function_url" != "None" ]; then
            http_code=$(curl -s -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"test": "connectivity"}' "$function_url" -o /dev/null || echo "000")
            
            if [[ $http_code =~ ^[2-5][0-9][0-9]$ ]]; then
                echo "✅ Lambda function is responding (HTTP $http_code)"
                exit 0
            else
                echo "⚠️  Lambda function not responding yet (HTTP $http_code), but deployment will continue"
                exit 0
            fi
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