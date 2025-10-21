# Interactive Test CLI

An interactive command-line interface for testing the Knock Lambda function with ACSM files.

## Features

- 🔍 **Auto-discovery**: Automatically finds all `.acsm` files in the repository
- 🏥 **Health Check**: Test Lambda connectivity before running tests
- � **Debug Mode**: Test presigned URL generation without consuming Adobe licenses
- �📂 **Single File Test**: Select and test individual ACSM files
- 📚 **Batch Testing**: Test all ACSM files at once
- 🔄 **Multi-select**: Choose specific files to test together
- 📄 **File Viewer**: Preview ACSM file content before testing
- 📊 **Summary Reports**: See test results with timing and status

## Prerequisites

```bash
# Install dependencies
uv sync

# Make sure Lambda is deployed
pulumi up
```

## Usage

### Run the Interactive CLI

The easiest way to run the interactive test CLI is using the `uv` script entry point:

```bash
# From anywhere in the project
uv run test
```

Alternative methods:

```bash
# Run directly with Python
uv run python tests/interactive_test.py

# Or make it executable and run
chmod +x tests/interactive_test.py
./tests/interactive_test.py
```

### Menu Options

1. **🏥 Run health check** - Verify Lambda is accessible and responding
2. **� Test presigned URL (debug mode)** - Test S3 upload and presigned URL generation without using Adobe licenses
3. **�📂 Test single ACSM file** - Select one file from a list to test
4. **📚 Test all ACSM files** - Run tests on all discovered ACSM files
5. **🔄 Test multiple files (select)** - Choose specific files to test (multi-select with Space)
6. **🔍 View file content** - Preview the content of an ACSM file
7. **🚪 Exit** - Quit the CLI

## Example Session

```
🚀 Knock Lambda Interactive Test CLI
======================================================================

🔍 Scanning for ACSM files...
✅ Found 7 ACSM file(s)

🔗 Getting Lambda function URL...
✅ Function URL: https://xxxxx.lambda-url.us-east-1.on.aws/

[?] What would you like to do?:
 > 🏥 Run health check
   📂 Test single ACSM file
   📚 Test all ACSM files
   🔄 Test multiple files (select)
   🔍 View file content
   🚪 Exit
```

## Navigation

- **Arrow Keys**: Move up/down in lists
- **Space**: Select/deselect items (in multi-select mode)
- **Enter**: Confirm selection
- **Ctrl+C**: Exit the program

## File Discovery

The CLI automatically searches for `.acsm` files in:

- `assets/`
- `tests/fixtures/`
- `tests/data/`
- And recursively throughout the project (excluding hidden dirs, node_modules, etc.)

## Output

For each test, you'll see:

```
======================================================================
📂 Testing: The_Creative_Habit-epub.acsm
======================================================================

📄 Content preview:
<?xml version="1.0" encoding="UTF-8"?>
<fulfillmentToken...

📡 Sending request to Lambda...

📋 Response:
──────────────────────────────────────────────────────────────────────
{
  "status": "success",
  "message": "EPUB file generated successfully",
  "epub_url": "https://..."
}
──────────────────────────────────────────────────────────────────────

✅ Status: 200
⏱️  Duration: 3.45s
📦 Response size: 1234 bytes
```

## Batch Testing Summary

When testing multiple files, you'll get a summary:

```
📊 Test Summary
======================================================================

✅ Ecosystem_Geography-epub.acsm              (2.34s)
✅ How_To_Practice-epub.acsm                  (3.12s)
❌ Invalid_Test-epub.acsm                     (0.45s)
✅ The_Creative_Habit-epub.acsm               (2.89s)

──────────────────────────────────────────────────────────────────────
Total: 4 | Passed: 3 | Failed: 1
──────────────────────────────────────────────────────────────────────
```

## Troubleshooting

### "No ACSM files found"

- Make sure you have `.acsm` files in `assets/`, `tests/fixtures/`, or `tests/data/`
- Check that the files have the `.acsm` extension

### "Could not get function URL"

- Ensure Lambda is deployed: `pulumi up`
- Check that you're in the project root directory
- Verify your `.env` file has correct AWS credentials

### "Request timeout"

- Lambda might be cold starting (first request after deployment)
- Check Lambda logs: `pulumi logs -f`
- Verify the ACSM file is valid

## Tips

- Use **health check** first to verify Lambda is ready
- Use **view content** to inspect ACSM files before testing
- Use **multi-select** mode to test specific problematic files together
- Test results show response time - useful for performance monitoring
