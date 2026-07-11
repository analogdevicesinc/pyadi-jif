"""Regression tests for per-instance component configuration state."""

import pytest

import adijif


@pytest.mark.parametrize(
    "component_type",
    [
        adijif.ad9680,
        adijif.ad9081_rx,
        adijif.ad9084_rx,
        adijif.ad9144,
        adijif.adrv9009_rx,
        adijif.hmc7044,
        adijif.ad9545,
        adijif.xilinx,
        adijif.adf4382,
    ],
)
def test_component_config_is_instance_local(component_type):
    """Runtime solver configuration cannot leak between component instances."""
    first = component_type(solver="gekko")
    second = component_type(solver="gekko")

    assert first.config is not second.config
    first.config["ownership_probe"] = object()
    assert "ownership_probe" not in second.config


def test_component_config_does_not_leak_across_converter_types():
    """Converters sharing the base-class default cannot contaminate each other."""
    adc = adijif.ad9680(solver="gekko")
    dac = adijif.ad9144(solver="gekko")

    adc.config["adc_only"] = 1
    assert "adc_only" not in dac.config


def test_nested_config_defaults_are_copied_per_instance():
    """Class templates with nested dictionaries retain defaults without sharing them."""
    first = adijif.ad9545(solver="gekko")
    second = adijif.ad9545(solver="gekko")

    assert first.config["r0"] == second.config["r0"] == 0
    assert first.config["PLL0"] is not second.config["PLL0"]
    first.config["PLL0"]["probe"] = 1
    assert "probe" not in second.config["PLL0"]
