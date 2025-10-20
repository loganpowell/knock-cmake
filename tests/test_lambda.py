"""Main test suite for Knock Lambda function."""

import time
from pathlib import Path

import pytest
import requests
from conftest import save_response


class TestLambdaBasic:
    """Basic Lambda function tests."""

    def test_health_check(
        self, function_url: str, dummy_acsm_content: str, results_dir: Path
    ):
        """Test basic Lambda connectivity (using dummy ACSM data)."""
        payload = {"acsm_content": dummy_acsm_content}

        start_time = time.time()
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        elapsed = time.time() - start_time

        response_data = (
            response.json()
            if response.headers.get("content-type") == "application/json"
            else response.text
        )
        save_response(
            results_dir, "health_check", response_data, response.status_code, elapsed
        )

        # Lambda is accessible if we get any HTTP response (2xx, 4xx, or 5xx)
        assert (
            200 <= response.status_code < 600
        ), f"Lambda not accessible: {response.status_code}"

    def test_missing_parameters(self, function_url: str, results_dir: Path):
        """Test that missing required parameters return 400."""
        payload = {}

        start_time = time.time()
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        elapsed = time.time() - start_time

        response_data = (
            response.json()
            if response.headers.get("content-type") == "application/json"
            else response.text
        )
        save_response(
            results_dir, "missing_params", response_data, response.status_code, elapsed
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"


class TestLambdaACSM:
    """ACSM content processing tests."""

    @pytest.mark.real_acsm
    def test_acsm_content_upload(
        self, function_url: str, acsm_content: str, acsm_file: Path, results_dir: Path
    ):
        """Test ACSM content upload and processing.

        WARNING: This test uses the real ACSM file which has limited downloads.
        Run with: pytest tests/test_lambda.py::TestLambdaACSM::test_acsm_content_upload -v
        Skip with: pytest tests/ -m "not real_acsm"
        """
        payload = {"acsm_content": acsm_content, "filename": acsm_file.name}

        start_time = time.time()
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=90,
        )
        elapsed = time.time() - start_time

        response_data = (
            response.json()
            if response.headers.get("content-type") == "application/json"
            else response.text
        )
        save_response(
            results_dir, "acsm_content", response_data, response.status_code, elapsed
        )

        # Check for Google device limit error (known limitation)
        if response.status_code == 500:
            if (
                isinstance(response_data, dict)
                and "stderr" in response_data
                and "E_GOOGLE_DEVICE_LIMIT_REACHED" in response_data["stderr"]
            ):
                pytest.skip(
                    "ACSM file has hit Google's device download limit. This is expected for heavily-used test files."
                )

        assert (
            200 <= response.status_code < 300
        ), f"ACSM processing failed: {response.status_code}"

    def test_invalid_acsm_content(self, function_url: str, results_dir: Path):
        """Test that invalid ACSM content returns an error."""
        payload = {"acsm_content": "This is not a valid ACSM file content"}

        start_time = time.time()
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        elapsed = time.time() - start_time

        response_data = (
            response.json()
            if response.headers.get("content-type") == "application/json"
            else response.text
        )
        save_response(
            results_dir, "invalid_acsm", response_data, response.status_code, elapsed
        )

        assert (
            400 <= response.status_code < 600
        ), f"Expected error status, got {response.status_code}"
