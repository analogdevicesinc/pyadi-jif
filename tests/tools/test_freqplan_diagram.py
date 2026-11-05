"""Tests for the frequency planner datapath block diagram."""

from types import SimpleNamespace

from adijif.freqplan import (
    Signal,
    compute_rx,
    compute_tx,
    default_rx_plan,
    default_tx_plan,
)
from adijif.tools.explorer.src.pages.helpers.freqplan_charts import (
    signal_colors,
)
from adijif.tools.explorer.src.pages.helpers.freqplan_diagram import (
    BADGE_MAX,
    _badge_text,
    clicked_block,
    diagram_chart,
    rx_layout,
    tx_layout,
)
from adijif.tools.explorer.src.pages.helpers.freqplan_paths import (
    rx_paths,
    tx_paths,
)


def _rx(plan=None, block=None):
    plan = plan or default_rx_plan()
    result = compute_rx(plan)
    path = rx_paths(plan, result)[0]
    blocks, wires = rx_layout(plan, result, {}, path, block)
    return plan, {b["block_id"]: b for b in blocks}, wires


def _right(b):
    return b["x"] + b["w"] / 2


def _left(b):
    return b["x"] - b["w"] / 2


def test_rx_layout_blocks():
    _, by_id, _ = _rx()
    ids = set(by_id)
    for kind, n in (("adc", 4), ("cddc", 4), ("fddc", 8)):
        assert {f"{kind}{i}" for i in range(n)} <= ids
    assert {"mux", "xbar", "jesd"} <= ids
    assert by_id["fddc1"]["enabled"] is False
    for bid in ("adc0", "cddc0", "fddc0"):
        assert by_id[bid]["on_path"] is True
    assert by_id["cddc1"]["on_path"] is False
    assert by_id["fddc0"]["status"] == "ok"
    assert by_id["fddc0"]["badge"] == "S1 400/400 MHz"
    xs = [by_id[b]["x"] for b in ("adc0", "cddc0", "fddc0", "jesd")]
    assert xs == sorted(xs) and len(set(xs)) == 4


def test_rx_layout_selected_and_sub():
    _, by_id, _ = _rx(block="cddc2")
    assert by_id["cddc2"]["selected"] is True
    assert by_id["cddc0"]["selected"] is False
    assert by_id["cddc0"]["sub"] == "NCO 1200 MHz · ÷4 · 5000 MSPS"
    assert by_id["input0"]["label"] == "S1"


def test_rx_layout_routing_wires():
    plan = default_rx_plan()
    plan.adc_to_cddc = [0, 0, 2, 3]
    plan.datapath.fddc_source[2] = 1
    _, by_id, wires = _rx(plan)
    adc0, mux, cddc1 = by_id["adc0"], by_id["mux"], by_id["cddc1"]
    assert any(
        w["x1"] == _right(adc0)
        and w["y1"] == adc0["y"]
        and w["x2"] == _left(mux)
        and w["y2"] == cddc1["y"]
        for w in wires
    )
    xbar, fddc2, fddc1 = by_id["xbar"], by_id["fddc2"], by_id["fddc1"]
    assert any(
        w["x1"] == _right(xbar)
        and w["x2"] == _left(fddc2)
        and w["y1"] == w["y2"] == fddc2["y"]
        for w in wires
    )
    assert not any(
        w["x2"] == _left(fddc1) and w["y2"] == fddc1["y"] for w in wires
    )


def test_rx_layout_cddc_direct_to_jesd():
    plan = default_rx_plan()
    plan.datapath.fddc_enabled[0] = False
    _, by_id, wires = _rx(plan)
    cddc0, jesd = by_id["cddc0"], by_id["jesd"]
    assert any(
        w["x1"] == _right(cddc0)
        and w["x2"] == _left(jesd)
        and w["y1"] == w["y2"] == cddc0["y"]
        for w in wires
    )
    assert cddc0["badge"] == "S1 400/400 MHz"


def test_rx_layout_error_badge():
    plan = default_rx_plan()
    plan.datapath.cddc_enabled[0] = False
    _, by_id, _ = _rx(plan)
    assert by_id["fddc0"]["status"] == "error"
    assert by_id["fddc0"]["badge"] == "error"
    assert by_id["cddc0"]["enabled"] is False


def test_tx_layout_blocks():
    plan = default_tx_plan()
    result = compute_tx(plan)
    path = next(p for p in tx_paths(plan, result) if p.id == "S1@dac0")
    blocks, wires = tx_layout(plan, result, {}, path, None)
    by_id = {b["block_id"]: b for b in blocks}
    ids = set(by_id)
    for kind, n in (("fduc", 8), ("cduc", 4), ("dac", 4)):
        assert {f"{kind}{i}" for i in range(n)} <= ids
    assert {"xbar", "route", "rfout"} <= ids
    xs = [by_id[b]["x"] for b in ("fduc0", "cduc0", "dac0", "rfout")]
    assert xs == sorted(xs) and len(set(xs)) == 4
    for bid in ("fduc0", "cduc0", "dac0"):
        assert by_id[bid]["on_path"] is True
    assert by_id["dac2"]["on_path"] is False
    assert "S1" in by_id["fduc0"]["label"]
    assert by_id["dac0"]["badge"] == "S1 400/400 MHz"
    assert wires and any(w["on_path"] for w in wires)


