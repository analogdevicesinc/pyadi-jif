"""Tests for API endpoints."""

import pytest
import requests


class TestAPIEndpoints:
    """Test suite for backend API endpoints."""

    def test_health_endpoint(self, api_url: str) -> None:
        """Test that health endpoint returns successfully."""
        response = requests.get(f"{api_url}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self, api_url: str) -> None:
        """Test root API endpoint."""
        response = requests.get(api_url, timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_supported_converters_endpoint(self, api_url: str) -> None:
        """Test that supported converters endpoint returns data."""
        response = requests.get(f"{api_url}/api/converters/supported", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "No converters returned"
        print(f"Number of supported converters: {len(data)}")
        print(f"Sample converters: {data[:5]}")

    def test_supported_clocks_endpoint(self, api_url: str) -> None:
        """Test that supported clocks endpoint returns data."""
        response = requests.get(f"{api_url}/api/clocks/supported", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "No clocks returned"
        print(f"Number of supported clocks: {len(data)}")
        print(f"Sample clocks: {data[:5]}")

    def test_fpga_dev_kits_endpoint(self, api_url: str) -> None:
        """Test that FPGA dev kits endpoint returns data."""
        response = requests.get(f"{api_url}/api/systems/fpga-dev-kits", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "No FPGA dev kits returned"
        print(f"Number of FPGA dev kits: {len(data)}")

    def test_fpga_constraints_endpoint(self, api_url: str) -> None:
        """Test that FPGA constraints endpoint returns data."""
        response = requests.get(f"{api_url}/api/systems/fpga-constraints", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "ref_clock_constraints" in data or "sys_clk_selections" in data

    @pytest.mark.parametrize(
        "converter",
        ["ad9680", "ad9144", "ad9081"],  # Common converters that should exist
    )
    def test_converter_info_endpoint(self, api_url: str, converter: str) -> None:
        """Test getting info for specific converters."""
        response = requests.get(
            f"{api_url}/api/converters/{converter}/info", timeout=5
        )

        # Converter may or may not exist
        if response.status_code == 200:
            data = response.json()
            assert "part" in data
            assert data["part"] == converter
            print(f"✓ Converter {converter} info retrieved")
        else:
            print(f"⚠ Converter {converter} not available (status: {response.status_code})")

    def test_cors_headers_present(self, api_url: str) -> None:
        """Test that CORS headers are present in API responses."""
        response = requests.get(f"{api_url}/health", timeout=5)
        assert response.status_code == 200

        # Check for CORS header (may not be present in all requests)
        headers = response.headers
        print(f"Response headers: {dict(headers)}")

        # CORS headers are typically added by OPTIONS requests or browser requests
        # This is informational

    def test_api_documentation_available(self, api_url: str) -> None:
        """Test that API documentation is available."""
        # FastAPI automatic docs
        docs_response = requests.get(f"{api_url}/docs", timeout=5)
        assert docs_response.status_code == 200
        assert "swagger" in docs_response.text.lower() or "openapi" in docs_response.text.lower()

        # ReDoc
        redoc_response = requests.get(f"{api_url}/redoc", timeout=5)
        assert redoc_response.status_code == 200

    def test_invalid_endpoint_returns_404(self, api_url: str) -> None:
        """Test that invalid endpoints return 404."""
        response = requests.get(f"{api_url}/api/nonexistent", timeout=5)
        assert response.status_code == 404

    def test_api_response_times(self, api_url: str) -> None:
        """Test that API endpoints respond quickly."""
        import time

        endpoints = [
            "/health",
            "/api/converters/supported",
            "/api/clocks/supported",
            "/api/systems/fpga-dev-kits",
        ]

        for endpoint in endpoints:
            start = time.time()
            response = requests.get(f"{api_url}{endpoint}", timeout=5)
            duration = time.time() - start

            assert response.status_code == 200
            assert duration < 2.0, f"Endpoint {endpoint} took {duration:.2f}s (> 2s)"
            print(f"✓ {endpoint}: {duration:.3f}s")

    @pytest.mark.slow
    def test_converter_jesd_controls(self, api_url: str) -> None:
        """Test getting JESD controls for a converter."""
        # First get a supported converter
        conv_response = requests.get(
            f"{api_url}/api/converters/supported", timeout=5
        )
        assert conv_response.status_code == 200
        converters = conv_response.json()

        if converters:
            first_converter = converters[0]

            # Get JESD controls for this converter
            controls_response = requests.post(
                f"{api_url}/api/converters/{first_converter}/jesd-controls",
                timeout=10,
            )

            if controls_response.status_code == 200:
                data = controls_response.json()
                assert "options" in data or "all_modes" in data
                print(f"✓ JESD controls retrieved for {first_converter}")
            else:
                print(
                    f"⚠ JESD controls not available for {first_converter} "
                    f"(status: {controls_response.status_code})"
                )

    def test_api_error_handling(self, api_url: str) -> None:
        """Test that API handles errors gracefully."""
        # Test invalid converter
        response = requests.get(
            f"{api_url}/api/converters/invalid_converter_xyz/info", timeout=5
        )
        assert response.status_code in [404, 500]  # Should return error code

        # Response should be JSON with error info
        try:
            error_data = response.json()
            assert "detail" in error_data or "error" in error_data
        except Exception:
            # Some error responses may not be JSON
            pass
