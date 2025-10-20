"""Pytest configuration and shared fixtures for Knock Lambda tests."""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

import inquirer
import pytest


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--acsm-file",
        action="store",
        default=None,
        help="Specify which ACSM file to use (filename only, e.g., 'Designing_Your_Life-epub.acsm')"
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "real_acsm: marks test as using real ACSM file (limited downloads)"
    )


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def assets_dir(project_root: Path) -> Path:
    """Get the assets directory."""
    return project_root / "assets"


@pytest.fixture(scope="session")
def results_dir() -> Path:
    """Get the results directory for test outputs."""
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    return results_dir


@pytest.fixture(scope="session")
def function_url(project_root: Path) -> str:
    """Get the Lambda function URL from Pulumi stack output."""
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

    # Try to get function URL from Pulumi
    try:
        result = subprocess.run(
            ["./pumi", "stack", "output", "function_url"],
            cwd=project_root,
            capture_output=True,
            text=True,
            env=env_vars,
            timeout=30,
        )

        # Extract URL from output
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("https://"):
                return line

        # If no URL found, raise error
        raise ValueError("Could not find function URL in Pulumi output")

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
    ) as e:
        pytest.fail(f"Failed to get function URL from Pulumi: {e}")


def find_acsm_files(assets_dir: Path) -> list[Path]:
    """Find all ACSM files in assets directory."""
    return sorted(assets_dir.glob("*.acsm"))


def select_acsm_file(acsm_files: list[Path], interactive: bool = True) -> Path:
    """Select an ACSM file from available files.
    
    Args:
        acsm_files: List of available ACSM files
        interactive: If True, prompt user; if False, return first file
    
    Returns:
        Selected ACSM file path
    """
    if not acsm_files:
        raise FileNotFoundError("No ACSM files found in assets directory")
    
    if len(acsm_files) == 1 or not interactive:
        return acsm_files[0]
    
    # Use inquirer for interactive selection
    choices = [f.name for f in acsm_files]
    questions = [
        inquirer.List(
            'acsm_file',
            message="Select an ACSM file to test",
            choices=choices,
        ),
    ]
    
    answers = inquirer.prompt(questions)
    if not answers:
        # User cancelled
        raise KeyboardInterrupt("ACSM file selection cancelled")
    
    selected_name = answers['acsm_file']
    return next(f for f in acsm_files if f.name == selected_name)


@pytest.fixture
def acsm_file(assets_dir: Path, request) -> Path:
    """Get the test ACSM file path.
    
    Can be controlled via:
    - --acsm-file=filename.acsm (specify exact file)
    - Default: uses first file alphabetically
    
    For interactive selection, use: python tests/manual_test.py
    """
    acsm_files = find_acsm_files(assets_dir)
    
    if not acsm_files:
        pytest.skip("No ACSM files found in assets directory")
    
    # Check if specific file was requested via command line
    requested_file = request.config.getoption("--acsm-file")
    if requested_file:
        matching = [f for f in acsm_files if f.name == requested_file]
        if matching:
            return matching[0]
        else:
            available = ', '.join([f.name for f in acsm_files])
            pytest.fail(f"Requested ACSM file '{requested_file}' not found. Available: {available}")
    
    # Default: use first file without prompting
    return acsm_files[0]


@pytest.fixture
def acsm_content(acsm_file: Path, request) -> str:
    """Read ACSM file content.

    WARNING: Only use this fixture in tests marked with @pytest.mark.real_acsm
    The ACSM file has limited downloads per device.
    """
    # Check if test is marked with real_acsm
    if request.node.get_closest_marker("real_acsm") is None:
        pytest.fail(
            "Test attempted to use real ACSM content without @pytest.mark.real_acsm marker. "
            "ACSM files have limited downloads - use dummy data instead."
        )
    return acsm_file.read_text()


@pytest.fixture
def dummy_acsm_content() -> str:
    """Get dummy ACSM-like content for tests that don't need real processing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<fulfillmentToken xmlns="http://ns.adobe.com/adept">
  <resourceItemInfo>
    <metadata>
      <dc:title>Test Book</dc:title>
    </metadata>
  </resourceItemInfo>
</fulfillmentToken>"""


def print_response(response_data: Any, status_code: int, elapsed_time: Optional[float] = None):
    """Print response in a formatted, readable way."""
    print("\n" + "=" * 70)
    print(f"📊 HTTP Status: {status_code}")
    if elapsed_time:
        print(f"⏱️  Response Time: {elapsed_time:.2f}s")
    print("=" * 70)
    
    if isinstance(response_data, dict):
        # Pretty print structured response
        if "error" in response_data:
            print(f"\n❌ Error: {response_data.get('error')}")
            if "stderr" in response_data:
                print(f"\nStderr:\n{response_data['stderr'][:500]}...")  # Truncate long errors
        elif "output_files" in response_data:
            print(f"\n✅ Conversion successful!")
            print(f"\nConverted {response_data.get('files_count', 0)} file(s):")
            for file_info in response_data.get("output_files", []):
                print(f"\n  📄 {file_info['filename']}")
                print(f"     Size: {file_info['size_bytes']:,} bytes")
                if 'download_url' in file_info:
                    url = file_info['download_url']
                    print(f"     Download: {url}")
        else:
            print("\n📋 Response:")
            print(json.dumps(response_data, indent=2))
    else:
        print(f"\n📋 Response: {response_data}")
    
    print("=" * 70 + "\n")


def save_response(
    results_dir: Path, 
    test_name: str, 
    response_data: Any, 
    status_code: int,
    elapsed_time: Optional[float] = None,
    print_output: bool = True
):
    """Save response data to results directory and optionally print it.
    
    Args:
        results_dir: Directory to save results
        test_name: Name of the test (used for filename)
        response_data: Response data to save
        status_code: HTTP status code
        elapsed_time: Request elapsed time in seconds
        print_output: Whether to print the response
    """
    # Save to file
    output_file = results_dir / f"{test_name}_response.json"
    data = {
        "status_code": status_code,
        "response": response_data,
    }
    if elapsed_time:
        data["elapsed_time"] = elapsed_time
    
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    
    # Print to console
    if print_output:
        print_response(response_data, status_code, elapsed_time)