def test_diagram_chart_has_block_selection():
    plan = default_rx_plan()
    result = compute_rx(plan)
    path = rx_paths(plan, result)[0]
    colors = signal_colors([s.name for s in plan.signals])
    d = diagram_chart(*rx_layout(plan, result, {}, path, None), colors)
    d = d.to_dict()

    def is_block(p):
        sel = p.get("select", {})
        return (
            p.get("name") == "block"
            and sel.get("type") == "point"
            and sel.get("fields") == ["block_id"]
        )

    in_layer = any(
        is_block(p) for lyr in d["layer"] for p in lyr.get("params", [])
    )
    top = [p for p in d.get("params", []) if is_block(p)]
    rect_names = {
        lyr.get("name")
        for lyr in d["layer"]
        if (lyr.get("mark") or {}).get("type") == "rect"
    }
    lifted = any(set(p.get("views", [])) & rect_names for p in top)
    assert in_layer or lifted


def test_diagram_chart_tx_builds():
    plan = default_tx_plan()
    result = compute_tx(plan)
    colors = signal_colors([s.name for s in plan.signals])
    blocks, wires = tx_layout(plan, result, {}, None, "dac1")
    d = diagram_chart(blocks, wires, colors).to_dict()
    assert d["height"] == 330


def test_clicked_block():
    assert (
        clicked_block({"selection": {"block": [{"block_id": "cddc2"}]}})
        == "cddc2"
    )
    assert clicked_block({"selection": {}}) is None
    assert clicked_block(None) is None
    assert clicked_block({"selection": {"block": [{}]}}) is None
    ev = SimpleNamespace(
        selection=SimpleNamespace(block=[{"block_id": "fddc0"}])
    )
    assert clicked_block(ev) == "fddc0"


def test_output_wires_stay_on_their_rows():
    _, by_id, wires = _rx()
    fddc2, jesd = by_id["fddc2"], by_id["jesd"]
    assert any(
        w["x1"] == _right(fddc2)
        and w["x2"] == _left(jesd)
        and w["y1"] == w["y2"] == fddc2["y"]
        for w in wires
    )
    plan = default_tx_plan()
    blocks, wires = tx_layout(plan, compute_tx(plan), {}, None, None)
    by_id = {b["block_id"]: b for b in blocks}
    dac3, rfout = by_id["dac3"], by_id["rfout"]
    assert any(
        w["x1"] == _right(dac3)
        and w["x2"] == _left(rfout)
        and w["y1"] == w["y2"] == dac3["y"]
        for w in wires
    )


def _text_layers(d):
    return [
        lyr
        for lyr in d["layer"]
        if (lyr.get("mark") or {}).get("type") == "text"
    ]


def test_diagram_chart_text_color_theme():
    plan = default_rx_plan()
    result = compute_rx(plan)
    rows = rx_layout(plan, result, {}, None, None)
    d = diagram_chart(*rows, {}).to_dict()
    for lyr in _text_layers(d):
        assert "color" not in lyr["mark"] and "fill" not in lyr["mark"]
    d = diagram_chart(*rows, {}, theme="dark").to_dict()
    layers = _text_layers(d)
    assert len(layers) == 4
    assert all(lyr["mark"]["color"] == "#fafafa" for lyr in layers)
    d = diagram_chart(*rows, {}, theme="light").to_dict()
    assert all(lyr["mark"]["color"] == "#262730" for lyr in _text_layers(d))


def test_badge_shows_interferer_on_error():
    """A spur in FDDC0's band makes the badge name it, not S1's capture."""
    plan = default_rx_plan()
    plan.signals.append(Signal("SP", 1.25e9, 20e6, 0))
    _, by_id, _ = _rx(plan)
    assert by_id["fddc0"]["status"] == "error"
    assert by_id["fddc0"]["badge"] == "SP in band"


def test_badge_shows_tx_overlap():
    """Two signals colliding on DAC0 show as an overlap badge."""
    plan = default_tx_plan()
    plan.cduc_dac_hz[2] = 3e9
    plan.datapath.cduc_sources[0] = [1, 3]
    blocks, _ = tx_layout(plan, compute_tx(plan), {}, None, None)
    dac0 = next(b for b in blocks if b["block_id"] == "dac0")
    assert dac0["status"] == "error"
    assert dac0["badge"] == "S1/S2 overlap"


def test_badge_text_reasons():
    """Badges explain the status: interferer, then partial capture."""
    full = "S1: 400 of 400 MHz captured"
    assert _badge_text([full, "40% of output BW used"], "ok") == (
        "S1 400/400 MHz"
    )
    part = [full, "S2: 50 of 100 MHz captured", "100% of output BW used"]
    assert _badge_text(part, "warn") == "S2 50/100 MHz"
    assert _badge_text([full, "S1: tone missed"], "warn") == "S1: tone missed"
    msgs = [full, "S9 in band (5 MHz) (attenuated)", "S8 image in band (20 MHz)"]
    assert _badge_text(msgs, "error") == "S8 image in band"
    assert _badge_text(msgs[:2], "warn") == "S9 in band (att.)"
    assert _badge_text([], "ok") == "no signals"
    long = [full, "S1 and A_very_long_signal_name overlap (10 MHz)"]
    text = _badge_text(long, "error")
    assert len(text) <= BADGE_MAX and text.startswith("S1/A_very")
