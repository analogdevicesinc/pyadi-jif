"""Regression tests for complete system model resets."""

from pathlib import Path
from typing import Any

import adijif

PROFILE = (
    Path(__file__).parent
    / "apollo_profiles"
    / "ad9084_profiles"
    / "id00_stock_mode.json"
)


def test_model_reset_preserves_topology_and_rebinds_every_component():
    """A reset must rebuild solver state without changing system topology."""
    system: Any = adijif.system(
        "ad9084", "hmc7044", "xilinx", 125_000_000, solver="CPLEX"
    )
    system.add_pll_inline("adf4382", system.clock, system.converter)
    system.add_pll_sysref(
        "adf4030", system.clock, system.converter, system.fpga
    )
    system.converter.apply_profile_settings(str(PROFILE))
    system.fpga.setup_by_dev_kit_name("vcu118")
    system.converter.clocking_option = "direct"

    inline_pll = system.plls[0]
    sysref_pll = system.plls_sysref[0]
    sysref_connections = list(sysref_pll._connected_to_output)
    nested = [getattr(system.converter, name) for name in system.converter._nested]
    components: list[Any] = [
        system.clock,
        system.fpga,
        system.converter,
        *nested,
        inline_pll,
        sysref_pll,
    ]
    old_model = system.model
    system._solution = object()
    for component in components:
        component._solution = object()
        component._last_config = {"stale": True}

    system._model_reset()

    assert system.model is not old_model
    assert system.plls == [inline_pll]
    assert system.plls_sysref == [sysref_pll]
    assert inline_pll._connected_to_output == system.converter.name
    assert sysref_pll._connected_to_output == sysref_connections
    assert system._solution is None
    assert system._initialized is False
    assert system._last_clocks is None
    for component in components:
        assert component.model is system.model
        assert component._solution is None
        assert component._last_config is None

    clocks = system.initialize()
    assert "AD9084_ref_clk_from_ext_pll" in clocks
    assert "adf4030_ref_clk" in clocks
    assert "adc_sysref" in clocks
    assert "dac_sysref" in clocks
