"""Tests for OR-Tools example scripts.

Verifies that OR-Tools examples run successfully and produce feasible solutions
when OR-Tools is installed. Tests skip gracefully when OR-Tools is not available.
"""

import subprocess
import sys
from importlib.util import find_spec

import pytest

# Check if OR-Tools is available
ortools_available = find_spec("ortools") is not None


@pytest.mark.skipif(not ortools_available, reason="OR-Tools not installed")
class TestORToolsExamples:
    """Test OR-Tools example scripts."""

    def test_hmc7044_ortools(self):
        """Test HMC7044 OR-Tools example runs and produces feasible solution."""
        result = subprocess.run(
            [sys.executable, "examples/hmc7044_ortools.py"],
            capture_output=True,
            text=True,
            cwd="/home/tcollins/dev/pyadi-jif",
        )

        # Should not error
        assert result.returncode == 0, (
            f"Example failed with exit code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

        # Should find feasible solution
        output = result.stdout.lower()
        assert (
            "feasible" in output
        ), f"Expected 'feasible' in output, got:\n{result.stdout}"

    def test_adf4371_ortools(self):
        """Test ADF4371 OR-Tools example runs and produces feasible solution."""
        result = subprocess.run(
            [sys.executable, "examples/adf4371_ortools.py"],
            capture_output=True,
            text=True,
            cwd="/home/tcollins/dev/pyadi-jif",
        )

        # Should not error
        assert result.returncode == 0, (
            f"Example failed with exit code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

        # Should find feasible solution
        output = result.stdout.lower()
        assert (
            "feasible" in output
        ), f"Expected 'feasible' in output, got:\n{result.stdout}"

    def test_simple_system_ortools(self):
        """Test simple system OR-Tools example runs."""
        result = subprocess.run(
            [sys.executable, "examples/simple_system_ortools.py"],
            capture_output=True,
            text=True,
            cwd="/home/tcollins/dev/pyadi-jif",
        )

        # Should not error
        assert result.returncode == 0, (
            f"Example failed with exit code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

        # Should indicate solution (exact text depends on implementation)
        output = result.stdout.lower()
        assert (
            "solution" in output or "feasible" in output
        ), f"Expected solution indication in output, got:\n{result.stdout}"

    def test_clock_optimization_ortools(self):
        """Test clock optimization OR-Tools example runs."""
        result = subprocess.run(
            [sys.executable, "examples/clock_optimization_ortools.py"],
            capture_output=True,
            text=True,
            cwd="/home/tcollins/dev/pyadi-jif",
        )

        # Should not error
        assert result.returncode == 0, (
            f"Example failed with exit code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

        # Should indicate solution
        output = result.stdout.lower()
        assert (
            "solution" in output or "feasible" in output
        ), f"Expected solution indication in output, got:\n{result.stdout}"
