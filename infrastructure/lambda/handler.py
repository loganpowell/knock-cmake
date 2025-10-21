"""
AWS Lambda handler for Knock ACSM conversion service.

This module provides the Lambda function handler that processes ACSM files
using the Knock binary and returns converted files (PDF/EPUB).

Updated with digest-based deployment system for reliable container updates.
"""

import json
import subprocess
import os
import tempfile

import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import urllib.request
import urllib.error
import shutil
import logging
import traceback
import sys

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add formatter for better log structure
for handler in logger.handlers:
    handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(funcName)s:%(lineno)d - %(message)s")
    )


def _parse_knock_error(stderr: str) -> Optional[str]:
    """
    Parse stderr from Knock conversion to identify specific error types.

    Args:
        stderr: Standard error output from Knock

    Returns:
        Error type identifier or None if not recognized
        - "E_GOOGLE_DEVICE_LIMIT_REACHED"
        - "E_ADEPT_REQUEST_EXPIRED"
    """
    if "E_GOOGLE_DEVICE_LIMIT_REACHED" in stderr:
        return "E_GOOGLE_DEVICE_LIMIT_REACHED"
    elif "E_ADEPT_REQUEST_EXPIRED" in stderr:
        return "E_ADEPT_REQUEST_EXPIRED"
    return None


def _reset_device_credentials_in_s3():
    """
    Delete device credentials from S3 to force regeneration.
    Equivalent to scripts/reset_device_credentials.sh
    """
    logger.info("Resetting device credentials in S3...")
    device_bucket = os.environ.get("DEVICE_CREDENTIALS_BUCKET")
    if not device_bucket:
        logger.warning("DEVICE_CREDENTIALS_BUCKET not configured, cannot reset")
        return False

    s3 = boto3.client("s3")
    credential_files = ["activation.xml", "device.xml", "devicesalt"]

    deleted_count = 0
    try:
        for filename in credential_files:
            s3_key = f"credentials/{filename}"
            try:
                s3.delete_object(Bucket=device_bucket, Key=s3_key)
                logger.info(f"Deleted credential file from S3: {filename}")
                deleted_count += 1
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code not in ("NoSuchKey", "404", "NotFound"):
                    logger.warning(f"Failed to delete {filename}: {e}")
            except Exception as e:
                logger.warning(f"Failed to delete {filename}: {e}")
    except Exception as e:
        logger.error(f"Error resetting device credentials in S3: {e}")
        return False

    logger.info(f"Reset complete: deleted {deleted_count} credential files")
    return deleted_count > 0


