#!/usr/bin/env python3
"""Simple manual testing helper for Knock Lambda."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests


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
    
    print(f"📂 Processing ACSM file: {acsm_file}")
    
    # Read ACSM content
    acsm_content = acsm_file.read_text()
    payload = {"acsm_content": acsm_content}
    
    print("📡 Sending request...")
    print()
    
    start_time = time.time()
    response = requests.post(
        function_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    elapsed = time.time() - start_time
    
    # Print response
    print("📋 Response:")
    if response.headers.get("content-type") == "application/json":
        print(json.dumps(response.json(), indent=2))
    else:
        print(response.text)
    
    print()
    print(f"📊 HTTP Status: {response.status_code}")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"📦 Response size: {len(response.content)} bytes")


def test_custom_content(function_url: str, content: str):
    """Test with custom content."""
    print(f"📝 Testing with custom content: {content}")
    
    payload = {"acsm_content": content}
    
    print("📡 Sending request...")
    print()
    
    start_time = time.time()
    response = requests.post(
        function_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    elapsed = time.time() - start_time
    
    # Print response
    print("📋 Response:")
    if response.headers.get("content-type") == "application/json":
        print(json.dumps(response.json(), indent=2))
    else:
        print(response.text)
    
    print()
    print(f"📊 HTTP Status: {response.status_code}")
    print(f"⏱️  Total time: {elapsed:.2f}s")


def test_basic(function_url: str):
    """Test basic connectivity."""
    print("🔌 Testing basic connectivity...")
    
    payload = {"test": "basic_connectivity"}
    
    start_time = time.time()
    response = requests.post(
        function_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    elapsed = time.time() - start_time
    
    # Print response
    print("📋 Response:")
    if response.headers.get("content-type") == "application/json":
        print(json.dumps(response.json(), indent=2))
    else:
        print(response.text)
    
    print()
    print(f"📊 HTTP Status: {response.status_code}")
    print(f"⏱️  Total time: {elapsed:.2f}s")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Simple manual testing helper for Knock Lambda",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s basic
  %(prog)s file /path/to/file.acsm
  %(prog)s content 'Some test content'
  %(prog)s asset
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Test command")
    
    # Basic connectivity test
    subparsers.add_parser("basic", help="Test basic connectivity")
    
    # File test
    file_parser = subparsers.add_parser("file", help="Test with ACSM file")
    file_parser.add_argument("path", type=Path, help="Path to ACSM file")
    
    # Content test
    content_parser = subparsers.add_parser("content", help="Test with custom content")
    content_parser.add_argument("text", help="Content string to test")
    
    # Asset test
    subparsers.add_parser("asset", help="Test with bundled asset file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Get function URL
    print("🚀 Knock Lambda Manual Tester")
    print("=" * 30)
    function_url = get_function_url()
    print(f"Function URL: {function_url}")
    print()
    
    # Execute command
    if args.command == "basic":
        test_basic(function_url)
    elif args.command == "file":
        test_acsm_file(function_url, args.path)
    elif args.command == "content":
        test_custom_content(function_url, args.text)
    elif args.command == "asset":
        project_root = Path(__file__).parent.parent
        asset_file = project_root / "assets" / "The_Chemical_Muse-epub.acsm"
        if asset_file.exists():
            test_acsm_file(function_url, asset_file)
        else:
            print(f"❌ Asset file not found: {asset_file}")
            sys.exit(1)


if __name__ == "__main__":
    main()
