"""Advanced test scenarios for Knock Lambda function."""

import concurrent.futures
import json
import time
from pathlib import Path

import pytest
import requests


class TestConcurrency:
    """Concurrency and load tests."""

    def test_concurrent_requests(
        self, function_url: str, dummy_acsm_content: str, results_dir: Path
    ):
        """Test handling of concurrent requests (using dummy ACSM data)."""
        payload = {"acsm_content": dummy_acsm_content}
        num_requests = 3

        def make_request(request_id: int) -> tuple[int, int, float]:
            """Make a single request and return results."""
            start_time = time.time()
            response = requests.post(
                function_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            elapsed = time.time() - start_time

            # Save individual response
            output_file = results_dir / f"concurrent_{request_id}_response.json"
            output_file.write_text(
                json.dumps(
                    {
                        "status_code": response.status_code,
                        "elapsed_time": elapsed,
                        "response": (
                            response.json()
                            if response.headers.get("content-type")
                            == "application/json"
                            else response.text
                        ),
                    },
                    indent=2,
                )
            )

            return request_id, response.status_code, elapsed

        # Launch concurrent requests
        print(f"🚀 Launching {num_requests} concurrent requests...")
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=num_requests
        ) as executor:
            futures = [
                executor.submit(make_request, i) for i in range(1, num_requests + 1)
            ]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # Verify all completed
        assert (
            len(results) == num_requests
        ), f"Expected {num_requests} results, got {len(results)}"

        for request_id, status_code, elapsed in results:
            print(
                f"✅ Request {request_id} completed with status {status_code} in {elapsed:.2f}s"
            )

        print("✅ All concurrent requests completed")


class TestPerformance:
    """Performance and timing tests."""

    def test_response_time(self, function_url: str, results_dir: Path):
        """Test response time measurement."""
        payload = {"test": "timing"}

        start_time = time.time()
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        elapsed = time.time() - start_time

        # Save response
        output_file = results_dir / "timing_response.json"
        output_file.write_text(
            json.dumps(
                {
                    "status_code": response.status_code,
                    "elapsed_time": elapsed,
                    "response": (
                        response.json()
                        if response.headers.get("content-type") == "application/json"
                        else response.text
                    ),
                },
                indent=2,
            )
        )

        print(f"⏱️  Response time: {elapsed:.2f}s")

        # Check if response time is reasonable (under 30 seconds for cold start)
        if elapsed < 30:
            print("✅ Response time is acceptable")
        else:
            print("⚠️  Response time is slow (may be cold start)")


class TestMemory:
    """Memory and resource tests."""

    def test_memory_stress(self, function_url: str, results_dir: Path):
        """Test memory stress with large payload."""
        # Create a very large payload (5MB)
        large_content = "X" * 5_000_000
        payload = {"acsm_content": large_content}

        print("📡 Sending large payload (5MB)...")
        try:
            response = requests.post(
                function_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            # Save response
            output_file = results_dir / "memory_stress_response.json"
            output_file.write_text(
                json.dumps(
                    {
                        "status_code": response.status_code,
                        "response": (
                            response.json()
                            if response.headers.get("content-type")
                            == "application/json"
                            else response.text
                        ),
                    },
                    indent=2,
                )
            )

            print(f"📊 Status: {response.status_code}")

            if 200 <= response.status_code < 400:
                print("✅ Large payload handled successfully")
            else:
                print("ℹ️  Large payload rejected (expected for memory protection)")

        except requests.exceptions.Timeout:
            print("ℹ️  Request timed out (expected for memory protection)")
        except requests.exceptions.RequestException as e:
            print(f"ℹ️  Request failed: {e} (may be expected for memory protection)")


class TestErrorHandling:
    """Error handling and validation tests."""

    @pytest.mark.parametrize(
        "payload,description",
        [
            ('{"incomplete": ', "incomplete JSON"),
            ('{"invalid": "json"', "missing closing brace"),
            ("not json at all", "non-JSON text"),
            ('{"acsm_content": "test", "extra_comma": ,}', "extra comma"),
        ],
    )
    def test_malformed_json(
        self, function_url: str, payload: str, description: str, results_dir: Path
    ):
        """Test malformed JSON handling."""
        print(f"🧪 Testing {description}: {payload}")

        try:
            response = requests.post(
                function_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            # Save response
            safe_name = description.replace(" ", "_")
            output_file = results_dir / f"malformed_{safe_name}_response.json"
            output_file.write_text(
                json.dumps(
                    {
                        "status_code": response.status_code,
                        "payload": payload,
                        "response": response.text,
                    },
                    indent=2,
                )
            )

            if 400 <= response.status_code < 500:
                print(
                    f"✅ Correctly rejected malformed JSON with status {response.status_code}"
                )
            else:
                print(f"⚠️  Unexpected status {response.status_code} for malformed JSON")

        except requests.exceptions.RequestException as e:
            print(f"✅ Request properly rejected: {e}")

    @pytest.mark.parametrize("method", ["GET", "PUT", "DELETE", "PATCH"])
    def test_http_methods(self, function_url: str, method: str, results_dir: Path):
        """Test different HTTP methods."""
        print(f"🌐 Testing {method} method...")

        response = requests.request(
            method,
            function_url,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        # Save response
        output_file = results_dir / f"method_{method}_response.json"
        output_file.write_text(
            json.dumps(
                {
                    "status_code": response.status_code,
                    "response": (
                        response.json()
                        if response.headers.get("content-type") == "application/json"
                        else response.text
                    ),
                },
                indent=2,
            )
        )

        print(f"📊 {method} returned status: {response.status_code}")

        # Most Lambda functions only accept POST
        if method == "POST" and 200 <= response.status_code < 400:
            print("✅ POST method works correctly")
        elif method != "POST" and 400 <= response.status_code < 500:
            print(f"✅ {method} correctly rejected")
        else:
            print(f"ℹ️  {method} returned unexpected status {response.status_code}")
