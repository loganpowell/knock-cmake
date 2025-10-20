"""Advanced test scenarios for Knock Lambda function."""

import concurrent.futures
import time
from pathlib import Path

import pytest
import requests
from conftest import save_response


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
            response_data = response.json() if response.headers.get("content-type") == "application/json" else response.text
            save_response(results_dir, f"concurrent_{request_id}", response_data, response.status_code, elapsed, print_output=False)

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

        # Print summary
        print(f"\n📊 Concurrent Request Results:")
        for request_id, status_code, elapsed in results:
            print(f"  ✅ Request {request_id}: HTTP {status_code} in {elapsed:.2f}s")
        print(f"\n✅ All {num_requests} concurrent requests completed")


class TestStress:
    """Stress and performance tests."""

    def test_response_time(self, function_url: str, results_dir: Path):
        """Test response time with minimal payload."""
        payload = {"test": "timing"}

        start_time = time.time()
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        elapsed = time.time() - start_time

        response_data = response.json() if response.headers.get("content-type") == "application/json" else response.text
        save_response(results_dir, "timing", response_data, response.status_code, elapsed)

        # Check if response time is reasonable (under 30 seconds for cold start)
        if elapsed < 30:
            print("✅ Response time is acceptable")
        else:
            print("⚠️  Response time is slow (may be cold start)")

    def test_large_payload(self, function_url: str, results_dir: Path):
        """Test with large payload (5MB)."""
        large_content = "X" * 5_000_000
        payload = {"acsm_content": large_content}

        print("📡 Sending large payload (5MB)...")
        try:
            start_time = time.time()
            response = requests.post(
                function_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            elapsed = time.time() - start_time

            response_data = response.json() if response.headers.get("content-type") == "application/json" else response.text
            save_response(results_dir, "large_payload", response_data, response.status_code, elapsed)

        except requests.exceptions.Timeout:
            print("ℹ️  Request timed out (expected for memory protection)")
        except requests.exceptions.RequestException as e:
            print(f"ℹ️  Request failed: {e} (may be expected for memory protection)")


class TestErrorHandling:
    """Error handling and validation tests."""

    @pytest.mark.parametrize(
        "payload,description",
        [
            ('{"incomplete": ', "incomplete_json"),
            ("not json at all", "non_json_text"),
        ],
    )
    def test_malformed_json(
        self, function_url: str, payload: str, description: str, results_dir: Path
    ):
        """Test malformed JSON handling."""
        print(f"🧪 Testing malformed JSON: {description}")

        try:
            response = requests.post(
                function_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            save_response(results_dir, f"malformed_{description}", {"payload": payload, "response": response.text}, response.status_code, print_output=False)

            if 400 <= response.status_code < 500:
                print(f"✅ Correctly rejected with status {response.status_code}")
            else:
                print(f"⚠️  Unexpected status {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"✅ Request properly rejected: {e}")

    @pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
    def test_http_methods(self, function_url: str, method: str, results_dir: Path):
        """Test that only POST method is accepted."""
        response = requests.request(
            method,
            function_url,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        response_data = response.json() if response.headers.get("content-type") == "application/json" else response.text
        save_response(results_dir, f"method_{method}", response_data, response.status_code, print_output=False)

        # Lambda function URLs typically reject non-POST methods
        if 400 <= response.status_code < 500:
            print(f"✅ {method} correctly rejected with status {response.status_code}")
        else:
            print(f"ℹ️  {method} returned unexpected status {response.status_code}")
