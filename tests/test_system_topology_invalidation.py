"""Regression tests for system topology changes after initialization."""

from typing import Any

import pytest

import adijif


@pytest.mark.parametrize(
    "add_pll,expected_clocks",
    [
        (
            lambda system: system.add_pll_inline(
                "adf4382", system.clock, system.converter
            ),
            {"adf4382_ref_clk", "AD9680_ref_clk_from_ext_pll"},
        ),
        (
            lambda system: system.add_pll_sysref(
                "adf4030", system.clock, system.converter, system.fpga
            ),
            {"adf4030_ref_clk", "AD9680_sysref"},
        ),
    ],
)
def test_adding_pll_after_initialize_rebuilds_system_topology(
    add_pll, expected_clocks
):
    """A newly added PLL must appear in the next initialized clock bundle."""
    system: Any = adijif.system(
        "ad9680", "hmc7044", "xilinx", 125_000_000, solver="CPLEX"
    )
    system.fpga.setup_by_dev_kit_name("zc706")
    old_model = system.model
    old_clocks = system.initialize()

    add_pll(system)

    assert system.model is not old_model
    assert system._initialized is False
    assert system._last_clocks is None
    new_clocks = system.initialize()
    assert new_clocks is not old_clocks
    assert expected_clocks <= set(new_clocks)


def test_rejected_pll_change_preserves_initialized_topology():
    """Validation failures must not discard otherwise valid cached wiring."""
    system: Any = adijif.system(
        "ad9680", "hmc7044", "xilinx", 125_000_000, solver="CPLEX"
    )
    old_model = system.model
    system.fpga.setup_by_dev_kit_name("zc706")
    old_clocks = system.initialize()

    with pytest.raises(ValueError, match="Unknown pll"):
        system.add_pll_inline("not-a-pll", system.clock, system.converter)
    with pytest.raises(AssertionError, match="Converter or FPGA"):
        system.add_pll_sysref("adf4030", system.clock)

    assert system.model is old_model
    assert system._initialized is True
    assert system._last_clocks is old_clocks
