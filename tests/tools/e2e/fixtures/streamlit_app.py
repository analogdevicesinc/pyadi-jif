"""Streamlit app lifecycle management for E2E tests."""

import subprocess  # noqa: S404
import sys
import time

import requests


def start_streamlit_app(port: int = 8501, timeout: int = 60) -> subprocess.Popen:
    """Start Streamlit app and wait for readiness.

    Args:
        port: Port to run Streamlit on
        timeout: Maximum time to wait for app startup (seconds)

    Returns:
        subprocess.Popen: Process handle for the Streamlit app

    Raises:
        TimeoutError: If app fails to start within timeout
    """
    # Kill any existing process on port
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], capture_output=True, check=False, text=True
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                try:
                    subprocess.run(
                        ["kill", "-9", pid], check=False, capture_output=True
                    )
                except Exception:  # noqa: S110
                    pass
    except Exception:  # noqa: S110
        pass

    # Start streamlit using Python to call jiftools directly
    # This is more reliable than trying to run streamlit as a subprocess command
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "from adijif.tools.explorer.cli import run_streamlit; "
            "run_streamlit(['--server.headless', 'true', '--logger.level', 'error'])",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=None,  # Don't set preexec_fn to avoid issues
    )

    # Wait for health check with extended timeout
    start_time = time.time()
    last_error = None
    health_check_attempts = 0

    while time.time() - start_time < timeout:
        # Check if process is still alive
        poll_result = process.poll()
        if poll_result is not None:
            # Process has died
            stdout, stderr = process.communicate(timeout=1)
            error_msg = (
                f"Streamlit process exited with code {poll_result}\n"
                f"stderr: {stderr}\nstdout: {stdout}"
            )
            raise TimeoutError(error_msg)

        try:
            response = requests.get(
                f"http://localhost:{port}/_stcore/health", timeout=2
            )
            if response.status_code == 200:
                # Minimal stabilization time instead of 3 seconds
                time.sleep(0.5)
                return process
        except requests.exceptions.ConnectionError as e:
            last_error = str(e)
            health_check_attempts += 1
            time.sleep(0.2)  # Reduced from 0.5
        except requests.exceptions.Timeout as e:
            last_error = str(e)
            health_check_attempts += 1
            time.sleep(0.2)  # Reduced from 0.5
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            health_check_attempts += 1
            time.sleep(0.2)  # Reduced from 0.5

    process.terminate()
    error_msg = (
        f"Streamlit failed to start within {timeout}s "
        f"({health_check_attempts} health check attempts)"
    )
    if last_error:
        error_msg += f"\nLast error: {last_error}"

    # Try to get any output from the process
    try:
        stdout, stderr = process.communicate(timeout=1)
        if stderr:
            error_msg += f"\nStderr: {stderr}"
        if stdout:
            error_msg += f"\nStdout: {stdout}"
    except Exception:  # noqa: S110
        pass

    raise TimeoutError(error_msg)


def stop_streamlit_app(process: subprocess.Popen, timeout: int = 10) -> None:
    """Stop Streamlit app gracefully.

    Args:
        process: Process handle to stop
        timeout: Maximum time to wait for graceful shutdown (seconds)
    """
    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
