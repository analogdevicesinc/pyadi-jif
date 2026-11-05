"""Tests for the Tx stage chain."""

from adijif.freqplan.checks import evaluate_dac
from adijif.freqplan.rx import Signal
from adijif.freqplan.spectrum import spans_mhz
from adijif.freqplan.tx import compute_tx, default_tx_plan


def test_tx_single_signal():
    plan = default_tx_plan()
    plan.signals = [s for s in plan.signals if s.name == "S1"]
    plan.datapath.fduc_nco_frequencies[0] = 0.5e9
    res = compute_tx(plan)
    exp = [(3300, 3700, "S1", False, False)]
    assert spans_mhz(res.stages["fduc0"].spans) == [
        (300, 700, "S1", False, False)
    ]
    assert spans_mhz(res.stages["dac0"].spans) == exp
    assert spans_mhz(res.stages["dac1"].spans) == exp


def test_tx_default_ok():
    plan = default_tx_plan()
    res = compute_tx(plan)
    sigs = {s.name: s for s in plan.signals}
    dacs = [s for n, s in res.stages.items() if n.startswith("dac")]
    assert len(dacs) == 4
    for st in dacs:
        assert evaluate_dac(st, sigs).status == "ok"


def test_tx_mirror_collision():
    plan = default_tx_plan()
    plan.signals = [Signal("S1", 0, 0.2e9, 0), Signal("S2", 0, 0.2e9, 1)]
    dp = plan.datapath
    dp.fduc_enabled = [True, True] + [False] * 6
    dp.fduc_nco_frequencies[:2] = [0.5e9, -0.5e9]
    plan.cduc_dac_hz[0] = 0
    res = compute_tx(plan)
    sigs = {s.name: s for s in plan.signals}
    assert evaluate_dac(res.stages["dac0"], sigs).status == "error"


def test_tx_fduc_passband_warning():
    plan = default_tx_plan()
    plan.signals = [Signal("S1", 0, 2.4e9, 0)]
    res = compute_tx(plan)
    assert any("S1 exceeds FDUC0 passband" in w for w in res.warnings)


def test_tx_disabled_cduc():
    plan = default_tx_plan()
    plan.datapath.cduc_enabled = [False, True, True, True]
    res = compute_tx(plan)
    assert "cduc0" not in res.stages
    assert res.stages["fduc0"].error == "source CDUC1 is disabled"
    assert res.stages["fduc0"].spans == []
