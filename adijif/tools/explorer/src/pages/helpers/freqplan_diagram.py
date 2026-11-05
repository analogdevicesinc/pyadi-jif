"""Datasheet-style datapath block diagram for the Frequency Planner.

Layout functions turn a plan and its result into block and wire rows in
an abstract coordinate space (x in 0..``X_MAX``, y growing downward).
Block ``x``/``y`` are the block centre; ``w``/``h`` its size. Signal
flow runs left to right. ``diagram_chart`` draws the rows with Altair.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

import altair as alt

from adijif.freqplan import (
    RxPlan,
    RxResult,
    StageOutput,
    TxPlan,
    TxResult,
    evaluate_dac,
    evaluate_output,
)
from adijif.freqplan.parts import get_adapter

from .freqplan_frames import fmt_num, rx_stage_info, tx_stage_info
from .freqplan_paths import Path

# Abstract coordinate space and geometry.
X_MAX = 1000.0
ROW_H = 40.0
Y_PAD = 12.0
BLOCK_FILL = 0.82  # Fraction of its row span a block's height uses.
CHART_HEIGHT = 330

# Columns: block kind -> (centre x, width).
RX_COLUMNS: dict[str, tuple[float, float]] = {
    "input": (40.0, 64.0),
    "adc": (130.0, 70.0),
    "mux": (196.0, 18.0),
    "cddc": (330.0, 200.0),
    "xbar": (466.0, 18.0),
    "fddc": (610.0, 210.0),
    "jesd": (955.0, 30.0),
}
TX_COLUMNS: dict[str, tuple[float, float]] = {
    "fduc": (115.0, 210.0),
    "xbar": (256.0, 18.0),
    "cduc": (395.0, 200.0),
    "route": (531.0, 18.0),
    "dac": (640.0, 150.0),
    "rfout": (955.0, 30.0),
}
ROUTING_LABELS = {
    "mux": "ADC MUX",
    "xbar": "CROSSBAR",
    "route": "DAC ROUTE",
    "jesd": "JESD204",
    "rfout": "RF OUT",
}

# Colours.
STATUS_COLORS = {"ok": "#10b981", "warn": "#f59e0b", "error": "#ef4444"}
HIGHLIGHT = "#f97316"
NEUTRAL = "#94a3b8"
BLOCK_FILL_RGBA = "rgba(100, 116, 139, 0.14)"
ROUTING_FILL_RGBA = "rgba(100, 116, 139, 0.28)"
DASH_DISABLED = [4, 3]
STROKE_W = 1.2
STROKE_W_PATH = 2.0
STROKE_W_SELECTED = 3.2
WIRE_W = 1.2
WIRE_W_PATH = 2.5
DIM_OPACITY = 0.45

# Text. Theme text colours match Streamlit's light (project config)
# and default dark body text.
TEXT_COLORS = {"light": "#262730", "dark": "#fafafa"}
LABEL_SIZE = 11
SUB_SIZE = 9.5
BADGE_SIZE = 10
TEXT_PAD = 6.0
CHIP_SIZE = 8.0
CHIP_STEP = 12.0
BADGE_MAX = 24
BADGE_GAP = 10.0

_CAPTURE_RE = re.compile(r"^(.+?): ([\d.]+) of ([\d.]+) MHz captured$")


def _badge_text(messages: list[str]) -> str:
    """Compact badge text from a verdict's first message.

    Args:
        messages: Verdict messages.

    Returns:
        ``"S1 250/400 MHz"`` for capture messages, else the first
        message truncated to ``BADGE_MAX`` characters.
    """
    if not messages:
        return "no signals"
    msg = messages[0]
    m = _CAPTURE_RE.match(msg)
    if m:
        return f"{m.group(1)} {m.group(2)}/{m.group(3)} MHz"
    if len(msg) > BADGE_MAX:
        return msg[: BADGE_MAX - 1].rstrip() + "…"
    return msg


def _stage_sub(
    stage: StageOutput | None,
    enabled: bool,
    info: tuple[float | None, str | None],
) -> str:
    """Second-line text for a DSP stage block.

    Args:
        stage: Computed stage output, if any.
        enabled: True if the stage is enabled.
        info: (NCO MHz or None, ratio label or None).

    Returns:
        ``"NCO <f> MHz · <ratio> · <rate> MSPS"``, an error, or
        ``"disabled"``.
    """
    if not enabled:
        return "disabled"
    if stage is not None and stage.error:
        return stage.error
    nco, ratio = info
    parts: list[str] = []
    if nco is not None:
        parts.append(f"NCO {fmt_num(nco)} MHz")
    if ratio:
        parts.append(ratio)
    if stage is not None:
        parts.append(f"{fmt_num(stage.rate_hz / 1e6)} MSPS")
    return " · ".join(parts)


class _Grid:
    """Column/row geometry shared by the Rx and Tx layouts.

    Each column holds ``n`` equal blocks spread over ``rows`` rows, so a
    column of 4 blocks beside a column of 8 spans two rows per block.
    """

    def __init__(
        self,
        columns: dict[str, tuple[float, float]],
        rows: int,
        path: Path | None,
        block: str | None,
    ) -> None:
        """Set up the grid.

        Args:
            columns: Column name to (centre x, width).
            rows: Total row count.
            path: Highlighted path, if any.
            block: Selected block id, if any.
        """
        self.columns = columns
        self.rows = rows
        self.stages = set(path.stages) if path else set()
        self.has_path = path is not None
        self.block = block
        self.blocks: list[dict] = []
        self.full: set[str] = set()
        self.by_id: dict[str, dict] = {}
        self.wires: list[dict] = []

    def row_y(self, i: int, n: int) -> float:
        """Centre y of block ``i`` of ``n`` in a column.

        Args:
            i: Block index.
            n: Blocks in the column.

        Returns:
            The y coordinate.
        """
        span = self.rows / max(n, 1)
        return Y_PAD + (i + 0.5) * span * ROW_H

    def add(
        self,
        bid: str,
        kind: str,
        col: str,
        i: int,
        n: int,
        label: str,
        sub: str = "",
        enabled: bool = True,
        on_path: bool | None = None,
        signals: list[str] | None = None,
    ) -> dict:
        """Add a block in column ``col`` at slot ``i`` of ``n``.

        Args:
            bid: Block id.
            kind: Block kind.
            col: Column name.
            i: Slot index.
            n: Slots in the column (1 for a full-height block).
            label: First text line.
            sub: Second text line.
            enabled: False draws the block dashed and dimmed.
            on_path: Override for path membership.
            signals: Signal names to show as colour chips.

        Returns:
            The block row.
        """
        x, w = self.columns[col]
        span = self.rows / max(n, 1)
        h = span * ROW_H * (BLOCK_FILL if n > 1 else 1.0)
        row = {
            "block_id": bid,
            "kind": kind,
            "x": x,
            "y": self.row_y(i, n),
            "w": w,
            "h": h,
            "label": label,
            "sub": sub,
            "enabled": enabled,
            "on_path": bid in self.stages if on_path is None else on_path,
            "selected": bid == self.block,
            "status": "",
            "badge": "",
            "signals": list(signals or []),
        }
        self.blocks.append(row)
        if n <= 1:
            self.full.add(bid)
        self.by_id[bid] = row
        return row

    def left(self, bid: str) -> float:
        """Left edge x of a block.

        Args:
            bid: Block id.

        Returns:
            The x coordinate.
        """
        b = self.by_id[bid]
        return b["x"] - b["w"] / 2

    def right(self, bid: str) -> float:
        """Right edge x of a block.

        Args:
            bid: Block id.

        Returns:
            The x coordinate.
        """
        b = self.by_id[bid]
        return b["x"] + b["w"] / 2

    def y(self, bid: str) -> float:
        """Centre y of a block.

        Args:
            bid: Block id.

        Returns:
            The y coordinate.
        """
        return self.by_id[bid]["y"]

    def wire(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        via: tuple[str, ...],
    ) -> None:
        """Add a wire, on the path if every ``via`` stage is.

        Args:
            x1: Start x.
            y1: Start y.
            x2: End x.
            y2: End y.
            via: Stage ids the wire belongs to.
        """
        on = self.has_path and all(s in self.stages for s in via)
        self.wires.append(
            {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "on_path": on}
        )

    def route(
        self, src: str, hub: str, dst_y: float, via: tuple[str, ...]
    ) -> None:
        """Wire ``src`` into a routing block, landing at ``dst_y``.

        Draws the diagonal from the source's right edge to the hub's
        left edge at the destination row, then across the hub.

        Args:
            src: Source block id.
            hub: Routing block id.
            dst_y: Destination row y.
            via: Stage ids the wire belongs to.
        """
        self.wire(self.right(src), self.y(src), self.left(hub), dst_y, via)
        self.wire(self.left(hub), dst_y, self.right(hub), dst_y, via)

    def out(self, src: str, dst: str, via: tuple[str, ...]) -> None:
        """Horizontal wire from ``src``'s right edge to ``dst``.

        The wire runs at ``dst``'s row, or at ``src``'s row when ``dst``
        is a full-height block.

        Args:
            src: Source block id.
            dst: Destination block id.
            via: Stage ids the wire belongs to.
        """
        y = self.y(src) if dst in self.full else self.y(dst)
        self.wire(self.right(src), y, self.left(dst), y, via)

    def output(
        self,
        bid: str,
        stage: StageOutput,
        statuses: dict[str, str],
        evaluate: Callable[[StageOutput], Any],
    ) -> None:
        """Set status and badge on an output block.

        Args:
            bid: Block id.
            stage: The output stage.
            statuses: Output block id to status overrides.
            evaluate: Returns the stage's verdict.
        """
        row = self.by_id[bid]
        if stage.error:
            row["status"], row["badge"] = "error", "error"
            return
        verdict = evaluate(stage)
        row["status"] = statuses.get(bid) or verdict.status
        row["badge"] = _badge_text(verdict.messages)

    def result(self) -> tuple[list[dict], list[dict]]:
        """Return the block and wire rows.

        Returns:
            ``(blocks, wires)``.
        """
        return self.blocks, self.wires


def rx_layout(
    plan: RxPlan,
    result: RxResult,
    statuses: dict[str, str],
    path: Path | None,
    block: str | None,
) -> tuple[list[dict], list[dict]]:
    """Lay out the Rx datapath block diagram.

    Columns: signal inputs, ADCs, ADC mux, CDDCs, crossbar, FDDCs, JESD.

    Args:
        plan: The Rx plan.
        result: Computed Rx result.
        statuses: Output block id (e.g. ``"fddc0"``) to status; falls
            back to the computed verdict status.
        path: Highlighted path, if any.
        block: Selected block id, if any.

    Returns:
        ``(blocks, wires)`` rows.
    """
    dp = plan.datapath
    n_adc = get_adapter(plan.part).num_adcs
    n_c = len(dp.cddc_enabled)
    n_f = len(dp.fddc_enabled)
    g = _Grid(RX_COLUMNS, max(n_adc, n_c, n_f), path, block)
    info = rx_stage_info(plan)
    stages = result.stages
    sigs = {s.name: s for s in plan.signals}
    on = g.has_path

    for a in range(n_adc):
        names = [s.name for s in plan.signals if s.source == a]
        g.add(
            f"input{a}",
            "input",
            "input",
            a,
            n_adc,
            ", ".join(names) or "—",
            on_path=f"adc{a}" in g.stages,
            signals=names,
        )
        g.add(
            f"adc{a}",
            "adc",
            "adc",
            a,
            n_adc,
            f"ADC{a}",
            f"{fmt_num(plan.adc_rate_hz / 1e6)} MSPS",
        )
    g.add("mux", "xbar", "mux", 0, 1, ROUTING_LABELS["mux"], on_path=on)
    for c in range(n_c):
        bid = f"cddc{c}"
        en = bool(dp.cddc_enabled[c])
        sub = _stage_sub(stages.get(bid), en, info.get(bid, (None, None)))
        g.add(bid, "cddc", "cddc", c, n_c, f"CDDC{c}", sub, en)
    has_fddc = any(s.startswith("fddc") for s in g.stages)
    g.add(
        "xbar", "xbar", "xbar", 0, 1, ROUTING_LABELS["xbar"], on_path=has_fddc
    )
    for j in range(n_f):
        bid = f"fddc{j}"
        en = bool(dp.fddc_enabled[j])
        sub = _stage_sub(stages.get(bid), en, info.get(bid, (None, None)))
        g.add(bid, "fddc", "fddc", j, n_f, f"FDDC{j}", sub, en)
    g.add("jesd", "jesd", "jesd", 0, 1, ROUTING_LABELS["jesd"], on_path=on)

    for a in range(n_adc):
        g.out(f"input{a}", f"adc{a}", (f"adc{a}",))
    fed = {dp.fddc_source[j] - 1 for j in range(n_f) if dp.fddc_enabled[j]}
    for c in range(n_c):
        a = plan.adc_to_cddc[c]
        cid = f"cddc{c}"
        if not dp.cddc_enabled[c] or not 0 <= a < n_adc:
            continue
        g.route(f"adc{a}", "mux", g.y(cid), (f"adc{a}", cid))
        g.out("mux", cid, (cid,))
        if c not in fed:
            g.out(cid, "jesd", (cid,))
    for j in range(n_f):
        fid = f"fddc{j}"
        c = dp.fddc_source[j] - 1
        if not dp.fddc_enabled[j]:
            continue
        if 0 <= c < n_c and dp.cddc_enabled[c]:
            g.route(f"cddc{c}", "xbar", g.y(fid), (f"cddc{c}", fid))
        g.out("xbar", fid, (fid,))
        g.out(fid, "jesd", (fid,))

    for name, st in stages.items():
        if st.is_output and name in g.by_id:
            g.output(
                name,
                st,
                statuses,
                lambda s, n=name: evaluate_output(
                    s, sigs, plan.targets.get(n, [])
                ),
            )
    return g.result()


def tx_layout(
    plan: TxPlan,
    result: TxResult,
    statuses: dict[str, str],
    path: Path | None,
    block: str | None,
) -> tuple[list[dict], list[dict]]:
    """Lay out the Tx datapath block diagram.

    Columns: FDUCs, crossbar, CDUCs, DAC routing, DACs, RF outputs.

    Args:
        plan: The Tx plan.
        result: Computed Tx result.
        statuses: Output block id (e.g. ``"dac0"``, not the Tx path id)
            to status; falls back to the computed verdict status.
        path: Highlighted path, if any.
        block: Selected block id, if any.

    Returns:
        ``(blocks, wires)`` rows.
    """
    dp = plan.datapath
    n_dac = get_adapter(plan.part).num_dacs
    n_f = len(dp.fduc_enabled)
    n_c = len(dp.cduc_enabled)
    g = _Grid(TX_COLUMNS, max(n_dac, n_c, n_f), path, block)
    info = tx_stage_info(plan)
    stages = result.stages
    sigs = {s.name: s for s in plan.signals}
    on = g.has_path

    for i in range(n_f):
        bid = f"fduc{i}"
        en = bool(dp.fduc_enabled[i])
        names = [s.name for s in plan.signals if s.source == i]
        label = f"FDUC{i}" + (f": {', '.join(names)}" if names else "")
        sub = _stage_sub(stages.get(bid), en, info.get(bid, (None, None)))
        g.add(bid, "fduc", "fduc", i, n_f, label, sub, en, signals=names)
    g.add("xbar", "xbar", "xbar", 0, 1, ROUTING_LABELS["xbar"], on_path=on)
    for c in range(n_c):
        bid = f"cduc{c}"
        en = bool(dp.cduc_enabled[c])
        sub = _stage_sub(stages.get(bid), en, info.get(bid, (None, None)))
        g.add(bid, "cduc", "cduc", c, n_c, f"CDUC{c}", sub, en)
    g.add("route", "xbar", "route", 0, 1, ROUTING_LABELS["route"], on_path=on)
    for j in range(n_dac):
        bid = f"dac{j}"
        st = stages.get(bid)
        rate = f"{fmt_num(st.rate_hz / 1e6)} MSPS" if st else ""
        g.add(bid, "dac", "dac", j, n_dac, f"DAC{j}", rate)
    g.add("rfout", "rfout", "rfout", 0, 1, ROUTING_LABELS["rfout"], on_path=on)

    cducs_fed: set[int] = set()
    for i in range(n_f):
        c = dp.fduc_source[i] - 1
        if not dp.fduc_enabled[i] or not 0 <= c < n_c:
            continue
        cid = f"cduc{c}"
        g.route(f"fduc{i}", "xbar", g.y(cid), (f"fduc{i}", cid))
        if dp.cduc_enabled[c] and c not in cducs_fed:
            cducs_fed.add(c)
            g.out("xbar", cid, (cid,))
    for j in range(n_dac):
        did = f"dac{j}"
        srcs = dp.cduc_sources[j] if j < len(dp.cduc_sources) else []
        routed = False
        for c1 in srcs:
            c = c1 - 1
            if not 0 <= c < n_c or not dp.cduc_enabled[c]:
                continue
            g.route(f"cduc{c}", "route", g.y(did), (f"cduc{c}", did))
            routed = True
        if routed:
            g.out("route", did, (did,))
        g.out(did, "rfout", (did,))

    for j in range(n_dac):
        st = stages.get(f"dac{j}")
        if st is not None:
            g.output(f"dac{j}", st, statuses, lambda s: evaluate_dac(s, sigs))
    return g.result()


def _style(b: dict) -> dict:
    """Add drawing attributes to a block row.

    Args:
        b: Block row.

    Returns:
        A copy with stroke, fill, dash, edge and opacity keys.
    """
    routing = b["kind"] in ("xbar", "jesd", "rfout")
    if not b["enabled"]:
        stroke, fill, dash = NEUTRAL, "transparent", DASH_DISABLED
    else:
        fill = ROUTING_FILL_RGBA if routing else BLOCK_FILL_RGBA
        stroke, dash = NEUTRAL, []
    width = STROKE_W
    if b["on_path"]:
        stroke, width = HIGHLIGHT, STROKE_W_PATH
    if b["selected"]:
        stroke, width = HIGHLIGHT, STROKE_W_SELECTED
    return {
        **b,
        "x_lo": b["x"] - b["w"] / 2,
        "x_hi": b["x"] + b["w"] / 2,
        "y_lo": b["y"] - b["h"] / 2,
        "y_hi": b["y"] + b["h"] / 2,
        "stroke": stroke,
        "fill": fill,
        "dash": dash,
        "stroke_w": width,
        "text_op": 1.0 if b["enabled"] else DIM_OPACITY,
        "routing": routing,
    }


def diagram_chart(
    blocks: list[dict],
    wires: list[dict],
    colors: dict[str, str],
    theme: str | None = None,
) -> alt.LayerChart:
    """Draw a block diagram from layout rows.

    Streamlit's Vega config themes axis and legend text but not text
    marks, which default to black. Pass the active theme type (e.g.
    ``st.context.theme.type``) so labels stay legible in dark mode.

    Args:
        blocks: Block rows from ``rx_layout`` or ``tx_layout``.
        wires: Wire rows from the same call.
        colors: Signal name to colour, for the input chips.
        theme: ``"light"``, ``"dark"`` or None to leave the text colour
            to the renderer's default.

    Returns:
        A layered chart; its rect layer carries the ``block`` click
        selection on ``block_id``.
    """
    rows = [_style(b) for b in blocks]
    tc = TEXT_COLORS.get(theme or "")
    text_kw: dict[str, Any] = {"color": tc} if tc else {}
    y_max = max((r["y_hi"] for r in rows), default=ROW_H) + Y_PAD
    xs = alt.Scale(domain=[0, X_MAX], nice=False, zero=False)
    ys = alt.Scale(domain=[0, y_max], nice=False, zero=False, reverse=True)

    def xy(x: str, y: str, **kw: Any) -> dict:
        """Positional encodings with fixed hidden scales."""
        enc = {
            "x": alt.X(f"{x}:Q", scale=xs, axis=None),
            "y": alt.Y(f"{y}:Q", scale=ys, axis=None),
        }
        for k, v in kw.items():
            enc[k] = alt.X2(f"{v}:Q") if k == "x2" else alt.Y2(f"{v}:Q")
        return enc

    sorted_wires = sorted(wires, key=lambda w: w["on_path"])
    wire_rows = [
        {
            **w,
            "color": HIGHLIGHT if w["on_path"] else NEUTRAL,
            "width": WIRE_W_PATH if w["on_path"] else WIRE_W,
        }
        for w in sorted_wires
    ]
    wire_layer = (
        alt.Chart(alt.Data(values=wire_rows))
        .mark_rule(strokeCap="round")
        .encode(
            **xy("x1", "y1", x2="x2", y2="y2"),
            color=alt.Color("color:N", scale=None),
            strokeWidth=alt.StrokeWidth("width:Q", scale=None),
        )
    )

    plain = [r for r in rows if not r["routing"]]
    label_rows, sub_rows, chip_rows = [], [], []
    for r in plain:
        two = bool(r["sub"]) or bool(r["signals"])
        dy = r["h"] * 0.2 if two else 0.0
        tx = r["x_lo"] + TEXT_PAD
        label_rows.append({**r, "tx": tx, "ty": r["y"] - dy})
        if r["kind"] == "input":
            for k, name in enumerate(r["signals"]):
                cx = tx + k * CHIP_STEP
                chip_rows.append(
                    {
                        "block_id": r["block_id"],
                        "cx": cx,
                        "cx2": cx + CHIP_SIZE,
                        "cy": r["y"] + dy - CHIP_SIZE / 2,
                        "cy2": r["y"] + dy + CHIP_SIZE / 2,
                        "color": colors.get(name, NEUTRAL),
                    }
                )
        elif r["sub"]:
            sub_rows.append({**r, "tx": tx, "ty": r["y"] + dy})

    label_layer = (
        alt.Chart(alt.Data(values=label_rows))
        .mark_text(
            align="left",
            baseline="middle",
            fontSize=LABEL_SIZE,
            fontWeight="bold",
            **text_kw,
        )
        .encode(
            **xy("tx", "ty"),
            text=alt.Text("label:N"),
            opacity=alt.Opacity("text_op:Q", scale=None),
        )
    )
    sub_layer = (
        alt.Chart(alt.Data(values=sub_rows))
        .mark_text(
            align="left", baseline="middle", fontSize=SUB_SIZE, **text_kw
        )
        .encode(
            **xy("tx", "ty"),
            text=alt.Text("sub:N"),
            opacity=alt.Opacity("text_op:Q", scale=None),
        )
    )
    chip_layer = (
        alt.Chart(alt.Data(values=chip_rows))
        .mark_rect(cornerRadius=2)
        .encode(
            **xy("cx", "cy", x2="cx2", y2="cy2"),
            color=alt.Color("color:N", scale=None),
        )
    )
    routing_layer = (
        alt.Chart(alt.Data(values=[r for r in rows if r["routing"]]))
        .mark_text(
            angle=270,
            align="center",
            baseline="middle",
            fontSize=LABEL_SIZE,
            fontWeight="bold",
            **text_kw,
        )
        .encode(**xy("x", "y"), text=alt.Text("label:N"))
    )

    # One badge column, right of the rightmost output block.
    badge_x = (
        max((r["x_hi"] for r in rows if r["badge"]), default=0.0) + BADGE_GAP
    )
    badge_rows = [
        {
            "block_id": r["block_id"],
            "bx": badge_x,
            "by": r["y"],
            "badge": r["badge"],
            "color": STATUS_COLORS.get(r["status"], NEUTRAL),
        }
        for r in rows
        if r["badge"]
    ]
    dot_layer = (
        alt.Chart(alt.Data(values=badge_rows))
        .mark_circle(size=60, opacity=1)
        .encode(**xy("bx", "by"), color=alt.Color("color:N", scale=None))
    )
    badge_layer = (
        alt.Chart(alt.Data(values=badge_rows))
        .mark_text(
            align="left",
            baseline="bottom",
            dx=8,
            dy=-3,
            fontSize=BADGE_SIZE,
            **text_kw,
        )
        .encode(**xy("bx", "by"), text=alt.Text("badge:N"))
    )

    select = alt.selection_point(
        name="block", fields=["block_id"], on="click", toggle=False
    )
    rect_layer = (
        alt.Chart(alt.Data(values=rows))
        .mark_rect(cornerRadius=3, cursor="pointer")
        .encode(
            **xy("x_lo", "y_lo", x2="x_hi", y2="y_hi"),
            fill=alt.Fill("fill:N", scale=None),
            stroke=alt.Stroke("stroke:N", scale=None),
            strokeWidth=alt.StrokeWidth("stroke_w:Q", scale=None),
            strokeDash=alt.StrokeDash("dash:N", scale=None),
            tooltip=[
                alt.Tooltip("label:N", title="Block"),
                alt.Tooltip("sub:N", title="Detail"),
                alt.Tooltip("badge:N", title="Verdict"),
            ],
        )
        .add_params(select)
    )

    return (
        alt.layer(
            wire_layer,
            label_layer,
            sub_layer,
            chip_layer,
            routing_layer,
            dot_layer,
            badge_layer,
            rect_layer,
        )
        .properties(height=CHART_HEIGHT, width="container")
        .configure_view(strokeWidth=0)
    )


def _get(obj: Any, key: str) -> Any:
    """Read ``key`` from a mapping or attribute-style object.

    Args:
        obj: Mapping or object.
        key: Key or attribute name.

    Returns:
        The value, or None if absent.
    """
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        return obj.get(key)
    return getattr(obj, key, None)


def clicked_block(event: Any) -> str | None:
    """Extract the clicked block id from a Streamlit selection event.

    Args:
        event: ``on_select`` event, dict- or attribute-style.

    Returns:
        The ``block_id`` of the first selected point, or None.
    """
    points = _get(_get(event, "selection"), "block")
    if not isinstance(points, (list, tuple)) or not points:
        return None
    bid = _get(points[0], "block_id")
    return bid if isinstance(bid, str) and bid else None
