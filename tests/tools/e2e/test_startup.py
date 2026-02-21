"""Quick test to verify Streamlit app startup works."""

import subprocess  # noqa: S404
import sys
import time
import requests
import pytest


def test_streamlit_startup():
    """Test that Streamlit app can start and respond to health checks."""
    print("Starting Streamlit app...")

    # Start the app using the same method as the fixture
    process = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-c",
            "from adijif.tools.explorer.cli import run_streamlit; "
            "run_streamlit(['--server.headless', 'true', '--logger.level', 'error'])",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    print(f"Process started with PID: {process.pid}")

    try:
        # Wait for it to be ready
        start_time = time.time()
        timeout = 60
        success = False

        while time.time() - start_time < timeout:
            # Check if process is alive
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print("❌ Process died!")
                print(f"Return code: {process.poll()}")
                if stderr:
                    print(f"Stderr: {stderr}")
                if stdout:
                    print(f"Stdout: {stdout}")
                pytest.fail(f"Process died with return code {process.poll()}")

            # Try health check
            try:
                response = requests.get("http://localhost:8501/_stcore/health", timeout=2)
                if response.status_code == 200:
                    print("✓ Streamlit app is responding to health checks!")
                    print(f"  Started in {time.time() - start_time:.1f} seconds")

                    # Test basic connectivity
                    response2 = requests.get("http://localhost:8501/", timeout=5)
                    print(f"✓ Main page returns status {response2.status_code}")
                    assert response2.status_code == 200
                    success = True
                    break
            except requests.exceptions.RequestException as e:
                elapsed = time.time() - start_time
                print(f"  [{elapsed:.1f}s] Health check failed: {e}")
                time.sleep(0.5)

        if not success:
            pytest.fail("Timeout: Streamlit app didn't respond within 60 seconds")

    finally:
        # Clean up
        process.terminate()
        process.wait(timeout=5)
        if process.poll() is None:
            process.kill()
        print("✓ Process terminated cleanly")
