#!/usr/bin/env python3
"""Interactive manual testing tool for Knock Lambda."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import inquirer
import requests

# Add parent directory to path to import conftest utilities
sys.path.insert(0, str(Path(__file__).parent))
from conftest import find_acsm_files, select_acsm_file, print_response


def get_function_url() -> str:
    """Get the Lambda function URL from Pulumi stack output."""
    project_root = Path(__file__).parent.parent
    
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
            ["./pumi", "stack", "output", "function_url"],
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
        
        print("❌ Could not get function URL from Pulumi stack")
        print("Make sure the stack is deployed with: ./pumi up")
        sys.exit(1)
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ Error getting function URL: {e}")
        sys.exit(1)


def test_acsm_file(function_url: str, acsm_file: Path):
    """Test with ACSM file."""
    if not acsm_file.exists():
        print(f"❌ File not found: {acsm_file}")
        return
    
    print(f"\n📂 Processing ACSM file: {acsm_file.name}")
    print(f"   Path: {acsm_file}")
    
    # Read ACSM content
    acsm_content = acsm_file.read_text()
    payload = {"acsm_content": acsm_content, "filename": acsm_file.name}
    
    print("\n📡 Sending request to Lambda...")
    
    start_time = time.time()
    try:
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=90,
        )
        elapsed = time.time() - start_time
        
        # Parse and print response
        response_data = response.json() if response.headers.get("content-type") == "application/json" else response.text
        print_response(response_data, response.status_code, elapsed)
        
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out after 90 seconds")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")


def test_custom_content(function_url: str, dummy_acsm_content: str):
    """Test with custom content."""
    print(f"\n📝 Testing with custom content (length: {len(dummy_acsm_content)} chars)")
    
    payload = {"acsm_content": dummy_acsm_content}
    
    print("\n📡 Sending request to Lambda...")
    
    start_time = time.time()
    try:
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        elapsed = time.time() - start_time
        
        # Parse and print response
        response_data = response.json() if response.headers.get("content-type") == "application/json" else response.text
        print_response(response_data, response.status_code, elapsed)
        
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out after 60 seconds")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")


def test_basic(function_url: str):
    """Test basic connectivity."""
    print("\n🔌 Testing basic connectivity...")
    
    payload = {"test": "basic_connectivity"}
    
    print("\n📡 Sending test request to Lambda...")
    
    start_time = time.time()
    try:
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        elapsed = time.time() - start_time
        
        # Parse and print response
        response_data = response.json() if response.headers.get("content-type") == "application/json" else response.text
        print_response(response_data, response.status_code, elapsed)
        
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out after 60 seconds")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")


def select_acsm_interactive(assets_dir: Path) -> Path:
    """Interactively select an ACSM file from assets directory."""
    acsm_files = find_acsm_files(assets_dir)
    
    if not acsm_files:
        print("❌ No ACSM files found in assets directory")
        sys.exit(1)
    
    return select_acsm_file(acsm_files, interactive=True)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive manual testing tool for Knock Lambda",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                   # Interactive ACSM file selection
  %(prog)s basic              # Test basic connectivity
  %(prog)s file /path/to/file.acsm
  %(prog)s content 'test'     # Test with custom content
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Test command")
    
    # Basic connectivity test
    subparsers.add_parser("basic", help="Test basic connectivity")
    
    # File test
    file_parser = subparsers.add_parser("file", help="Test with specific ACSM file")
    file_parser.add_argument("path", type=Path, help="Path to ACSM file")
    
    # Content test
    content_parser = subparsers.add_parser("content", help="Test with custom content")
    content_parser.add_argument("text", help="Content string to test")
    
    args = parser.parse_args()
    
    # Get function URL
    print("🚀 Knock Lambda Interactive Tester")
    print("=" * 40)
    function_url = get_function_url()
    print(f"Function URL: {function_url}")
    
    # Execute command
    if args.command == "basic":
        test_basic(function_url)
    elif args.command == "file":
        test_acsm_file(function_url, args.path)
    elif args.command == "content":
        test_custom_content(function_url, args.text)
    else:
        # No command specified - interactive ACSM selection
        project_root = Path(__file__).parent.parent
        assets_dir = project_root / "assets"
        
        try:
            acsm_file = select_acsm_interactive(assets_dir)
            test_acsm_file(function_url, acsm_file)
        except KeyboardInterrupt:
            print("\n\n❌ Cancelled by user")
            sys.exit(0)


if __name__ == "__main__":
    main()
