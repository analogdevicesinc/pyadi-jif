"""Downstream filter masks must agree with the frequency planner's DSP model."""

import pytest

from adijif.freqplan import (
    Span,
    StageOutput,
    compute_rx,
    ddc_stage,
    default_rx_plan,
)
from adijif.tools.explorer.src.pages.helpers.freqplan_filters import (
    downstream_filter_regions,
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
