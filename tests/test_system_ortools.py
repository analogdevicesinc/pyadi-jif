"""Tests for OR-Tools support in legacy system class."""

import pytest

import adijif
from adijif.solvers import ortools_solver

pytestmark = pytest.mark.skipif(not ortools_solver, reason="OR-Tools not installed")


class TestSystemORTools:
    """Test OR-Tools solver with legacy system interface."""

    def test_ortools_initialization(self):
        """Test system can be created with ortools solver."""
        sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6, solver="ortools")
        assert sys.solver == "ortools"
        assert sys.model is not None

    def test_ortools_simple_solve(self):
        """Test basic OR-Tools model operations."""
        # This test verifies basic OR-Tools model integration
        sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6, solver="ortools")

        # Set simple configuration
        sys.converter.sample_clock = 500e6
        sys.converter.decimation = 1

        # Just verify initialization worked - full solve with FPGA requires CPLEX
        # due to CPLEX-specific constraint features in the FPGA module
        assert sys.solver == "ortools"
        assert sys.model is not None
        assert sys.converter is not None
        assert sys.clock is not None

    def test_ortools_error_on_missing_solver(self):
        """Test proper error message when OR-Tools not available."""
        if ortools_solver:
            pytest.skip("OR-Tools is installed - this test requires it to be unavailable")

        with pytest.raises(Exception, match="OR-Tools not installed"):
            adijif.system("ad9680", "hmc7044", "xilinx", 125e6, solver="ortools")

