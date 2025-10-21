# Interactive Test CLI - Summary

## ✅ Completed

Created an interactive command-line interface for testing the Knock Lambda function with ACSM files.

### Files Created/Modified

1. **`tests/interactive_test.py`** - Main interactive CLI application

   - Auto-discovers all `.acsm` files in the repository
   - Menu-driven interface with inquirer
   - Health check functionality
   - Single file, batch, and multi-select testing modes
   - File content viewer
   - Formatted test results with timing and summaries

2. **`tests/INTERACTIVE_CLI.md`** - Documentation

   - Usage instructions
   - Feature list
   - Example session output
   - Troubleshooting guide

3. **`tests/__init__.py`** - Package initialization

   - Makes tests directory a proper Python package

4. **`pyproject.toml`** - Updated configuration

   - Added `inquirer>=3.1.0` to dev dependencies
   - Added `[project.scripts]` entry point: `itest = "tests.interactive_test:main"`
   - Added tests package to build targets

5. **`README.md`** - Updated main documentation
   - Added reference to Interactive CLI at top of testing section

### Usage

Simply run:

```bash
uv run itest
```

From anywhere in the project!

### Features

- 🔍 **Auto-discovery**: Finds all `.acsm` files in assets/, tests/fixtures/, tests/data/
- 🏥 **Health Check**: Test Lambda connectivity
- 📂 **Single File Test**: Select one file from a menu
- 📚 **Batch Testing**: Test all files with summary report
- 🔄 **Multi-select**: Choose specific files (Space to select, Enter to confirm)
- 📄 **File Viewer**: Preview ACSM content before testing
- 📊 **Summary Reports**: Shows pass/fail counts and timing

### Example Output

```
======================================================================
🚀 Knock Lambda Interactive Test CLI
======================================================================

🔍 Scanning for ACSM files...
✅ Found 7 ACSM file(s)

🔗 Getting Lambda function URL...
✅ Function URL: https://xxxxx.lambda-url.us-east-2.on.aws/

[?] What would you like to do?:
   🏥 Run health check
 ❯ 📂 Test single ACSM file
   📚 Test all ACSM files
   🔄 Test multiple files (select)
   🔍 View file content
   🚪 Exit
```

### Technical Details

- Uses `inquirer` library for interactive menus
- Integrates with existing `get_function_url()` function from manual_test.py
- Supports keyboard navigation (arrows, space, enter)
- Graceful error handling with Ctrl+C support
- Cross-platform compatible (works on macOS, Linux, Windows)

### Next Steps

Users can now:

1. Run `uv sync` to install dependencies
2. Deploy Lambda with `pulumi up`
3. Run `uv run itest` to start interactive testing
4. Select files and view results in real-time
5. Get immediate feedback on Lambda performance
