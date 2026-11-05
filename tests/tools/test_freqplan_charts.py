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
