"""Tests for the AD9084 adapter and Rx stage chain."""

import pytest

from adijif.freqplan.parts import get_adapter
from adijif.freqplan.rx import Signal, compute_rx, default_rx_plan
from adijif.freqplan.spectrum import spans_mhz


def test_get_adapter():
    assert get_adapter("AD9084").num_adcs == 4
    with pytest.raises(ValueError, match="Unsupported part"):
        get_adapter("AD9999")


def test_rx_chain_single_signal():
    plan = default_rx_plan()
    plan.signals = [Signal("S1", 1.2e9, 0.4e9, 0)]
    plan.cddc_rf_hz[0] = 1.6e9
    plan.datapath.fddc_enabled = [True] + [False] * 7
    plan.datapath.fddc_nco_frequencies[0] = -0.4e9
    plan.datapath.fddc_decimations[0] = 4
    st = compute_rx(plan).stages
    assert spans_mhz(st["cddc0"].spans) == [
        (-600, -200, "S1", False, False),
        (2000, 2400, "S1", True, True),
    ]
    assert spans_mhz(st["fddc0"].spans) == [(-200, 200, "S1", False, False)]
    assert st["fddc0"].rate_hz == 1.25e9
    assert st["fddc0"].passband_hz == 0.5e9
    assert st["fddc0"].is_output
    assert not st["cddc0"].is_output
    assert st["cddc1"].is_output
    assert st["adc0"].kind == "adc" and st["adc0"].parent is None
    assert st["cddc0"].parent == "adc0" and st["fddc0"].parent == "cddc0"


def test_disabled_source_cddc_marks_error():
    plan = default_rx_plan()
    plan.datapath.cddc_enabled[0] = False
    st = compute_rx(plan).stages
    assert "cddc0" not in st
    assert st["fddc0"].error == "source CDDC1 is disabled"
    assert st["fddc0"].spans == []
    assert st["fddc2"].error is None


def test_rx_warnings():
    plan = default_rx_plan()
    plan.signals[0] = Signal("S1", 10e9, 0.4e9, 0)
    assert "S1 straddles a Nyquist boundary" in compute_rx(plan).warnings

    plan = default_rx_plan()
    plan.adc_to_cddc = [0, 0, 2, 3]
    plan.cddc_rf_hz[1] = 12e9
    assert (
        "ADC0 CDDCs target different Nyquist zones [1, 2]"
        in compute_rx(plan).warnings
    )
