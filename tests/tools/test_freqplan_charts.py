"""Tests for frequency planner Altair chart helpers."""

from adijif.freqplan import (
    Span,
    StageOutput,
    compute_rx,
    compute_tx,
    default_rx_plan,
    default_tx_plan,
)
from adijif.tools.explorer.src.pages.helpers.freqplan_charts import (
    signal_colors,
    spans_to_rows,
    stage_chart,
    stage_overlay_chart,
)


def test_signal_colors_stable():
    """Colours are assigned in palette order."""
    assert signal_colors(["A", "B"]) == {"A": "#3b82f6", "B": "#f59e0b"}


def test_signal_colors_cycle():
    """Colours cycle after eight names."""
    names = [str(i) for i in range(9)]
    colors = signal_colors(names)
    assert colors["8"] == colors["0"]


def test_spans_to_rows():
    """Image spans convert to MHz rows with reduced height."""
    colors = {"S1": "#3b82f6"}
    rows = spans_to_rows([Span(1.0e9, 1.4e9, "S1", image=True)], colors)
    assert rows[0]["lo_mhz"] == 1000.0
    assert rows[0]["hi_mhz"] == 1400.0
    assert rows[0]["height"] == 0.6
    assert rows[0]["color"] == "#3b82f6"


def test_stage_chart_serializes():
    """Every Rx and Tx stage chart serializes to a layered spec."""
    result = compute_rx(default_rx_plan())
    colors = signal_colors(["S1"])
    for stage in result.stages.values():
        chart = stage_chart(stage, colors, True, True)
        assert "layer" in chart.to_dict()
    tx = compute_tx(default_tx_plan())
    for stage in tx.stages.values():
        assert "layer" in stage_chart(stage, colors, True, True).to_dict()


def test_stage_chart_error_stage():
    """An errored stage renders a text layer."""
    stage = StageOutput("x", "cddc", 0.0, 0.0, [], None, False, "boom")
    spec = stage_chart(stage, {}, True, True).to_dict()
    assert "layer" in spec