def activate_device_with_adept(force_reset: bool = False):
    """
    Run adept_activate to generate device credentials if they don't exist.
    Uses anonymous activation (no Adobe ID required).

    Args:
        force_reset: If True, clear existing credentials before activating
    """
    logger.info("=" * 60)
    logger.info("STARTING DEVICE ACTIVATION WITH ADEPT_ACTIVATE")
    logger.info("=" * 60)

    credentials_dir = "/tmp/knock/acsm"

    # Handle force reset
    if force_reset:
        logger.info("Force reset requested - clearing existing credentials...")
        if os.path.exists(credentials_dir):
            shutil.rmtree(credentials_dir)
            logger.info("Cleared local credentials directory")
        _reset_device_credentials_in_s3()

    # Check if credentials already exist before clearing
    credential_files = ["activation.xml", "device.xml", "devicesalt"]
    if os.path.exists(credentials_dir):
        existing_files = [
            f
            for f in credential_files
            if os.path.exists(os.path.join(credentials_dir, f))
        ]
        logger.info(f"Found existing directory with files: {existing_files}")

        if len(existing_files) == len(credential_files):
            logger.info("✓ All device credentials already exist, skipping activation")
            return True

        # Directory exists but incomplete - clear it to avoid interactive prompt
        logger.info(
            "Clearing incomplete credentials directory to avoid interactive prompt..."
        )
        shutil.rmtree(credentials_dir)

    # Create fresh directory
    os.makedirs(credentials_dir, exist_ok=True)
    logger.info(f"Created fresh credentials directory: {credentials_dir}")

    # Run adept_activate to generate credentials
    adept_binary = os.path.join(
        os.environ["LAMBDA_TASK_ROOT"], "knock", "adept_activate"
    )
    logger.info(f"Binary path: {adept_binary}")
    logger.info(f"Binary exists: {os.path.exists(adept_binary)}")

    if not os.path.exists(adept_binary):
        logger.error(f"✗ adept_activate binary not found at {adept_binary}")
        return False

    # Log binary info
    try:
        stat_info = os.stat(adept_binary)
        logger.info(f"Binary size: {stat_info.st_size} bytes")
        logger.info(f"Binary permissions: {oct(stat_info.st_mode)}")
    except Exception as e:
        logger.warning(f"Could not stat binary: {e}")

    # Set up environment
    lib_path = os.path.join(os.environ["LAMBDA_TASK_ROOT"], "lib")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{lib_path}:{env.get('LD_LIBRARY_PATH', '')}"
    logger.info(f"LD_LIBRARY_PATH: {env['LD_LIBRARY_PATH']}")

    # Check memory before running
    try:
        with open("/proc/meminfo", "r") as f:
            meminfo = f.read()
            for line in meminfo.split("\n"):
                if "MemAvailable" in line or "MemFree" in line:
                    logger.info(line.strip())
    except Exception as e:
        logger.warning(f"Could not read meminfo: {e}")

    cmd = [adept_binary, "-a", "-v", "-v", "-O", credentials_dir]
    logger.info(f"Executing command: {' '.join(cmd)}")
    logger.info("Starting adept_activate (timeout: 120s)...")

    # Write output to temp files instead of buffering in memory (avoid OOM)
    stdout_file = "/tmp/adept_activate_stdout.log"
    stderr_file = "/tmp/adept_activate_stderr.log"

    try:
        with open(stdout_file, "w") as out, open(stderr_file, "w") as err:
            result = subprocess.run(
                cmd,
                stdout=out,
                stderr=err,
                timeout=120,
                env=env,
                input="y\n",  # Answer the overwrite prompt with 'y'
                text=True,
            )

        logger.info(f"Process completed with return code: {result.returncode}")

        # Read and log output files (with size limits)
        try:
            with open(stdout_file, "r") as f:
                stdout_lines = f.readlines()
                logger.info(f"STDOUT: {len(stdout_lines)} lines")
                if stdout_lines:
                    logger.info("=== ADEPT_ACTIVATE STDOUT (first 30 lines) ===")
                    for i, line in enumerate(stdout_lines[:30], 1):
                        logger.info(f"  {i}: {line.rstrip()}")
                    if len(stdout_lines) > 30:
                        logger.info(f"  ... ({len(stdout_lines) - 30} more lines)")
        except Exception as e:
            logger.warning(f"Could not read stdout file: {e}")

        try:
            with open(stderr_file, "r") as f:
                stderr_lines = f.readlines()
                logger.info(f"STDERR: {len(stderr_lines)} lines")
                if stderr_lines:
                    logger.warning("=== ADEPT_ACTIVATE STDERR (first 30 lines) ===")
                    for i, line in enumerate(stderr_lines[:30], 1):
                        logger.warning(f"  {i}: {line.rstrip()}")
                    if len(stderr_lines) > 30:
                        logger.warning(f"  ... ({len(stderr_lines) - 30} more lines)")
        except Exception as e:
            logger.warning(f"Could not read stderr file: {e}")

        if result.returncode != 0:
            logger.error(
                f"✗ adept_activate failed with return code {result.returncode}"
            )
            return False

        # Verify credentials were created
        created_files = [
            f
            for f in credential_files
            if os.path.exists(os.path.join(credentials_dir, f))
        ]
        logger.info(f"Created credential files: {created_files}")

        # Cleanup temp log files
        for log_file in [stdout_file, stderr_file]:
            try:
                if os.path.exists(log_file):
                    os.remove(log_file)
            except Exception as e:
                logger.warning(f"Could not remove {log_file}: {e}")

        if len(created_files) == len(credential_files):
            logger.info("✓ Device credentials generated successfully")
            return True
        else:
            logger.error(
                f"✗ Not all credential files were created. Missing: {set(credential_files) - set(created_files)}"
            )
            return False

    except subprocess.TimeoutExpired as e:
        logger.error("✗ adept_activate TIMED OUT after 120 seconds")
        logger.error(
            "This suggests the process is hanging - likely network issue or interactive prompt"
        )

        # Try to read partial output from files
        try:
            if os.path.exists(stdout_file):
                with open(stdout_file, "r") as f:
                    lines = f.readlines()[:20]
                    if lines:
                        logger.info("Partial stdout before timeout:")
                        for line in lines:
                            logger.info(f"  {line.rstrip()}")
        except Exception as ex:
            logger.warning(f"Could not read partial stdout: {ex}")

        try:
            if os.path.exists(stderr_file):
                with open(stderr_file, "r") as f:
                    lines = f.readlines()[:20]
                    if lines:
                        logger.warning("Partial stderr before timeout:")
                        for line in lines:
                            logger.warning(f"  {line.rstrip()}")
        except Exception as ex:
            logger.warning(f"Could not read partial stderr: {ex}")

        return False

    except Exception as e:
        logger.error(f"✗ Unexpected error running adept_activate: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(traceback.format_exc())
        return False


def sync_device_credentials_from_s3():
    """
    Download device credentials from S3 to /tmp/knock/acsm if they exist.
    This ensures the same device is used across Lambda invocations,
    avoiding the Google device limit error.
    """
    logger.info("Syncing device credentials from S3...")
    device_bucket = os.environ.get("DEVICE_CREDENTIALS_BUCKET")
    if not device_bucket:
        logger.warning("DEVICE_CREDENTIALS_BUCKET not configured")
        return False

    logger.info(f"S3 bucket: {device_bucket}")

    s3 = boto3.client("s3")
    credentials_dir = "/tmp/knock/acsm"
    os.makedirs(credentials_dir, exist_ok=True)

    # List of credential files to sync
    credential_files = ["activation.xml", "device.xml", "devicesalt"]

    downloaded_count = 0
    try:
        for filename in credential_files:
            s3_key = f"credentials/{filename}"
            local_path = os.path.join(credentials_dir, filename)

            try:
                s3.download_file(device_bucket, s3_key, local_path)
                print(f"Downloaded device credential: {filename}")
                downloaded_count += 1
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code in ("NoSuchKey", "404", "NotFound"):
                    print(f"Device credential not found in S3: {filename}")
                else:
                    print(f"Failed to download {filename}: {e}")
            except Exception as e:
                print(f"Failed to download {filename}: {e}")
    except Exception as e:
        print(f"Error syncing device credentials from S3: {e}")

    # Return True if all files were downloaded
    return downloaded_count == len(credential_files)


def sync_device_credentials_to_s3():
    """
    Upload device credentials from /tmp/knock/acsm to S3 for persistence.
    This is called after successful device activation.
    """
    device_bucket = os.environ.get("DEVICE_CREDENTIALS_BUCKET")
    if not device_bucket:
        return

    s3 = boto3.client("s3")
    credentials_dir = "/tmp/knock/acsm"

    if not os.path.exists(credentials_dir):
        return

    # Upload all files in the credentials directory
    try:
        for filename in os.listdir(credentials_dir):
            local_path = os.path.join(credentials_dir, filename)
            if os.path.isfile(local_path):
                s3_key = f"credentials/{filename}"
                try:
                    s3.upload_file(local_path, device_bucket, s3_key)
                    print(f"Uploaded device credential: {filename}")
                except Exception as e:
                    print(f"Failed to upload {filename}: {e}")
    except Exception as e:
        print(f"Error syncing device credentials to S3: {e}")


def _find_param_by_pattern(body: Dict[str, Any], *patterns: str) -> Optional[Any]:
    """Find a parameter value by matching keys against patterns (case-insensitive).

    Args:
        body: Request body dictionary
        patterns: One or more substring patterns to match (all must be present)

    Returns:
        The first matching value found, or None
    """
    patterns_lower = [p.lower() for p in patterns]
    for key, value in body.items():
        key_lower = key.lower()
        if all(pattern in key_lower for pattern in patterns_lower):
            return value
    return None


def _sanitize_key_component(name: str) -> str:
    """Sanitize a filename component for safe S3 key usage."""
    import re

    # Replace path separators and control chars
    name = re.sub(r"[\r\n\t\\/]+", "_", name)
    # Allow alphanum, dash, underscore, dot, and space -> convert spaces to underscores
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    # Collapse repeated underscores
    name = re.sub(r"_+", "_", name).strip("._-")
    return name[:200] if name else "input"


def _get_book_title_from_acsm_content(acsm_content: str) -> Optional[str]:
    """
    Extract book title from ACSM XML content.

    Supports two formats:
    1. ACSM with <metadata><dc:title> element (preferred)
    2. ACSM with <src> URL containing the title in the filename

    Args:
        acsm_content: The ACSM file content as a string

    Returns:
        Book title if found, otherwise None
    """
    try:
        import xml.etree.ElementTree as ET
        from urllib.parse import urlparse, unquote

        root = ET.fromstring(acsm_content)

        # ACSM and Dublin Core namespaces
        namespaces = {
            "adept": "http://ns.adobe.com/adept",
            "dc": "http://purl.org/dc/elements/1.1/",
        }

        # Format 1: Try to find dc:title in metadata (most reliable)
        metadata = root.find(".//metadata", namespaces)
        if metadata is not None:
            title_elem = metadata.find(".//dc:title", namespaces)
            if title_elem is not None and title_elem.text:
                title = title_elem.text.strip()
                if title:
                    return title

        # Format 2: Fall back to extracting from <src> URL
        src_elem = root.find(".//adept:src", namespaces)
        if src_elem is None:
            # Try without namespace
            src_elem = root.find(".//src")

        if src_elem is not None and src_elem.text:
            url = src_elem.text.strip()
            # Extract filename from URL
            path = urlparse(url).path
            candidate = os.path.basename(path)
            if candidate:
                filename = unquote(candidate)
                # Remove extension to get the title
                title = os.path.splitext(filename)[0]
                if title and title.lower() not in ("", "input"):
                    return title

    except Exception as e:
        logger.warning(f"Could not extract book title from ACSM content: {e}")

    return None


def _derive_acsm_filename(body: Dict[str, Any], acsm_url: Optional[str]) -> str:
    """Determine the original ACSM filename from the request body."""
    from urllib.parse import urlparse, unquote

    # Prefer explicit filename if provided (keys containing "acsm" and "filename" or "name")
    explicit = _find_param_by_pattern(
        body, "acsm", "filename"
    ) or _find_param_by_pattern(body, "acsm", "name")
    # Also check for standalone "filename" parameter
    if not explicit:
        explicit = body.get("filename") or body.get("Filename") or body.get("fileName")
    if isinstance(explicit, str) and explicit.strip():
        fname = explicit.strip()
    else:
        fname = "input.acsm"
        if isinstance(acsm_url, str) and acsm_url:
            try:
                path = urlparse(acsm_url).path
                candidate = os.path.basename(path)
                if candidate:
                    fname = unquote(candidate)
                    # Ensure it ends with .acsm for clarity
                    if not fname.lower().endswith(".acsm"):
                        fname = f"{fname}.acsm"
            except Exception:
                pass
    # Final sanitize
    base, ext = os.path.splitext(fname)
    base = _sanitize_key_component(base or "input")
    ext = ".acsm"
    return f"{base}{ext}"


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle Lambda invocation for Knock ACSM conversion.

    Args:
        event: Lambda event containing either 'acsm_url' or 'acsm_content'
        context: Lambda context (unused)

    Returns:
        Dict containing response with converted files or error information
    """
    logger.info("\n" + "#" * 80)
    logger.info("#  KNOCK LAMBDA INVOCATION")
    logger.info("#" * 80)
    logger.info(f"Request ID: {context.aws_request_id if context else 'N/A'}")
    logger.info(f"Function version: {context.function_version if context else 'N/A'}")
    logger.info(f"Memory limit: {context.memory_limit_in_mb if context else 'N/A'} MB")

    try:
        # Parse the request body first to validate inputs early
        if "body" in event and event["body"]:
            try:
                body = json.loads(event["body"])  # Function URL JSON body
            except json.JSONDecodeError:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid JSON in request body"}),
                }
        else:
            # Direct invocation or already-parsed event
            body = event or {}

        # Validate required parameters before any heavy work
        # Look for keys containing "acsm" and "url" or "acsm" and "content"
        acsm_url = _find_param_by_pattern(body, "acsm", "url")
        acsm_content = _find_param_by_pattern(body, "acsm", "content")

        if not acsm_url and not acsm_content:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "error": "Either a parameter containing 'acsm' and 'url' or 'acsm' and 'content' is required"
                    }
                ),
            }

        # Derive original ACSM filename and base
        original_acsm_filename = _derive_acsm_filename(body, acsm_url)
        original_base = os.path.splitext(original_acsm_filename)[0]

        # If we got a generic "input" filename and have ACSM content, try to extract the real title
        if original_base == "input" and acsm_content:
            extracted_title = _get_book_title_from_acsm_content(acsm_content)
            if extracted_title:
                original_base = _sanitize_key_component(extracted_title)
                original_acsm_filename = f"{original_base}.acsm"
                logger.info(f"Extracted title from ACSM content: {extracted_title}")

        logger.info(f"Original ACSM filename (derived): {original_acsm_filename}")

        # Ensure device credentials are available only after input validation
        credentials_exist = sync_device_credentials_from_s3()
        if not credentials_exist:
            print(
                "No credentials in S3, generating new credentials with adept_activate..."
            )
            if not activate_device_with_adept():
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(
                        {
                            "error": "Failed to activate device. Could not generate credentials."
                        }
                    ),
                }
            # Upload newly generated credentials to S3
            sync_device_credentials_to_s3()
        else:
            print("Using existing credentials from S3")

        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as tmp_dir:
            acsm_path = os.path.join(tmp_dir, "input.acsm")

            # Download or write ACSM file
            if acsm_url:
                try:
                    # Download ACSM file
                    urllib.request.urlretrieve(acsm_url, acsm_path)
                except urllib.error.URLError as e:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps(
                            {"error": f"Failed to download ACSM file: {str(e)}"}
                        ),
                    }
            else:
                # Write ACSM content to file
                if acsm_content:
                    with open(acsm_path, "w", encoding="utf-8") as f:
                        f.write(acsm_content)
                else:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "ACSM content is empty"}),
                    }

            # Run the Knock conversion
            knock_binary = os.path.join(
                os.environ["LAMBDA_TASK_ROOT"], "knock", "knock"
            )

            if not os.path.exists(knock_binary):
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(
                        {"error": "Knock binary not found at expected location"}
                    ),
                }

            # Ensure shared libraries can be found
            lib_path = os.path.join(os.environ["LAMBDA_TASK_ROOT"], "lib")
            env = os.environ.copy()
            env["LD_LIBRARY_PATH"] = f"{lib_path}:{env.get('LD_LIBRARY_PATH', '')}"

            # Log environment for debugging
            logger.info("=" * 60)
            logger.info("RUNNING KNOCK CONVERSION")
            logger.info("=" * 60)
            logger.info(f"LD_LIBRARY_PATH: {env['LD_LIBRARY_PATH']}")
            logger.info(f"Knock binary path: {knock_binary}")
            logger.info(f"ACSM path: {acsm_path}")
            logger.info(f"Working directory: {tmp_dir}")

            # Execute Knock conversion
            try:
                result = subprocess.run(
                    [knock_binary, acsm_path],
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minute timeout
                    env=env,  # Use environment with updated LD_LIBRARY_PATH
                )

                # Sync device credentials immediately after first run
                # This ensures they're saved even if conversion fails
                sync_device_credentials_to_s3()

                # Log the full output for debugging
                logger.info(f"Knock stdout: {result.stdout}")
                logger.info(f"Knock stderr: {result.stderr}")
                logger.info(f"Knock return code: {result.returncode}")

            except subprocess.TimeoutExpired:
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(
                        {"error": "Knock conversion timed out after 10 minutes"}
                    ),
                }

            if result.returncode != 0:
                # Parse error to determine error type
                error_type = _parse_knock_error(result.stderr)

                # Handle E_GOOGLE_DEVICE_LIMIT_REACHED
                if error_type == "E_GOOGLE_DEVICE_LIMIT_REACHED":
                    # Use the already-derived filename, convert to user-friendly title
                    book_title = original_base.replace("_", " ")
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps(
                            {
                                "error": f"You have already exhausted the download limit for {book_title}",
                                "error_type": "DEVICE_LIMIT_REACHED",
                                "book_title": book_title,
                                "details": "This book has been downloaded the maximum number of times allowed by the publisher.",
                                "stderr": result.stderr,
                                "stdout": result.stdout,
                            }
                        ),
                    }

                # Handle E_ADEPT_REQUEST_EXPIRED - reset credentials and retry once
                elif error_type == "E_ADEPT_REQUEST_EXPIRED":
                    logger.warning(
                        "Detected E_ADEPT_REQUEST_EXPIRED - resetting credentials and retrying..."
                    )

                    # Reset credentials
                    if not activate_device_with_adept(force_reset=True):
                        return {
                            "statusCode": 500,
                            "headers": {"Content-Type": "application/json"},
                            "body": json.dumps(
                                {
                                    "error": "Failed to reset device credentials after expired request error",
                                    "error_type": "CREDENTIAL_RESET_FAILED",
                                    "stderr": result.stderr,
                                }
                            ),
                        }

                    # Retry the conversion
                    logger.info("Retrying Knock conversion with fresh credentials...")
                    try:
                        result = subprocess.run(
                            [knock_binary, acsm_path],
                            cwd=tmp_dir,
                            capture_output=True,
                            text=True,
                            timeout=600,
                            env=env,
                        )

                        # Sync new credentials
                        sync_device_credentials_to_s3()

                        logger.info(f"Retry - Knock stdout: {result.stdout}")
                        logger.info(f"Retry - Knock stderr: {result.stderr}")
                        logger.info(f"Retry - Knock return code: {result.returncode}")

                    except subprocess.TimeoutExpired:
                        return {
                            "statusCode": 500,
                            "headers": {"Content-Type": "application/json"},
                            "body": json.dumps(
                                {
                                    "error": "Knock conversion retry timed out after 10 minutes"
                                }
                            ),
                        }

                    # Check if retry succeeded
                    if result.returncode != 0:
                        return {
                            "statusCode": 500,
                            "headers": {"Content-Type": "application/json"},
                            "body": json.dumps(
                                {
                                    "error": "Knock conversion failed after credential reset and retry",
                                    "stderr": result.stderr,
                                    "stdout": result.stdout,
                                    "return_code": result.returncode,
                                }
                            ),
                        }

                    # Retry succeeded - continue to success path below
                    logger.info("✓ Retry succeeded after credential reset")

                else:
                    # Generic error handling for other errors
                    return {
                        "statusCode": 500,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps(
                            {
                                "error": "Knock conversion failed",
                                "stderr": result.stderr,
                                "stdout": result.stdout,
                                "return_code": result.returncode,
                            }
                        ),
                    }

            # Handle output files
            output_bucket = os.environ.get("OUTPUT_BUCKET")
            if output_bucket:
                return _handle_s3_output(
                    tmp_dir,
                    output_bucket,
                    result.stdout,
                    original_base,
                    original_acsm_filename,
                )
            else:
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(
                        {"message": "Conversion successful", "stdout": result.stdout}
                    ),
                }

    except Exception as e:
        logger.error("\n" + "!" * 80)
        logger.error("!  UNHANDLED EXCEPTION IN LAMBDA HANDLER")
        logger.error("!" * 80)
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception message: {str(e)}")
        logger.error("Stack trace:")
        logger.error(traceback.format_exc())

        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "error": f"Unexpected error: {str(e)}",
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc().split("\n")[
                        -10:
                    ],  # Last 10 lines
                }
            ),
        }


def _handle_s3_output(
    tmp_dir: str,
    output_bucket: str,
    stdout: str,
    original_base: str,
    original_acsm_filename: str,
) -> Dict[str, Any]:
    """
    Handle uploading converted files to S3, preserving the original ACSM filename base.

    Args:
        tmp_dir: Temporary directory containing converted files
        output_bucket: S3 bucket name for output
        stdout: Standard output from Knock conversion
        original_base: Base name (without extension) derived from input ACSM
        original_acsm_filename: Original ACSM filename (sanitized) for response context

    Returns:
        Dict containing response with S3 file information
    """
    try:
        s3 = boto3.client("s3")
        output_files: List[Dict[str, Union[str, int]]] = []

        # Find generated files (PDF/EPUB)
        for file_path in Path(tmp_dir).glob("*"):
            if file_path.suffix.lower() in [".pdf", ".epub"] and file_path.is_file():
                key_filename = f"{_sanitize_key_component(original_base)}{file_path.suffix.lower()}"
                key = f"converted/{key_filename}"
                s3.upload_file(str(file_path), output_bucket, key)

                # Generate presigned URL (valid for 1 hour)
                presigned_url = s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": output_bucket, "Key": key},
                    ExpiresIn=3600,  # 1 hour
                )

                output_files.append(
                    {
                        "filename": key_filename,
                        "s3_key": key,
                        "download_url": presigned_url,
                        "size_bytes": file_path.stat().st_size,
                        "source_acsm_filename": original_acsm_filename,
                    }
                )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Conversion successful",
                    "output_files": output_files,
                    "files_count": len(output_files),
                    "stdout": stdout,
                    "source_acsm_filename": original_acsm_filename,
                }
            ),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"error": f"Failed to upload files to S3: {str(e)}", "stdout": stdout}
            ),
        }
