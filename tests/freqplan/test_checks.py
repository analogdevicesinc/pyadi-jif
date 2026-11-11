"""Tests for per-output capture/interference verdicts."""

import pytest

from adijif.freqplan.checks import evaluate_dac, evaluate_output
from adijif.freqplan.rx import Signal, StageOutput, compute_rx, default_rx_plan
from adijif.freqplan.spectrum import Span

SIGS = {
    "S1": Signal("S1", 0.0, 400e6, 0),
    "S2": Signal("S2", 0.0, 100e6, 0),
    "S3": Signal("S3", 0.0, 1200e6, 0),
    "T": Signal("T", 0.0, 0.0, 0),
}


def _stage(spans, rate=1e9, p=0.5e9, error=None):
    return StageOutput("out", "cddc", rate, p, spans, None, True, error)


def test_full_capture_ok():
    v = evaluate_output(_stage([Span(-0.2e9, 0.2e9, "S1")]), SIGS, ["S1"])
    assert v.status == "ok"
    assert v.captures[0].fraction == 1.0
    assert v.used_fraction == pytest.approx(0.4)
    assert v.can_decimate_more
    assert "S1: 400 of 400 MHz captured" in v.messages
    assert "could decimate further" in v.messages


def test_partial_capture_warns():
    v = evaluate_output(_stage([Span(-0.6e9, 0.6e9, "S3")]), SIGS, ["S3"])
    assert v.status == "warn"
    assert v.captures[0].captured_hz == pytest.approx(1.0e9)


def test_other_signal_is_error():
    spans = [Span(-0.2e9, 0.2e9, "S1"), Span(0.3e9, 0.4e9, "S2")]
    v = evaluate_output(_stage(spans), SIGS, ["S1"])
    assert v.status == "error"
    assert v.interference[0].overlap_hz == pytest.approx(0.1e9)
    assert "S2 in band (100 MHz)" in v.messages


def test_attenuated_interference_warns():
    spans = [
        Span(-0.2e9, 0.2e9, "S1"),
        Span(0.3e9, 0.4e9, "S2", attenuated=True),
    ]
    v = evaluate_output(_stage(spans), SIGS, ["S1"])
    assert v.status == "warn"


def test_image_is_error():
    spans = [Span(-0.2e9, 0.2e9, "S1"), Span(0.25e9, 0.3e9, "S1", image=True)]
    v = evaluate_output(_stage(spans), SIGS, ["S1"])
    assert v.status == "error"


def test_no_targets_lists_present():
    spans = [Span(-0.2e9, 0.2e9, "S1"), Span(0.3e9, 0.4e9, "S2")]
    v = evaluate_output(_stage(spans), SIGS, [])
    assert v.status == "ok"
    assert {c.signal for c in v.captures} == {"S1", "S2"}


def test_cw_tone_full_capture():
    v = evaluate_output(_stage([Span(0.1e9, 0.1e9, "T")]), SIGS, ["T"])
    assert v.status == "ok"
    assert v.captures[0].fraction == 1.0


def test_stage_error_is_error_verdict():
    st = StageOutput(
        "fddc0",
        "fddc",
        0.0,
        0.0,
        [],
        "cddc0",
        True,
        error="source CDDC0 is disabled",
    )
    v = evaluate_output(st, SIGS, ["S1"])
    assert v.status == "error"
    assert v.messages == ["source CDDC0 is disabled"]


def test_dac_ignores_unrouted_signals():
    st = StageOutput(
        "dac0", "dac", 20e9, 8e9, [Span(3.0e9, 3.4e9, "S1")], None, True
    )
    v = evaluate_dac(st, SIGS)
    assert v.status == "ok"
    assert {c.signal for c in v.captures} == {"S1"}
    assert not v.can_decimate_more


def test_dac_mirror_collision():
    st = StageOutput(
        "dac0",
        "dac",
        20e9,
        8e9,
        [Span(0.4e9, 0.6e9, "S1"), Span(0.4e9, 0.6e9, "S2", image=True)],
        None,
        True,
    )
    assert evaluate_dac(st, SIGS).status == "error"


def test_default_rx_plan_all_ok():
    plan = default_rx_plan()
    sigs = {s.name: s for s in plan.signals}
    res = compute_rx(plan)
    outs = [(ch, st) for ch, st in res.stages.items() if st.is_output]
    assert outs
    for ch, st in outs:
        v = evaluate_output(st, sigs, plan.targets.get(ch, []))
        assert v.status == "ok", (ch, v.messages)
