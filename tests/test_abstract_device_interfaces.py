"""Tests for callable abstract device interfaces."""

import inspect

from adijif.clocks.clock import clock
from adijif.fpgas.fpga import fpga


def test_clock_abstract_operations_are_methods():
    """Clock discovery operations accept inputs and must remain callable."""
    assert inspect.isfunction(inspect.getattr_static(clock, "find_dividers"))
    assert inspect.isfunction(
        inspect.getattr_static(clock, "list_available_references")
    )


def test_fpga_abstract_operations_are_methods():
    """FPGA discovery and extraction operations must remain callable."""
    for operation in ("determine_cpll", "determine_qpll", "get_config"):
        assert inspect.isfunction(inspect.getattr_static(fpga, operation))
