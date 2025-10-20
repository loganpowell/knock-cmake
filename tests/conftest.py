"""Pytest configuration and shared fixtures for Knock Lambda tests."""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import pytest


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


@pytest.fixture
def acsm_file(assets_dir: Path) -> Path:
    """Get the test ACSM file path."""
    acsm_path = assets_dir / "Nudge-epub.acsm"
    if not acsm_path.exists():
        pytest.skip(f"ACSM test file not found: {acsm_path}")
    return acsm_path


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


def save_response(
    results_dir: Path, test_name: str, response_data: dict, status_code: int
):
    """Save response data to results directory."""
    output_file = results_dir / f"{test_name}_response.json"
    data = {
        "status_code": status_code,
        "response": response_data,
    }
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
