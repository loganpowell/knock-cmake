# AWS Lambda Function URL Authorization Update (Nov 2026)

## Summary

AWS Lambda is updating the Function URL authorization model to improve security. Starting **November 1, 2026**, function URLs will require permissions policies to include **both** actions:
- `lambda:InvokeFunctionUrl`
- `lambda:InvokeFunction`

Previously, only `lambda:InvokeFunctionUrl` was required.

## Changes Made

We've updated `infrastructure/environment_stack.py` to include both required permissions:

```python
# Permission for lambda:InvokeFunctionUrl
function_url_permission = aws.lambda_.Permission(
    "knock-lambda-url-permission",
    action="lambda:InvokeFunctionUrl",
    function=lambda_function.name,
    principal="*",  # Public access
    function_url_auth_type="NONE",
)

# Permission for lambda:InvokeFunction (new requirement)
function_invoke_permission = aws.lambda_.Permission(
    "knock-lambda-invoke-permission",
    action="lambda:InvokeFunction",
    function=lambda_function.name,
    principal="*",  # Public access
    source_account=<account_id>,
)
```

## Deployment

To apply these changes:

```bash
# Dev environment
pulumi stack select dev
pulumi up

# Main/production environment
pulumi stack select main
pulumi up
```

## Verification

After deployment, verify the function URL still works:

```bash
# Get the function URL
FUNCTION_URL=$(pulumi stack output function_url)

# Test health check
curl "$FUNCTION_URL/health"
```

You should see a successful response indicating the Lambda function is accessible.

## Impact

- ✅ **No breaking changes** - These permissions maintain the same public access level
- ✅ **Forward compatible** - Meets the new authorization model requirements
- ✅ **Deadline compliant** - Must be deployed before November 1, 2026

## Security Consideration

This function URL is currently configured with `authorization_type="NONE"`, meaning it's publicly accessible. If you want to restrict access:

1. Change `authorization_type` to `"AWS_IAM"`
2. Update permissions to use specific principals instead of `"*"`
3. Configure API Gateway or CloudFront for additional access controls

## References

- [AWS Lambda Function URLs - Authorization](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html)
- [AWS Health Dashboard Notification](https://health.aws.amazon.com/)
- [Lambda AddPermission API](https://docs.aws.amazon.com/lambda/latest/api/API_AddPermission.html)

## Timeline

- **Now - Oct 2025**: Temporary exception granted (grace period)
- **November 1, 2026**: New authorization model enforced
- **Action Required**: Update and deploy before the deadline

## Affected Resources

Check your AWS Health Dashboard for the complete list of affected function ARNs in your account.
