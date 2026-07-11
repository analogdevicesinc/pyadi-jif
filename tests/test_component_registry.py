"""Tests for validated device-model construction."""

import gc

import pytest

import adijif
from adijif.registry import COMPONENT_REGISTRY, get_component_class


@pytest.mark.parametrize(
    ("kind", "name", "expected"),
    [
        ("converter", "AD9084_RX", adijif.ad9084_rx),
        ("clock", "HMC7044", adijif.hmc7044),
        ("fpga", "XILINX", adijif.xilinx),
        ("pll", "ADF4382", adijif.adf4382),
    ],
)
def test_registry_resolves_supported_names_case_insensitively(
    kind, name, expected
):
    """Existing lowercase names and uppercase aliases resolve identically."""
    assert get_component_class(kind, name) is expected


def test_registry_rejects_unknown_and_executable_names():
    """Component names are data and cannot execute arbitrary expressions."""
    with pytest.raises(ValueError, match="Unknown converter"):
        get_component_class("converter", "__import__('os').system('false')")
    with pytest.raises(ValueError, match="Unknown component kind"):
        get_component_class("unknown", "ad9084_rx")


def test_registry_matches_public_supported_part_lists():
    """Public discovery lists cannot silently drift from construction support."""
    from adijif.clocks import supported_parts as clocks
    from adijif.converters import supported_parts as converters
    from adijif.plls import supported_parts as plls

    assert set(clocks) <= set(COMPONENT_REGISTRY["clock"])
    assert set(converters) <= set(COMPONENT_REGISTRY["converter"])
    assert set(plls) <= set(COMPONENT_REGISTRY["pll"])


def test_system_uses_registry_for_component_construction():
    """System construction supports aliases and rejects unknown names clearly."""
    system = adijif.system("AD9680", "HMC7044", "XILINX", 125_000_000, "gekko")
    assert isinstance(system.converter, adijif.ad9680)
    assert isinstance(system.clock, adijif.hmc7044)
    assert isinstance(system.fpga, adijif.xilinx)

    system.add_pll_inline("ADF4382", system.clock, system.converter)
    assert isinstance(system.plls[-1], adijif.adf4382)

    with pytest.raises(ValueError, match="Unknown converter"):
        adijif.system("not_a_device", "hmc7044", "xilinx", 125_000_000, "gekko")


def test_failed_system_construction_has_safe_cleanup(recwarn):
    """Partially initialized systems must not raise from their destructor."""
    with pytest.raises(Exception, match="Unknown solver"):
        adijif.system("ad9680", "hmc7044", "xilinx", 125_000_000, "invalid")

    gc.collect()
    assert not [warning for warning in recwarn if "system.__del__" in str(warning.message)]
