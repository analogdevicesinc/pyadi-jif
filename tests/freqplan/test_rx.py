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


def _two_tone_plan(rf_a_hz, rf_b_hz, cddc_rf_hz):
    plan = default_rx_plan()
    plan.signals = [
        Signal("A", rf_a_hz, 50e6, 0),
        Signal("B", rf_b_hz, 50e6, 0),
    ]
    plan.cddc_rf_hz[0] = cddc_rf_hz
    plan.datapath.cddc_enabled = [True, False, False, False]
    plan.datapath.fddc_enabled = [False] * 8
    plan.targets = {}
    return plan


@pytest.mark.parametrize("zone", [1, 2, 3, 4])
def test_cddc_output_in_rf_order(zone):
    """In every Nyquist zone the RF-higher signal sits above the CDDC centre."""
    base = (zone - 1) * 10e9
    plan = _two_tone_plan(base + 2.0e9, base + 2.3e9, base + 2.15e9)
    spans = spans_mhz(compute_rx(plan).stages["cddc0"].spans)
    primary = {s[2]: (s[0], s[1]) for s in spans if not s[3]}
    assert primary["A"] == (-175, -125)
    assert primary["B"] == (125, 175)


@pytest.mark.parametrize("zone", [2, 4])
def test_even_zone_fddc_positive_nco_selects_rf_higher(zone):
    """An FDDC at +150 MHz under an even-zone CDDC selects the RF-higher B."""
    from adijif.freqplan.checks import evaluate_output

    base = (zone - 1) * 10e9
    plan = _two_tone_plan(base + 2.0e9, base + 2.3e9, base + 2.15e9)
    dp = plan.datapath
    dp.fddc_enabled = [True] + [False] * 7
    dp.fddc_source[0] = 1
    dp.fddc_decimations[0] = 16
    dp.fddc_nco_frequencies[0] = 150e6
    plan.targets = {"fddc0": ["B"]}
    res = compute_rx(plan)
    sigs = {s.name: s for s in plan.signals}
    v = evaluate_output(res.stages["fddc0"], sigs, ["B"])
    assert v.status == "ok", v.messages
    assert spans_mhz(res.stages["fddc0"].spans) == [
        (-25, 25, "B", False, False)
    ]
