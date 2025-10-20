# Platform Compatibility Layer

This directory includes a cross-platform compatibility layer (`platform-compat.sh`) that ensures all scripts work correctly on both macOS and Linux environments.

## Why This Exists

Shell scripts have subtle differences between macOS (BSD-based tools) and Linux (GNU tools). Common issues include:

- `head -n -1` works on Linux but fails on macOS with "illegal line count"
- `stat` has different flag syntax between platforms
- `readlink -f` doesn't exist on macOS by default
- `date` command format strings differ

## Usage

All scripts that might run in different environments should source this file:

```bash
#!/bin/bash

# Load platform compatibility layer
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/platform-compat.sh"

# Now you can use cross-platform functions
response=$(curl -s -w "\n%{http_code}" ...)
http_code=$(echo "$response" | get_last_line)
body=$(echo "$response" | all_but_last_line)
```

## Available Functions

### Text Processing

- **`all_but_last_line`** - Get all lines except the last (replaces `head -n -1`)
  ```bash
  echo "$output" | all_but_last_line
  ```

- **`get_last_line`** - Get the last line of input
  ```bash
  echo "$output" | get_last_line
  ```

### File Operations

- **`absolute_path <path>`** - Get absolute path (replaces `readlink -f`)
  ```bash
  abs_path=$(absolute_path "relative/path/to/file")
  ```

- **`file_modified_time <path>`** - Get file modification timestamp
  ```bash
  mtime=$(file_modified_time "/path/to/file")
  ```

- **`file_size_human <path>`** - Get human-readable file size
  ```bash
  size=$(file_size_human "/path/to/file")
  ```

### Date/Time

- **`iso_timestamp`** - Get current timestamp in ISO 8601 format
  ```bash
  timestamp=$(iso_timestamp)  # 2025-10-19T17:42:38Z
  ```

- **`seconds_since_epoch`** - Get seconds since Unix epoch
  ```bash
  epoch=$(seconds_since_epoch)
  ```

### HTTP Response Parsing

- **`parse_http_response <response>`** - Parse curl response with status code
  ```bash
  response=$(curl -s -w "\n%{http_code}" "https://api.example.com")
  eval "$(parse_http_response "$response")"
  # Now $HTTP_CODE and $HTTP_BODY are available
  echo "Status: $HTTP_CODE"
  echo "Body: $HTTP_BODY"
  ```

### Utilities

- **`json_escape <string>`** - Escape a string for use in JSON
  ```bash
  escaped=$(json_escape "string with \"quotes\"")
  ```

- **`require_command <cmd> [hint]`** - Check if command exists, fail with message
  ```bash
  require_command "jq" "Install with: brew install jq"
  ```

- **`sleep_with_progress <seconds> [message]`** - Sleep with progress indicator
  ```bash
  sleep_with_progress 10 "Waiting for Lambda"
  ```

### Logging

- **`log_info <message>`** - Print info message with timestamp
- **`log_success <message>`** - Print success message with timestamp  
- **`log_warning <message>`** - Print warning message with timestamp
- **`log_error <message>`** - Print error message to stderr with timestamp

```bash
log_info "Deployment starting"
log_success "Deployment complete"
log_warning "Rate limit approaching"
log_error "Deployment failed"
```

## Platform Detection

The compatibility layer automatically detects the platform and exports the `$PLATFORM` variable:

```bash
source platform-compat.sh

if [ "$PLATFORM" = "macos" ]; then
    echo "Running on macOS"
elif [ "$PLATFORM" = "linux" ]; then
    echo "Running on Linux"
fi
```

## Debugging

Enable debug mode to see platform detection information:

```bash
DEBUG=1 source platform-compat.sh
# Output:
# Platform compatibility layer loaded
#   Platform: macos
#   OS Type: darwin21.0
```

## Scripts Using This Layer

Currently, these scripts source the compatibility layer:

- **`lambda-wait.sh`** - Lambda deployment verification (uses `get_last_line`, `all_but_last_line`)
- **`deploy.sh`** - One-command deployment wrapper (uses `get_last_line`, `all_but_last_line`)

**Note**: `codebuild-runner-with-digest.sh` does not use this layer because it executes within AWS CodeBuild (always Linux), so platform compatibility is not needed.

## Contributing

When writing new scripts:

1. **Always source** `platform-compat.sh` at the beginning
2. **Use the provided functions** instead of platform-specific commands
3. **Test on both macOS and Linux** when possible
4. **Add new functions** to the compatibility layer if you encounter new cross-platform issues

### Common Replacements

| Instead of | Use |
|------------|-----|
| `head -n -1` | `all_but_last_line` |
| `tail -n 1` | `get_last_line` |
| `readlink -f` | `absolute_path` |
| `stat -c` / `stat -f` | `file_modified_time` or `file_size_human` |
| `date --iso-8601` | `iso_timestamp` |

## Future Enhancements

Potential additions to the compatibility layer:

- Process management utilities
- Network testing helpers
- AWS CLI response parsers
- Retry logic helpers
- Color output support detection

## Related Files

- `platform-compat.sh` - The compatibility layer implementation
- `lambda-wait.sh` - Example usage in Lambda deployment
- `deploy.sh` - Example usage in deployment wrapper
