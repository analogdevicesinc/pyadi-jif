"""Downstream filter masks must agree with the frequency planner's DSP model."""

import pytest

from adijif.freqplan import (
    Signal,
    Span,
    StageOutput,
    compute_rx,
    ddc_stage,
    default_rx_plan,
)
from adijif.tools.explorer.src.pages.helpers.freqplan_filters import (
    downstream_filter_regions,
    rx_capture_regions,
    rx_filter_overlays,
)


def _stages(kind="cddc", decimation=4, alpha=0.8):
    source = StageOutput(f"{kind}0", kind, 100e6, 50e6, [], None, False)
    child_kind = "cddc" if kind == "adc" else "fddc"
    rate = source.rate_hz / decimation
    child = StageOutput(
        f"{child_kind}0",
        child_kind,
        rate,
        alpha * rate / 2,
        [],
        source.channel,
        True,
    )
    return source, child


def _capture_plan():
    plan = default_rx_plan()
    plan.signals = []
    plan.cddc_rf_hz[0] = 5e9
    plan.datapath.cddc_enabled = [True, False, False, False]
    plan.datapath.fddc_enabled = [
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
    ]
    plan.datapath.fddc_decimations[:2] = [4, 4]
    return plan


def test_composite_capture_merges_overlaps_without_requiring_input_signals():
    plan = _capture_plan()
    plan.datapath.fddc_nco_frequencies[:2] = [-200e6, 200e6]
    rows = rx_capture_regions(plan, compute_rx(plan))
    captured = [r for r in rows if r["region"] == "Captured"]
    assert [(r["stage"], r["lo_mhz"], r["hi_mhz"]) for r in captured] == [
        ("ADC0", 4300, 5700)
    ]
    assert captured[0]["fddcs"] == "FDDC0, FDDC1"
    assert captured[0]["captured_mhz"] == 1400
    assert all(r["region"] == "Blocked" for r in rows if r["stage"] != "ADC0")


def test_composite_capture_preserves_gaps_and_combines_coarse_branches():
    plan = _capture_plan()
    plan.datapath.cddc_enabled[1] = True
    plan.adc_to_cddc[1] = 0
    plan.cddc_rf_hz[1] = 8e9
    plan.datapath.fddc_source[1] = 2
    rows = rx_capture_regions(plan, compute_rx(plan))
    captured = [r for r in rows if r["region"] == "Captured"]
    assert [(r["lo_mhz"], r["hi_mhz"]) for r in captured] == [
        (4500, 5500),
        (7500, 8500),
    ]


@pytest.mark.parametrize("coarse_nco", [0.1e9, 5e9, 9.8e9, 15e9, 25e9])
@pytest.mark.parametrize("fine_nco", [-7.3e9, 0, 2.3e9])
@pytest.mark.parametrize(
    "decimations,alpha",
    [
        ((1, 1), 0.8),
        ((1, 4), 0.5),
        ((4, 1), 0.95),
        ((4, 4), 0.8),
        ((2, 2), 0.5),
        ((4, 4), 0.5),
        ((4, 4), 0.95),
    ],
)
def test_composite_capture_matches_tones_through_complete_rx_chain(
    coarse_nco, fine_nco, decimations, alpha
):
    """Independent forward DSP verifies inverse masks, including inversion/aliasing."""
    plan = _capture_plan()
    plan.alpha = alpha
    plan.cddc_rf_hz[0] = coarse_nco
    plan.datapath.cddc_decimations[0] = decimations[0]
    plan.datapath.fddc_decimations[:2] = [decimations[1]] * 2
    plan.datapath.fddc_nco_frequencies[:2] = [fine_nco, -0.7e9]
    rows = [
        r
        for r in rx_capture_regions(plan, compute_rx(plan))
        if r["stage"] == "ADC0"
    ]
    for i in range(137):
        freq = plan.adc_rate_hz / 2 * (i + 0.37) / 137
        plan.signals = [Signal("probe", freq, 0, 0)]
        out = compute_rx(plan)
        spans = out.stages["fddc0"].spans + out.stages["fddc1"].spans
        expected = (
            "Blocked"
            if not spans
            else (
                "Transition" if all(s.attenuated for s in spans) else "Captured"
            )
        )
        row = next(r for r in rows if r["lo_mhz"] < freq / 1e6 < r["hi_mhz"])
        assert row["region"] == expected, (freq, row, spans)


