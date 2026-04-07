"""Quick test to verify Streamlit app startup works."""

import subprocess  # noqa: S404
import sys
import time

import pytest
import requests


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

    # Wait for it to be ready
    start_time = time.time()
    timeout = 60

    while time.time() - start_time < timeout:
        # Check if process is alive
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            pytest.fail(
                f"Process died! Return code: {process.poll()}\n"
                f"Stderr: {stderr}\nStdout: {stdout}"
            )

        # Try health check
        try:
            response = requests.get(
                "http://localhost:8501/_stcore/health", timeout=2
            )
            if response.status_code == 200:
                print("✓ Streamlit app is responding to health checks!")
                print(f"  Started in {time.time() - start_time:.1f} seconds")

                # Test basic connectivity
                response2 = requests.get("http://localhost:8501/", timeout=5)
                print(f"✓ Main page returns status {response2.status_code}")

                # Clean up
                process.terminate()
                process.wait(timeout=5)
                print("✓ Process terminated cleanly")
                return
        except requests.exceptions.RequestException as e:
            elapsed = time.time() - start_time
            print(f"  [{elapsed:.1f}s] Health check failed: {e}")
            time.sleep(0.5)

    process.terminate()
    pytest.fail("Timeout: Streamlit app didn't respond within 60 seconds")


if __name__ == "__main__":
    try:
        test_streamlit_startup()
        sys.exit(0)
    except Exception:
        sys.exit(1)
