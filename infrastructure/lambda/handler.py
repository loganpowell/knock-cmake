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
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import urllib.request
import urllib.error


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle Lambda invocation for Knock ACSM conversion.

    Args:
        event: Lambda event containing either 'acsm_url' or 'acsm_content'
        context: Lambda context (unused)

    Returns:
        Dict containing response with converted files or error information
    """
    try:
        # Parse the request body for Function URL invocations
        if "body" in event and event["body"]:
            try:
                # Parse JSON body from Function URL request
                body = json.loads(event["body"])
            except json.JSONDecodeError:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid JSON in request body"}),
                }
        else:
            # Direct invocation or event already parsed
            body = event

        # Get the ACSM file URL or content from the parsed body
        acsm_url = body.get("acsm_url")
        acsm_content = body.get("acsm_content")

        if not acsm_url and not acsm_content:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"error": "Either acsm_url or acsm_content is required"}
                ),
            }

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
                        "body": json.dumps({"error": "ACSM content is empty"}),
                    }

            # Run the Knock conversion
            knock_binary = os.path.join(
                os.environ["LAMBDA_TASK_ROOT"], "knock", "knock"
            )

            if not os.path.exists(knock_binary):
                return {
                    "statusCode": 500,
                    "body": json.dumps(
                        {"error": "Knock binary not found at expected location"}
                    ),
                }

            # Execute Knock conversion
            try:
                result = subprocess.run(
                    [knock_binary, acsm_path],
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minute timeout
                )
            except subprocess.TimeoutExpired:
                return {
                    "statusCode": 500,
                    "body": json.dumps(
                        {"error": "Knock conversion timed out after 10 minutes"}
                    ),
                }

            if result.returncode != 0:
                return {
                    "statusCode": 500,
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
                return _handle_s3_output(tmp_dir, output_bucket, result.stdout)
            else:
                return {
                    "statusCode": 200,
                    "body": json.dumps(
                        {"message": "Conversion successful", "stdout": result.stdout}
                    ),
                }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": f"Unexpected error: {str(e)}", "error_type": type(e).__name__}
            ),
        }


def _handle_s3_output(tmp_dir: str, output_bucket: str, stdout: str) -> Dict[str, Any]:
    """
    Handle uploading converted files to S3.

    Args:
        tmp_dir: Temporary directory containing converted files
        output_bucket: S3 bucket name for output
        stdout: Standard output from Knock conversion

    Returns:
        Dict containing response with S3 file information
    """
    try:
        s3 = boto3.client("s3")
        output_files: List[Dict[str, Union[str, int]]] = []

        # Find generated files (PDF/EPUB)
        for file_path in Path(tmp_dir).glob("*"):
            if file_path.suffix.lower() in [".pdf", ".epub"] and file_path.is_file():
                key = f"converted/{file_path.name}"
                s3.upload_file(str(file_path), output_bucket, key)
                output_files.append(
                    {
                        "filename": file_path.name,
                        "s3_key": key,
                        "s3_url": f"https://{output_bucket}.s3.amazonaws.com/{key}",
                        "size_bytes": file_path.stat().st_size,
                    }
                )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Conversion successful",
                    "output_files": output_files,
                    "files_count": len(output_files),
                    "stdout": stdout,
                }
            ),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": f"Failed to upload files to S3: {str(e)}", "stdout": stdout}
            ),
        }