def test_composite_capture_excludes_disabled_paths_and_honors_bypass():
    plan = _capture_plan()
    plan.datapath.cddc_decimations[0] = 1
    plan.datapath.fddc_decimations[:2] = [1, 1]
    rows = rx_capture_regions(plan, compute_rx(plan))
    assert [
        (r["lo_mhz"], r["hi_mhz"], r["region"])
        for r in rows
        if r["stage"] == "ADC0"
    ] == [(0, 10000, "Captured")]
    plan.datapath.fddc_enabled = [False] * 8
    assert all(
        r["region"] == "Blocked"
        for r in rx_capture_regions(plan, compute_rx(plan))
    )
    plan.datapath.fddc_enabled[0] = True
    plan.datapath.cddc_enabled[0] = False
    assert all(
        r["region"] == "Blocked"
        for r in rx_capture_regions(plan, compute_rx(plan))
    )


def test_filter_mask_separates_pass_transition_and_rejection():
    source, child = _stages()
    regions = downstream_filter_regions(source, child, 0)
    assert [(r["lo_mhz"], r["hi_mhz"], r["region"]) for r in regions] == [
        (-50, -15, "Rejected"),
        (-15, -10, "Transition"),
        (10, 15, "Transition"),
        (15, 50, "Rejected"),
    ]
    assert {r["filter"] for r in regions} == {"FDDC0"}


def test_filter_mask_wraps_a_shifted_passband_at_nyquist():
    source, child = _stages()
    regions = downstream_filter_regions(source, child, 45e6)
    assert [(r["lo_mhz"], r["hi_mhz"], r["region"]) for r in regions] == [
        (-45, -40, "Transition"),
        (-40, 30, "Rejected"),
        (30, 35, "Transition"),
    ]


@pytest.mark.parametrize("kind", ["adc", "cddc"])
@pytest.mark.parametrize("nco_mhz", [-145, -49, 0, 47, 145])
@pytest.mark.parametrize("decimation,alpha", [(1, 0.8), (2, 0.5), (4, 0.95)])
def test_filter_mask_matches_tones_through_the_actual_ddc(
    kind, nco_mhz, decimation, alpha
):
    """Probe both spectral images for real ADC input, including wrapped NCOs."""
    source, child = _stages(kind, decimation, alpha)
    regions = downstream_filter_regions(source, child, nco_mhz * 1e6)
    lo = 0 if kind == "adc" else -50e6
    hi = 50e6
    for i in range(113):
        freq = lo + (hi - lo) * (i + 0.37) / 113
        spans = [Span(freq, freq, "probe")]
        if kind == "adc":
            spans.append(Span(-freq, -freq, "probe", image=True))
        out = ddc_stage(spans, source.rate_hz, nco_mhz * 1e6, decimation, alpha)
        expected = (
            "Rejected"
            if not out
            else (
                "Transition" if all(span.attenuated for span in out) else None
            )
        )
        region = next(
            (
                r["region"]
                for r in regions
                if r["lo_mhz"] < freq / 1e6 < r["hi_mhz"]
            ),
            None,
        )
        assert region == expected, (freq, nco_mhz, regions, out)


def test_selected_rx_path_uses_folded_coarse_nco_and_only_its_fine_filter():
    plan = default_rx_plan()
    plan.cddc_rf_hz[0] = 12e9  # ADC sees 8 GHz in the even Nyquist zone.
    plan.datapath.fddc_nco_frequencies[0] = 2.3e9
    result = compute_rx(plan)
    masks = rx_filter_overlays(plan, result, ("adc0", "cddc0", "fddc0"))
    assert set(masks) == {"adc0", "cddc0"}
    assert [(r["lo_mhz"], r["hi_mhz"], r["region"]) for r in masks["adc0"]] == [
        (0, 5000, "Rejected"),
        (5000, 6000, "Transition"),
    ]
    assert {r["filter"] for r in masks["cddc0"]} == {"FDDC0"}
    assert rx_filter_overlays(plan, result, ("adc0", "cddc0")) == {
        "adc0": masks["adc0"]
    }


def test_disabled_error_and_bypassed_filters_have_no_mask():
    source, child = _stages(decimation=1)
    assert downstream_filter_regions(source, child, 0) == []
    child.error = "source disabled"
    child.rate_hz = 0
    assert downstream_filter_regions(source, child, 0) == []
    plan = default_rx_plan()
    plan.datapath.cddc_enabled[0] = False
    assert (
        rx_filter_overlays(plan, compute_rx(plan), ("adc0", "cddc0", "fddc0"))
        == {}
    )
