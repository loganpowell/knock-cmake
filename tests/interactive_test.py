#!/usr/bin/env python3
"""
Interactive CLI for testing Knock Lambda with ACSM files.

This tool provides an interactive menu-driven interface for:
- Running health checks
- Testing presigned URL generation (debug mode - no licenses used)
- Selecting ACSM files from the repository
- Testing Lambda function with selected files
- Viewing formatted results
- Running multiple tests in sequence
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

import inquirer
import requests
from inquirer.themes import GreenPassion


def find_acsm_files(project_root: Path) -> List[Path]:
    """
    Find all ACSM files in the repository.

    Args:
        project_root: Root directory of the project

    Returns:
        List of Path objects for ACSM files
    """
    acsm_files = []

    # Common locations for ACSM files
    search_dirs = [
        project_root / "assets",
        project_root / "tests" / "fixtures",
        project_root / "tests" / "data",
    ]

    for search_dir in search_dirs:
        if search_dir.exists():
            acsm_files.extend(search_dir.glob("*.acsm"))

    # Also search recursively from project root (limit depth)
    for acsm_file in project_root.rglob("*.acsm"):
        # Skip hidden directories and common excludes
        if any(part.startswith(".") for part in acsm_file.parts):
            continue
        if any(
            exclude in str(acsm_file)
            for exclude in ["node_modules", "__pycache__", "build"]
        ):
            continue
        if acsm_file not in acsm_files:
            acsm_files.append(acsm_file)

    return sorted(acsm_files)


def get_function_url(project_root: Path) -> str:
    """
    Get the Lambda function URL from Pulumi stack output.

    Args:
        project_root: Root directory of the project

    Returns:
        Function URL string

    Raises:
        SystemExit: If URL cannot be retrieved
    """
    # Load environment variables from .env if present
    env_file = project_root / ".env"
    env_vars = os.environ.copy()

    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    if key and value:
                        env_vars[key.strip()] = value.strip()

    try:
        result = subprocess.run(
            ["pulumi", "stack", "output", "function_url"],
            cwd=project_root,
            capture_output=True,
            text=True,
            env=env_vars,
            timeout=30,
        )

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("https://"):
                return line

        print("\n❌ Could not get function URL from Pulumi stack")
        print("Make sure the stack is deployed with: pulumi up\n")
        sys.exit(1)

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
    ) as e:
        print(f"\n❌ Error getting function URL: {e}\n")
        sys.exit(1)


def test_acsm_file(
    function_url: str, acsm_file: Path, show_full_response: bool = True
) -> dict:
    """
    Test Lambda function with an ACSM file.

    Args:
        function_url: Lambda function URL
        acsm_file: Path to ACSM file
        show_full_response: Whether to show full response content

    Returns:
        Dictionary with test results
    """
    if not acsm_file.exists():
        return {
            "success": False,
            "error": f"File not found: {acsm_file}",
            "status_code": None,
            "elapsed": 0,
        }

    print(f"\n{'='*70}")
    print(f"📂 Testing: {acsm_file.name}")
    print(f"{'='*70}\n")

    # Read ACSM content
    try:
        acsm_content = acsm_file.read_text()
        # Show first 200 chars of content
        preview = (
            acsm_content[:200] + "..." if len(acsm_content) > 200 else acsm_content
        )
        print(f"📄 Content preview:\n{preview}\n")
    except Exception as e:
        return {
            "success": False,
            "error": f"Error reading file: {e}",
            "status_code": None,
            "elapsed": 0,
        }

    payload = {"acsm_content": acsm_content}

    print("📡 Sending request to Lambda...\n")

    try:
        start_time = time.time()
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        elapsed = time.time() - start_time

        # Parse response
        result = {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "elapsed": elapsed,
            "size": len(response.content),
        }

        # Print response
        print("📋 Response:")
        print(f"{'─'*70}")

        if response.headers.get("content-type") == "application/json":
            try:
                json_response = response.json()
                result["response"] = json_response

                if show_full_response:
                    print(json.dumps(json_response, indent=2))
                else:
                    # Show summary
                    if isinstance(json_response, dict):
                        for key in ["status", "message", "error", "epub_url"]:
                            if key in json_response:
                                print(f"{key}: {json_response[key]}")
            except json.JSONDecodeError:
                result["response"] = response.text
                print(response.text)
        else:
            result["response"] = response.text
            print(response.text)

        print(f"{'─'*70}\n")

        # Print summary
        status_emoji = "✅" if result["success"] else "❌"
        print(f"{status_emoji} Status: {response.status_code}")
        print(f"⏱️  Duration: {elapsed:.2f}s")
        print(f"📦 Response size: {len(response.content)} bytes")

        return result

    except requests.Timeout:
        return {
            "success": False,
            "error": "Request timeout (60s)",
            "status_code": None,
            "elapsed": 60,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Request error: {e}",
            "status_code": None,
            "elapsed": 0,
        }


def test_health_check(function_url: str) -> bool:
    """
    Test basic Lambda connectivity.

    Args:
        function_url: Lambda function URL

    Returns:
        True if health check passes
    """
    print(f"\n{'='*70}")
    print("🔌 Health Check")
    print(f"{'='*70}\n")

    payload = {"test": "health_check"}

    try:
        start_time = time.time()
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        elapsed = time.time() - start_time

        success = response.status_code == 200
        status_emoji = "✅" if success else "❌"

        print(f"{status_emoji} Status: {response.status_code}")
        print(f"⏱️  Duration: {elapsed:.2f}s")

        if response.headers.get("content-type") == "application/json":
            print(f"\n📋 Response:\n{json.dumps(response.json(), indent=2)}")

        return success

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_presigned_url_debug(function_url: str) -> bool:
    """
    Test presigned URL generation using debug mode.
    Creates a dummy file without using Adobe licenses.

    Args:
        function_url: Lambda function URL

    Returns:
        True if test passes
    """
    print(f"\n{'='*70}")
    print("🔧 Presigned URL Debug Test")
    print(f"{'='*70}\n")
    print("This test creates a dummy file to validate S3 upload and presigned URLs")
    print("WITHOUT consuming Adobe licenses.\n")

    payload = {"debug": True, "filename": "Interactive_Debug_Test"}

    try:
        print("📤 Sending debug request to Lambda...")
        start_time = time.time()
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        elapsed = time.time() - start_time

        print(f"⏱️  Lambda duration: {elapsed:.2f}s")
        print(f"📊 Status code: {response.status_code}\n")

        if response.status_code != 200:
            print(f"❌ Lambda returned error status: {response.status_code}")
            print(f"Response: {response.text}")
            return False

        response_data = response.json()
        print("📋 Lambda Response:")
        print(json.dumps(response_data, indent=2))
        print()

        # Try to download the file using the presigned URL
        if "output_files" in response_data and len(response_data["output_files"]) > 0:
            output_file = response_data["output_files"][0]
            download_url = output_file.get("download_url")

            if not download_url:
                print("❌ No download URL in response")
                return False

            print(f"🔗 Testing presigned URL download...")
            print(f"URL (first 80 chars): {download_url[:80]}...\n")

            try:
                download_start = time.time()
                download_response = requests.get(download_url, timeout=10)
                download_elapsed = time.time() - download_start

                if download_response.status_code == 200:
                    content = download_response.text
                    print(f"✅ Download successful!")
                    print(f"⏱️  Download duration: {download_elapsed:.2f}s")
                    print(f"📦 Content size: {len(content)} bytes")
                    print(f"\n📄 File content:")
                    print("─" * 70)
                    print(content)
                    print("─" * 70)
                    print("\n✅ Presigned URL test PASSED!\n")
                    return True
                else:
                    print(
                        f"❌ Download failed with HTTP {download_response.status_code}"
                    )
                    print(f"Error: {download_response.reason}")
                    print(f"\n📄 Error details:")
                    print(download_response.text[:1000])  # First 1000 chars of error
                    return False

            except Exception as e:
                print(f"❌ Download request failed: {e}")
                print(f"Exception type: {type(e).__name__}")
                return False
        else:
            print("❌ No output files in response")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(f"Exception type: {type(e).__name__}")
        return False


def main():
    """Main interactive CLI."""
    project_root = Path(__file__).parent.parent

    # Print banner
    print("\n" + "=" * 70)
    print("🚀 Knock Lambda Interactive Test CLI")
    print("=" * 70)

    # Find ACSM files
    print("\n🔍 Scanning for ACSM files...")
    acsm_files = find_acsm_files(project_root)

    if not acsm_files:
        print("\n❌ No ACSM files found in the repository!")
        print("Expected locations: assets/, tests/fixtures/, tests/data/")
        sys.exit(1)

    print(f"✅ Found {len(acsm_files)} ACSM file(s)\n")

    # Get function URL once at start
    print("🔗 Getting Lambda function URL...")
    function_url = get_function_url(project_root)
    print(f"✅ Function URL: {function_url}\n")

    # Main menu loop
    while True:
        # Create menu choices - inquirer expects (display_name, value) tuples
        file_choices = []
        for acsm_file in acsm_files:
            relative_path = acsm_file.relative_to(project_root)
            file_choices.append((f"📄 {relative_path}", acsm_file))

        questions = [
            inquirer.List(
                "action",
                message="What would you like to do?",
                choices=[
                    ("🏥 Run health check", "health"),
                    ("� Test presigned URL (debug mode)", "debug_presigned_url"),
                    ("�📂 Test single ACSM file", "single"),
                    ("📚 Test all ACSM files", "all"),
                    ("🔄 Test multiple files (select)", "multiple"),
                    ("🔍 View file content", "view"),
                    ("🚪 Exit", "exit"),
                ],
            ),
        ]

        answers = inquirer.prompt(questions, theme=GreenPassion())

        if not answers or answers["action"] == "exit":
            print("\n👋 Goodbye!\n")
            break

        action = answers["action"]

        if action == "health":
            test_health_check(function_url)
            input("\nPress Enter to continue...")

        elif action == "debug_presigned_url":
            test_presigned_url_debug(function_url)
            input("\nPress Enter to continue...")

        elif action == "single":
            file_question = [
                inquirer.List(
                    "file",
                    message="Select ACSM file to test",
                    choices=file_choices,
                ),
            ]
            file_answer = inquirer.prompt(file_question, theme=GreenPassion())

            if file_answer:
                test_acsm_file(function_url, file_answer["file"])
                input("\nPress Enter to continue...")

        elif action == "all":
            confirm = inquirer.confirm(
                f"Run tests for all {len(acsm_files)} files?",
                default=True,
            )

            if confirm:
                results = []
                for i, acsm_file in enumerate(acsm_files, 1):
                    print(f"\n[{i}/{len(acsm_files)}]")
                    result = test_acsm_file(
                        function_url, acsm_file, show_full_response=False
                    )
                    results.append({"file": acsm_file.name, "result": result})

                # Show summary
                print(f"\n{'='*70}")
                print("📊 Test Summary")
                print(f"{'='*70}\n")

                passed = sum(1 for r in results if r["result"]["success"])
                failed = len(results) - passed

                for r in results:
                    status = "✅" if r["result"]["success"] else "❌"
                    elapsed = r["result"]["elapsed"]
                    print(f"{status} {r['file']:40s} ({elapsed:.2f}s)")

                print(f"\n{'─'*70}")
                print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")
                print(f"{'─'*70}")

                input("\nPress Enter to continue...")

        elif action == "multiple":
            file_questions = [
                inquirer.Checkbox(
                    "files",
                    message="Select files to test (Space to select, Enter to confirm)",
                    choices=file_choices,
                ),
            ]
            file_answers = inquirer.prompt(file_questions, theme=GreenPassion())

            if file_answers and file_answers["files"]:
                selected_files = file_answers["files"]
                results = []

                for i, acsm_file in enumerate(selected_files, 1):
                    print(f"\n[{i}/{len(selected_files)}]")
                    result = test_acsm_file(
                        function_url, acsm_file, show_full_response=False
                    )
                    results.append({"file": acsm_file.name, "result": result})

                # Show summary
                print(f"\n{'='*70}")
                print("📊 Test Summary")
                print(f"{'='*70}\n")

                passed = sum(1 for r in results if r["result"]["success"])
                failed = len(results) - passed

                for r in results:
                    status = "✅" if r["result"]["success"] else "❌"
                    elapsed = r["result"]["elapsed"]
                    print(f"{status} {r['file']:40s} ({elapsed:.2f}s)")

                print(f"\n{'─'*70}")
                print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")
                print(f"{'─'*70}")

                input("\nPress Enter to continue...")
            else:
                print("\n⚠️  No files selected")
                input("Press Enter to continue...")

        elif action == "view":
            file_question = [
                inquirer.List(
                    "file",
                    message="Select ACSM file to view",
                    choices=file_choices,
                ),
            ]
            file_answer = inquirer.prompt(file_question, theme=GreenPassion())

            if file_answer:
                acsm_file = file_answer["file"]
                print(f"\n{'='*70}")
                print(f"📄 {acsm_file.relative_to(project_root)}")
                print(f"{'='*70}\n")

                try:
                    content = acsm_file.read_text()
                    print(content)
                    print(f"\n{'─'*70}")
                    print(f"File size: {len(content)} bytes")
                except Exception as e:
                    print(f"❌ Error reading file: {e}")

                input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!\n")
        sys.exit(0)
