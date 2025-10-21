#!/bin/bash

# Platform Compatibility Layer
# Provides cross-platform compatible commands for use in all scripts
# Usage: source this file at the beginning of your script

# Detect operating system
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    PATH_SEP="/"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    PATH_SEP="/"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    PLATFORM="windows"
    PATH_SEP="\\"
    # Git Bash on Windows uses forward slashes but we need to be aware
    if command -v cygpath &> /dev/null; then
        PLATFORM="windows-gitbash"
        PATH_SEP="/"  # Git Bash translates paths
    fi
else
    PLATFORM="unknown"
    PATH_SEP="/"
fi

# Export platform for scripts that need it
export PLATFORM
export PATH_SEP

#
# Function: normalize_path
# Purpose: Normalize path separators for current platform
# Usage: normalized=$(normalize_path "/path/to/file")
#
normalize_path() {
    local path="$1"
    
    if [ "$PLATFORM" = "windows" ]; then
        # Convert forward slashes to backslashes for native Windows
        echo "$path" | sed 's/\//\\/g'
    elif [ "$PLATFORM" = "windows-gitbash" ]; then
        # Git Bash handles paths automatically, but ensure forward slashes
        echo "$path" | sed 's/\\/\//g'
    else
        # Unix-like systems: ensure forward slashes
        echo "$path" | sed 's/\\/\//g'
    fi
}

#
# Function: to_windows_path
# Purpose: Convert Unix-style path to Windows-style (if on Windows)
# Usage: winpath=$(to_windows_path "/c/Users/name/file")
#
to_windows_path() {
    local path="$1"
    
    if [ "$PLATFORM" = "windows-gitbash" ] && command -v cygpath &> /dev/null; then
        cygpath -w "$path"
    elif [ "$PLATFORM" = "windows" ]; then
        # Basic conversion for native Windows
        echo "$path" | sed 's/^\/\([a-zA-Z]\)\//\1:\\/g' | sed 's/\//\\/g'
    else
        # Not on Windows, return as-is
        echo "$path"
    fi
}

#
# Function: to_unix_path
# Purpose: Convert Windows-style path to Unix-style (always)
# Usage: unixpath=$(to_unix_path "C:\Users\name\file")
#
to_unix_path() {
    local path="$1"
    
    if [ "$PLATFORM" = "windows-gitbash" ] && command -v cygpath &> /dev/null; then
        cygpath -u "$path"
    else
        # Basic conversion: C:\path\to\file -> /c/path/to/file
        echo "$path" | sed 's/\\/\//g' | sed 's/^\([A-Za-z]\):/\/\L\1/g'
    fi
}

#
# Function: join_path
# Purpose: Join path components with correct separator
# Usage: fullpath=$(join_path "$dir" "$file")
#
join_path() {
    local result="$1"
    shift
    
    for component in "$@"; do
        # Remove leading/trailing slashes from component
        component="${component#/}"
        component="${component%/}"
        
        if [ -n "$component" ]; then
            result="${result}/${component}"
        fi
    done
    
    normalize_path "$result"
}

#
# Function: get_script_dir
# Purpose: Get the directory containing the calling script (cross-platform)
# Usage: SCRIPT_DIR=$(get_script_dir)
# Note: Should be called early in script, before changing directories
#
get_script_dir() {
    local source="${BASH_SOURCE[1]}"
    local dir=""
    
    # Resolve symlinks
    while [ -h "$source" ]; do
        dir="$(cd -P "$(dirname "$source")" && pwd)"
        source="$(readlink "$source")"
        [[ $source != /* ]] && source="$dir/$source"
    done
    
    dir="$(cd -P "$(dirname "$source")" && pwd)"
    normalize_path "$dir"
}

#
# Function: seq_compat
# Purpose: Cross-platform sequence generator (alternative to seq command)
# Usage: seq_compat 1 10  or  for i in $(seq_compat 1 5); do ... done
#
seq_compat() {
    if command -v seq &> /dev/null; then
        seq "$@"
    else
        # Fallback for systems without seq (rare, but possible)
        local start=$1
        local end=$2
        local i=$start
        while [ $i -le $end ]; do
            echo $i
            i=$((i + 1))
        done
    fi
}

#
# Function: timeout_compat
# Purpose: Cross-platform timeout command
# Usage: timeout_compat 30 command args...
#
timeout_compat() {
    local duration=$1
    shift
    
    if command -v timeout &> /dev/null; then
        timeout "$duration" "$@"
    elif command -v gtimeout &> /dev/null; then
        # macOS with coreutils installed
        gtimeout "$duration" "$@"
    else
        # Fallback: run command without timeout
        log_warning "timeout command not available, running without timeout"
        "$@"
    fi
}

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
# Function: date_iso
# Purpose: Cross-platform ISO date formatting
# Usage: date_iso
#
date_iso() {
    if [ "$PLATFORM" = "macos" ]; then
        date -u +"%Y-%m-%dT%H:%M:%SZ"
    else
        date -u --iso-8601=seconds 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ"
    fi
}

#
# Function: date_seconds
# Purpose: Cross-platform seconds since epoch
# Usage: date_seconds
#
date_seconds() {
    date +%s
}

#
# Function: mktemp_compat
# Purpose: Cross-platform temporary file creation
# Usage: tmpfile=$(mktemp_compat)
#
mktemp_compat() {
    if [ "$PLATFORM" = "macos" ]; then
        mktemp -t "knock-lambda"
    else
        mktemp -t "knock-lambda.XXXXXXXXXX"
    fi
}

#
# Function: get_temp_dir
# Purpose: Get the system's temporary directory (cross-platform)
# Usage: tmpdir=$(get_temp_dir)
#
get_temp_dir() {
    if [ -n "${TMPDIR:-}" ]; then
        normalize_path "$TMPDIR"
    elif [ -n "${TEMP:-}" ]; then
        normalize_path "$TEMP"
    elif [ -n "${TMP:-}" ]; then
        normalize_path "$TMP"
    elif [ -d "/tmp" ]; then
        echo "/tmp"
    else
        echo "."
    fi
}

#
# Function: safe_file_path
# Purpose: Create a safe file path that works on all platforms
# Usage: safe_path=$(safe_file_path "/tmp/image_uri_digest.txt")
#
safe_file_path() {
    local path="$1"
    local normalized
    
    # Normalize the path
    normalized=$(normalize_path "$path")
    
    # If path is absolute, use it
    if [[ "$normalized" == /* ]] || [[ "$normalized" =~ ^[A-Za-z]: ]]; then
        echo "$normalized"
    else
        # Make it relative to current directory
        echo "$(pwd)/$normalized"
    fi
}

#
# Function: realpath_compat
# Purpose: Cross-platform realpath (absolute path resolution)
# Usage: realpath_compat "path/to/file"
#
realpath_compat() {
    local path="$1"
    
    if command -v realpath &> /dev/null; then
        realpath "$path"
    elif command -v grealpath &> /dev/null; then
        grealpath "$path"
    else
        # Use our existing absolute_path function
        absolute_path "$path"
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
