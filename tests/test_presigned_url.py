"""
Test script to debug presigned URL issues without using Adobe licenses.

This script invokes the Lambda function in debug mode, which creates a dummy file
to test S3 upload and presigned URL generation.
"""

import json
import subprocess
import sys


def test_presigned_url_debug_mode():
    """Test presigned URL generation using Lambda debug mode."""

    # Get the function URL from Pulumi
    print("📋 Getting Lambda function URL from Pulumi...")
    result = subprocess.run(
        ["pulumi", "stack", "output", "function_url"],
        cwd="../infrastructure",
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"❌ Failed to get function URL: {result.stderr}")
        sys.exit(1)

    function_url = result.stdout.strip()
    print(f"✓ Function URL: {function_url}")

    # Prepare debug payload
    payload = {"debug": True, "filename": "Test_Presigned_URL_Debug"}

    print(f"\n📤 Sending debug request to Lambda...")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    # Invoke Lambda via HTTP
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(
            function_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))

        print(f"\n✅ Lambda Response (Status {response.status}):")
        print(json.dumps(response_data, indent=2))

        # Try to download the file using the presigned URL
        if "output_files" in response_data and len(response_data["output_files"]) > 0:
            download_url = response_data["output_files"][0].get("download_url")

            if download_url:
                print(f"\n🔗 Testing download URL...")
                print(f"URL: {download_url[:100]}...")

                try:
                    req = urllib.request.Request(download_url)
                    with urllib.request.urlopen(req, timeout=10) as download_response:
                        content = download_response.read().decode("utf-8")

                    print(f"\n✅ Download successful!")
                    print(f"Status: {download_response.status}")
                    print(f"Content Length: {len(content)} bytes")
                    print(f"\nFile content:")
                    print("-" * 60)
                    print(content)
                    print("-" * 60)

                except urllib.error.HTTPError as e:
                    print(f"\n❌ Download failed with HTTP {e.code}")
                    print(f"Error: {e.reason}")
                    error_body = e.read().decode("utf-8")
                    print(f"\nError details:")
                    print(error_body)

                except Exception as e:
                    print(f"\n❌ Download failed: {e}")
                    print(f"Exception type: {type(e).__name__}")

    except urllib.error.HTTPError as e:
        print(f"\n❌ Lambda invocation failed with HTTP {e.code}")
        print(f"Error: {e.reason}")
        error_body = e.read().decode("utf-8")
        print(f"\nError details:")
        print(error_body)
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Request failed: {e}")
        print(f"Exception type: {type(e).__name__}")
        sys.exit(1)


if __name__ == "__main__":
    test_presigned_url_debug_mode()
