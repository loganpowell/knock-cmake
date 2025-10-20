#!/bin/bash

# Platform Compatibility Layer
# Provides cross-platform compatible commands for use in all scripts
# Usage: source this file at the beginning of your script

# Detect operating system
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
else
    PLATFORM="unknown"
fi

# Export platform for scripts that need it
export PLATFORM

#
# Function: all_but_last_line
# Purpose: Print all lines except the last (cross-platform alternative to head -n -1)
# Usage: echo "$output" | all_but_last_line
#
all_but_last_line() {
    sed '$d'
}

#
# Function: get_last_line
# Purpose: Get the last line of input
# Usage: echo "$output" | get_last_line
#
get_last_line() {
    tail -n 1
}

#
# Function: absolute_path
# Purpose: Get absolute path of a file/directory (cross-platform)
# Usage: absolute_path "relative/path"
#
absolute_path() {
    local path="$1"
    if [ "$PLATFORM" = "macos" ]; then
        # macOS doesn't have readlink -f by default
        if command -v greadlink &> /dev/null; then
            greadlink -f "$path"
        else
            # Fallback: use Python if available
            if command -v python3 &> /dev/null; then
                python3 -c "import os; print(os.path.abspath('$path'))"
            else
                # Last resort: cd and pwd
                (cd "$(dirname "$path")" && echo "$PWD/$(basename "$path")")
            fi
        fi
    else
        readlink -f "$path"
    fi
}

#
# Function: file_modified_time
# Purpose: Get file modification timestamp (cross-platform)
# Usage: file_modified_time "path/to/file"
#
file_modified_time() {
    local path="$1"
    if [ "$PLATFORM" = "macos" ]; then
        stat -f "%m" "$path"
    else
        stat -c "%Y" "$path"
    fi
}

#
# Function: file_size_human
# Purpose: Get human-readable file size (cross-platform)
# Usage: file_size_human "path/to/file"
#
file_size_human() {
    local path="$1"
    if [ "$PLATFORM" = "macos" ]; then
        stat -f "%z" "$path" | numfmt --to=iec 2>/dev/null || stat -f "%z" "$path"
    else
        stat -c "%s" "$path" | numfmt --to=iec 2>/dev/null || stat -c "%s" "$path"
    fi
}

#
# Function: iso_timestamp
# Purpose: Get current timestamp in ISO 8601 format (cross-platform)
# Usage: iso_timestamp
#
iso_timestamp() {
    if [ "$PLATFORM" = "macos" ]; then
        date -u +"%Y-%m-%dT%H:%M:%SZ"
    else
        date -u --iso-8601=seconds
    fi
}

#
# Function: seconds_since_epoch
# Purpose: Get seconds since Unix epoch (cross-platform)
# Usage: seconds_since_epoch
#
seconds_since_epoch() {
    date +%s
}

#
# Function: sleep_with_progress
# Purpose: Sleep with a progress indicator
# Usage: sleep_with_progress 10 "Waiting for Lambda"
#
sleep_with_progress() {
    local duration=$1
    local message="${2:-Waiting}"
    local i=0
    while [ $i -lt $duration ]; do
        printf "\r%s... %ds" "$message" $((duration - i))
        sleep 1
        i=$((i + 1))
    done
    printf "\r%s... done\n" "$message"
}

#
# Function: parse_http_response
# Purpose: Parse curl response that includes status code
# Usage: 
#   response=$(curl -s -w "\n%{http_code}" ...)
#   eval "$(parse_http_response "$response")"
#   # Now $HTTP_CODE and $HTTP_BODY are available
#
parse_http_response() {
    local response="$1"
    local code
    local body
    
    code=$(echo "$response" | get_last_line)
    body=$(echo "$response" | all_but_last_line)
    
    # Output as eval-able variables
    printf 'HTTP_CODE="%s"\n' "$code"
    printf 'HTTP_BODY=%s\n' "$(printf '%q' "$body")"
}

#
# Function: json_escape
# Purpose: Escape a string for use in JSON
# Usage: json_escape "string with \"quotes\""
#
json_escape() {
    local string="$1"
    if command -v jq &> /dev/null; then
        printf '%s' "$string" | jq -Rs .
    else
        # Fallback: basic escaping
        printf '%s' "$string" | sed 's/\\/\\\\/g; s/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g'
    fi
}

#
# Function: require_command
# Purpose: Check if a command exists, exit with error if not
# Usage: require_command "jq" "Install with: brew install jq"
#
require_command() {
    local cmd="$1"
    local hint="${2:-}"
    
    if ! command -v "$cmd" &> /dev/null; then
        echo "❌ Error: Required command '$cmd' not found" >&2
        if [ -n "$hint" ]; then
            echo "   $hint" >&2
        fi
        return 1
    fi
    return 0
}

#
# Function: log_info
# Purpose: Print info message with timestamp
# Usage: log_info "Deployment starting"
#
log_info() {
    echo "[$(iso_timestamp)] ℹ️  $*"
}

#
# Function: log_success
# Purpose: Print success message with timestamp
# Usage: log_success "Deployment complete"
#
log_success() {
    echo "[$(iso_timestamp)] ✅ $*"
}

#
# Function: log_warning
# Purpose: Print warning message with timestamp
# Usage: log_warning "Rate limit approaching"
#
log_warning() {
    echo "[$(iso_timestamp)] ⚠️  $*"
}

#
# Function: log_error
# Purpose: Print error message with timestamp
# Usage: log_error "Deployment failed"
#
log_error() {
    echo "[$(iso_timestamp)] ❌ $*" >&2
}

# Print platform info if sourced with DEBUG
if [ "${DEBUG:-0}" = "1" ]; then
    echo "Platform compatibility layer loaded"
    echo "  Platform: $PLATFORM"
    echo "  OS Type: $OSTYPE"
fi
