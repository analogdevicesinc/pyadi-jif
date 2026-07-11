"""Regression tests for device-instance state and focused model defects."""

from types import SimpleNamespace

import pytest

import adijif
from adijif.fpgas.xilinx.ultrascaleplus import QPLL


@pytest.mark.parametrize(
    "device_type, mutable_attribute",
    [
        (adijif.ad9081_rx, "cddc_decimations"),
        (adijif.ad9081_tx, "fduc_enabled"),
        (adijif.ad9084_rx, "cddc_decimations"),
        (adijif.ad9088_rx, "cddc_decimations"),
        (adijif.ad9084_tx, "fduc_enabled"),
        (adijif.ad9088_tx, "fduc_enabled"),
    ],
)
def test_converter_datapath_is_per_instance(device_type, mutable_attribute):
    """Mutating one converter datapath must not affect another instance."""
    first = device_type(solver="gekko")
    second = device_type(solver="gekko")

    assert first.datapath is not second.datapath
    first_values = getattr(first.datapath, mutable_attribute)
    second_values = getattr(second.datapath, mutable_attribute)
    assert first_values is not second_values

    original = list(second_values)
    first_values[0] = not first_values[0] if isinstance(first_values[0], bool) else 99
    assert getattr(second.datapath, mutable_attribute) == original


def test_ad9084_tx_runs_common_initialization():
    """AD9084 TX must initialize the state guaranteed by core."""
    device = adijif.ad9084_tx(solver="gekko")

    assert device.model is not None
    assert device.configs == []
    assert device._objectives == []
    assert device._disabled_objectives == set()
    assert device._last_config is None


def test_xilinx_runtime_state_is_per_instance():
    """FPGA constraint-build collections must not leak between instances."""
    first = adijif.xilinx(solver="gekko")
    second = adijif.xilinx(solver="gekko")

    for attribute in (
        "_clock_names",
        "_used_progdiv",
        "_device_clock_source",
        "_out_clk_select",
        "configs",
        "_transceiver_models",
        "_use_gearbox",
        "_sps",
    ):
        assert getattr(first, attribute) is not getattr(second, attribute)

    first._clock_names.append("first_only")
    first._use_gearbox["converter"] = True
    assert second._clock_names == []
    assert second._use_gearbox == {}


@pytest.mark.parametrize(
    "clock_type, message",
    [
        (adijif.hmc7044, "HMC7044"),
        (adijif.ltc6952, "LTC6952"),
    ],
)
def test_gekko_restricted_output_dividers_are_detected(clock_type, message):
    """Restricted divider lists must not bypass the documented GEKKO guard."""
    clock = clock_type(solver="gekko")
    clock.d = [1]

    with pytest.raises(Exception, match=message):
        clock.set_requested_clocks(100_000_000, [10_000_000], ["out"])


@pytest.mark.parametrize("transceiver_type", ["GTHE4", "GTYE4"])
def test_ultrascale_qpll_clkout_rate_can_be_set(transceiver_type):
    """Valid GTH and GTY clock-output-rate selections must be retained."""
    qpll = object.__new__(QPLL)
    qpll.parent = SimpleNamespace(transceiver_type=transceiver_type)

    qpll.QPLL_CLKOUTRATE = 1

    assert qpll.QPLL_CLKOUTRATE == 1


def test_ultrascale_qpll_clkout_rate_rejects_unavailable_value():
    """GTHE4 supports rate selections one and two only."""
    qpll = object.__new__(QPLL)
    qpll.parent = SimpleNamespace(transceiver_type="GTHE4")

    with pytest.raises(Exception, match="QPLL_CLKOUTRATE"):
        qpll.QPLL_CLKOUTRATE = 4