def _domains(spec) -> list:
    """Collect every x scale domain in a chart spec."""
    out = []

    def walk(node) -> None:
        if isinstance(node, dict):
            if "domain" in node and isinstance(node["domain"], list):
                out.append(node["domain"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(spec)
    return out


def test_dac_chart_spans_zero_to_fs():
    """DAC rows show [0, fs]; ADC rows stay on [0, fs/2]."""
    tx = compute_tx(default_tx_plan())
    dac_spec = stage_chart(tx.stages["dac0"], {}, True, True).to_dict()
    assert [0.0, 20000.0] in _domains(dac_spec)
    rx = compute_rx(default_rx_plan())
    adc_spec = stage_chart(rx.stages["adc0"], {}, True, True).to_dict()
    assert [0.0, 10000.0] in _domains(adc_spec)
    assert [0.0, 20000.0] not in _domains(adc_spec)


def test_dac_chart_draws_fs2_mirror():
    """The fs/2 mirror reaches the DAC chart data."""
    tx = compute_tx(default_tx_plan())
    spec = stage_chart(tx.stages["dac0"], {}, True, True).to_dict()
    text = str(spec)
    assert "16800" in text


def test_stage_chart_tall_with_signal_labels() -> None:
    """Spectrum charts are tall enough to read and name each signal."""
    from adijif.freqplan import compute_rx, default_rx_plan

    plan = default_rx_plan()
    stage = compute_rx(plan).stages["fddc0"]
    d = stage_chart(stage, signal_colors(["S1"]), True, True).to_dict()
    assert d["height"] >= 200
    texts = [
        layer
        for layer in d["layer"]
        if (layer.get("mark", {}) or {}).get("type") == "text"
        or layer.get("mark") == "text"
    ]
    assert texts, "expected a text layer naming the signals"


def _chart_rows(spec) -> list[dict]:
    """Collect inline Vega data rows from layered chart specifications."""
    rows = list(spec.get("data", {}).get("values", []))
    for layer in spec.get("layer", []):
        rows.extend(_chart_rows(layer))
    return rows


def test_overlay_keeps_channel_identity_and_native_frequency_limits():
    """Different output rates share an axis without extending narrower bands."""
    stages = [
        StageOutput(
            "fddc0",
            "fddc",
            100e6,
            40e6,
            [Span(-80e6, 80e6, "wide")],
            "cddc0",
            True,
        ),
        StageOutput(
            "fddc2",
            "fddc",
            200e6,
            80e6,
            [Span(60e6, 90e6, "narrow")],
            "cddc1",
            True,
        ),
    ]
    spec = stage_overlay_chart(stages, True, True).to_dict()
    assert [-100.0, 100.0] in _domains(spec)
    rows = _chart_rows(spec)
    bands = [r for r in rows if r.get("signal") == "wide"]
    assert bands
    assert all(r["lo_mhz"] == -50 and r["hi_mhz"] == 50 for r in bands)
    assert {r["stage"] for r in rows if "signal" in r} == {"FDDC0", "FDDC2"}
    assert any(p.get("bind") == "legend" for p in spec["params"])


def test_overlay_handles_empty_channels_tones_images_and_errors():
    """Empty/error channels and zero-width tones cannot erase other spectra."""
    stages = [
        StageOutput(
            "adc0",
            "adc",
            100e6,
            50e6,
            [
                Span(10e6, 10e6, "tone"),
                Span(-30e6, -20e6, "mirror", image=True),
            ],
            None,
            False,
        ),
        StageOutput("adc1", "adc", 100e6, 50e6, [], None, False),
        StageOutput("adc2", "adc", 0, 0, [], None, False, "invalid"),
    ]
    spec = stage_overlay_chart(stages, False, False).to_dict()
    assert [0.0, 50.0] in _domains(spec)
    rows = _chart_rows(spec)
    assert any(r.get("signal") == "tone" for r in rows)
    assert not any(r.get("signal") == "mirror" for r in rows)
    assert {r["stage"] for r in rows} == {"ADC0", "ADC1"}


def test_overlay_guides_follow_each_channels_passband():
    """Unequal channel passbands remain distinct and the toggles remove them."""
    result = compute_rx(default_rx_plan())
    stages = [s for s in result.stages.values() if s.kind == "fddc"]
    shown = _chart_rows(stage_overlay_chart(stages, True, True).to_dict())
    hidden = _chart_rows(stage_overlay_chart(stages, False, False).to_dict())
    edges = {
        (r["stage"], r["lo_mhz"])
        for r in shown
        if r.get("guide") == "Passband edge"
    }
    assert edges == {
        (s.channel.upper(), sign * s.passband_hz / 1e6)
        for s in stages
        for sign in (-1, 1)
    }
    assert any(r.get("guide") == "Guard band" for r in shown)
    assert not any("guide" in r for r in hidden)


def test_composite_regions_use_one_color_and_keep_adc_legend_selection():
    from adijif.tools.explorer.src.pages.helpers.freqplan_filters import (
        rx_capture_regions,
    )

    plan = default_rx_plan()
    plan.signals = []
    result = compute_rx(plan)
    adcs = [s for s in result.stages.values() if s.kind == "adc"]
    spec = stage_overlay_chart(
        adcs, True, True, rx_capture_regions(plan, result)
    ).to_dict()
    layers = [
        layer
        for layer in spec["layer"]
        if any("region" in row for row in _chart_rows(layer))
    ]
    assert len(layers) == 3
    assert len({layer["encoding"]["color"]["value"] for layer in layers}) == 1
    assert spec["layer"][0]["encoding"]["color"]["field"] == "stage"
    for layer in layers:
        assert layer["encoding"]["stroke"] == layer["encoding"]["color"]
        assert layer["transform"] == [{"filter": {"param": "adc_channels"}}]
    assert {r["region"] for r in _chart_rows(spec) if "region" in r} == {
        "Captured",
        "Transition",
        "Blocked",
    }
