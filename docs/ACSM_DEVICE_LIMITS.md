# ACSM Device Limit Issues

## Understanding the Error

The `E_GOOGLE_DEVICE_LIMIT_REACHED` error occurs when:
1. **Device Limit**: The Adobe device credentials have been activated on too many devices (Google Books limit: ~6 devices)
2. **Transaction Limit**: The specific ACSM file/transaction has been fulfilled too many times
3. **Expiration**: The ACSM file has expired

## Current Issue

Your test ACSM file (`assets/Princes_of_the_Yen-epub.acsm`) has:
- **Expired**: `2025-10-19T12:32:29-07:00` (expired today)
- **Transaction ID**: `ge:6dcf2e9a-31a9-b54e-8c76-c039a5b903ba:1760901449093561`

This transaction has likely reached its fulfillment limit with Google Books. Even with fresh device credentials, the same ACSM file cannot be used.

## Solution: Get a Fresh ACSM File

### Option 1: Download from Google Books (Recommended)

1. Go to [Google Play Books](https://play.google.com/books)
2. Find a free book or one you own
3. Look for the "Download ACSM" option (usually in settings/download options)
4. Save the new `.acsm` file
5. Replace the test file:
   ```bash
   cp /path/to/new/file.acsm assets/test-book.acsm
   ```

### Option 2: Use a Different Book Source

If Google Books continues to have limits, try:
- [Internet Archive](https://archive.org/) - Many public domain books with ACSM
- [OverDrive](https://www.overdrive.com/) - Library ebooks (requires library card)
- [Adobe Content Server Test Files](https://www.adobe.com/solutions/ebook/digital-editions.html)

### Option 3: Generate Test ACSM (Development Only)

For development/testing, you can create a mock ACSM file, but it won't work for actual fulfillment:

```bash
# This creates a template - you'll need valid credentials for real testing
cp assets/Princes_of_the_Yen-epub.acsm assets/test-template.acsm
# Edit the file to update expiration, transaction ID, etc.
```

## Resetting Device Credentials

If you've already tried multiple ACSM files and still hit device limits:

```bash
# Clear device credentials and force regeneration
./scripts/reset_device_credentials.sh

# Then test with a FRESH ACSM file
./tests/run_tests.sh
```

## How the System Works

1. **First Run**: Lambda generates device credentials using `adept_activate`
2. **Credential Storage**: Credentials saved to S3 for reuse
3. **Subsequent Runs**: Lambda reuses credentials from S3
4. **Device Limit**: Adobe/Google allows ~6 device activations per account
5. **Transaction Limit**: Each ACSM file can only be fulfilled a limited number of times

## Monitoring Device Usage

Check which credentials are in use:

```bash
BUCKET=$(cd infrastructure && pulumi stack output device_credentials_bucket)
aws s3 ls s3://$BUCKET/credentials/ --no-cli-pager
```

View credential details:

```bash
# Download and inspect activation.xml
aws s3 cp s3://$BUCKET/credentials/activation.xml /tmp/activation.xml --no-cli-pager
cat /tmp/activation.xml
```

## Troubleshooting

### Error: "Device credentials not found"
- Run: `./scripts/reset_device_credentials.sh`
- Lambda will auto-generate on next invocation

### Error: "E_GOOGLE_DEVICE_LIMIT_REACHED" (persists)
- ✅ Reset credentials (done)
- ❌ **Get a fresh ACSM file** (required)
- The current ACSM transaction is exhausted

### Error: "ACSM file expired"
- ACSM files have expiration dates
- Download a new ACSM from the source
- Check expiration: `grep expiration assets/your-file.acsm`

## Best Practices for Testing

1. **Use Fresh ACSM Files**: Download new ones periodically
2. **Check Expiration**: ACSM files typically expire within days/weeks
3. **Limit Test Runs**: Each test uses one device activation slot
4. **Reset Periodically**: Clear credentials when switching test files
5. **Document Sources**: Keep track of where test ACSM files come from

## References

- [Adobe ADEPT Protocol](https://www.adobe.com/solutions/ebook/digital-editions.html)
- [libgourou Documentation](../deps/libgourou/README.md)
- [Knock Lambda Handler](../infrastructure/lambda/handler.py)
