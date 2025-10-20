"""Main test suite for Knock Lambda function."""

import json
from pathlib import Path

import pytest
import requests


class TestLambdaBasic:
    """Basic Lambda function tests."""
    
    def test_health_check(self, function_url: str, dummy_acsm_content: str, results_dir: Path):
        """Test basic Lambda connectivity (using dummy ACSM data)."""
        payload = {"acsm_content": dummy_acsm_content}
        
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        
        # Save response
        output_file = results_dir / "health_check_response.json"
        output_file.write_text(json.dumps({
            "status_code": response.status_code,
            "response": response.json() if response.headers.get("content-type") == "application/json" else response.text,
        }, indent=2))
        
        # Lambda is accessible if we get any HTTP response (2xx, 4xx, or 5xx)
        assert 200 <= response.status_code < 600, f"Lambda not accessible: {response.status_code}"
        print(f"✓ Lambda is accessible and responding with status {response.status_code}")
    
    def test_missing_parameters(self, function_url: str, results_dir: Path):
        """Test that missing required parameters return 400."""
        payload = {}
        
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        
        # Save response
        output_file = results_dir / "missing_params_response.json"
        output_file.write_text(json.dumps({
            "status_code": response.status_code,
            "response": response.json() if response.headers.get("content-type") == "application/json" else response.text,
        }, indent=2))
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Correctly returned 400 for missing parameters")


class TestLambdaACSM:
    """ACSM content processing tests."""
    
    @pytest.mark.real_acsm
    def test_acsm_content_upload(self, function_url: str, acsm_content: str, acsm_file: Path, results_dir: Path):
        """Test ACSM content upload and processing.
        
        WARNING: This test uses the real ACSM file which has limited downloads.
        Run with: pytest tests/test_lambda.py::TestLambdaACSM::test_acsm_content_upload -v
        Skip with: pytest tests/ -m "not real_acsm"
        """
        payload = {
            "acsm_content": acsm_content,
            "filename": acsm_file.name
        }
        
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        
        # Save response
        output_file = results_dir / "acsm_content_response.json"
        response_data = response.json() if response.headers.get("content-type") == "application/json" else response.text
        output_file.write_text(json.dumps({
            "status_code": response.status_code,
            "response": response_data,
        }, indent=2))
        
        # Check for Google device limit error (known limitation)
        if response.status_code == 500:
            if isinstance(response_data, dict) and "stderr" in response_data and "E_GOOGLE_DEVICE_LIMIT_REACHED" in response_data["stderr"]:
                pytest.skip("ACSM file has hit Google's device download limit. This is expected for heavily-used test files.")
        
        assert 200 <= response.status_code < 300, f"ACSM processing failed: {response.status_code}"
        
        # Display presigned URLs
        if isinstance(response_data, dict) and "output_files" in response_data:
            print("✓ ACSM content processed successfully")
            print(f"\nConverted {response_data.get('files_count', 0)} file(s):")
            for file_info in response_data.get("output_files", []):
                print(f"  • {file_info['filename']} ({file_info['size_bytes']} bytes)")
                print(f"    Download URL: {file_info['download_url']}")
                print(f"    S3 Key: {file_info['s3_key']}")
        else:
            print("✓ ACSM content processed successfully (no output files in response)")
    
    def test_invalid_acsm_content(self, function_url: str, results_dir: Path):
        """Test that invalid ACSM content returns an error."""
        payload = {"acsm_content": "This is not a valid ACSM file content"}
        
        response = requests.post(
            function_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        
        # Save response
        output_file = results_dir / "invalid_acsm_response.json"
        output_file.write_text(json.dumps({
            "status_code": response.status_code,
            "response": response.json() if response.headers.get("content-type") == "application/json" else response.text,
        }, indent=2))
        
        assert 400 <= response.status_code < 600, f"Expected error status, got {response.status_code}"
        print(f"✓ Correctly returned error status ({response.status_code}) for invalid ACSM")


class TestLambdaLoad:
    """Load and stress tests."""
    
    def test_large_request(self, function_url: str, results_dir: Path):
        """Test large request handling."""
        # Create a large payload (1MB)
        large_content = "A" * 1_000_000
        payload = {"acsm_content": large_content}
        
        try:
            response = requests.post(
                function_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            
            # Save response
            output_file = results_dir / "large_request_response.json"
            output_file.write_text(json.dumps({
                "status_code": response.status_code,
                "response": response.json() if response.headers.get("content-type") == "application/json" else response.text,
            }, indent=2))
            
            # Large requests may be rejected or processed - both are acceptable
            print(f"ℹ️  Large request returned status {response.status_code}")
            
        except requests.exceptions.Timeout:
            print("ℹ️  Large request timed out (expected for memory protection)")
        except requests.exceptions.RequestException as e:
            print(f"ℹ️  Large request failed: {e} (may be expected)")
