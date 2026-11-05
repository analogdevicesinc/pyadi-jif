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
    # The DAC row also carries the fs/2 mirror (f -> fs - f) as an image.
    exp = [
        (3300, 3700, "S1", False, False),
        (16300, 16700, "S1", True, False),
    ]
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


def _dac_nco_plan(dac_nco_hz):
    plan = default_tx_plan()
    plan.signals = [s for s in plan.signals if s.name == "S1"]
    plan.cduc_dac_hz[0] = dac_nco_hz
    return plan


def test_dac_negative_complex_signal_captured():
    """A DAC NCO above fs/2 (or negative) still puts the signal out."""
    for nco, lo in ((12000e6, 7800), (-3000e6, 2800)):
        plan = _dac_nco_plan(nco)
        res = compute_tx(plan)
        sigs = {s.name: s for s in plan.signals}
        v = evaluate_dac(res.stages["dac0"], sigs)
        assert v.status == "ok", (nco, v.messages)
        assert v.messages[0] == "S1: 400 of 400 MHz captured"
        assert (lo, lo + 400, "S1", True, False) in spans_mhz(
            res.stages["dac0"].spans
        )


def test_dac_shows_fs2_mirror():
    """The DAC row covers [0, fs] with the fs/2 mirror flagged as image."""
    plan = _dac_nco_plan(12000e6)
    spans = spans_mhz(compute_tx(plan).stages["dac0"].spans)
    assert (11800, 12200, "S1", True, False) in spans
    plan = _dac_nco_plan(3000e6)
    spans = spans_mhz(compute_tx(plan).stages["dac0"].spans)
    assert spans == [
        (2800, 3200, "S1", False, False),
        (16800, 17200, "S1", True, False),
    ]


def test_dac_signal_overlapping_own_mirror_is_error():
    """A real DAC cannot hold a signal straddling DC without self-overlap."""
    plan = _dac_nco_plan(100e6)
    res = compute_tx(plan)
    sigs = {s.name: s for s in plan.signals}
    assert evaluate_dac(res.stages["dac0"], sigs).status == "error"


def _unreachable(plan):
    return [w for w in compute_tx(plan).warnings if "exceeds" not in w]


def test_default_tx_plan_has_no_warnings():
    assert compute_tx(default_tx_plan()).warnings == []


def test_signal_on_disabled_fduc_warns():
    plan = default_tx_plan()
    plan.signals.append(Signal("S3", 0, 100e6, 1))
    assert _unreachable(plan) == ["S3: FDUC1 is disabled"]


def test_signal_on_missing_fduc_warns():
    plan = default_tx_plan()
    plan.signals.append(Signal("S3", 0, 100e6, 9))
    assert _unreachable(plan) == ["S3: FDUC9 does not exist"]


def test_signal_on_disabled_cduc_warns():
    plan = default_tx_plan()
    plan.datapath.cduc_enabled = [False, True, True, True]
    assert _unreachable(plan) == ["S1: CDUC1 is disabled"]


def test_signal_on_unrouted_cduc_warns():
    plan = default_tx_plan()
    plan.datapath.fduc_enabled[2] = True
    plan.signals.append(Signal("S3", 0, 100e6, 2))
    assert _unreachable(plan) == ["S3: CDUC2 is not routed to any DAC"]
