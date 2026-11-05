"""Altair spectrum chart builders for the frequency planner."""

from __future__ import annotations

import altair as alt

from adijif.freqplan import Span, StageOutput

PALETTE = [
    "#3b82f6",
    "#f59e0b",
    "#10b981",
    "#ef4444",
    "#8b5cf6",
    "#ec4899",
    "#14b8a6",
    "#84cc16",
]
CHART_HEIGHT = 90
_REAL_KINDS = ("adc", "dac")
_OPACITY_PRIMARY = 0.85
_OPACITY_IMAGE = 0.45
_OPACITY_ATTENUATED = 0.2


def signal_colors(names: list[str]) -> dict[str, str]:
    """Assign palette colours to signal names in order.

    Args:
        names: Signal names.

    Returns:
        Mapping of name to hex colour, cycling the palette.
    """
    return {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(names)}


def spans_to_rows(spans: list[Span], colors: dict[str, str]) -> list[dict]:
    """Convert spans to chart rows in MHz.

    Args:
        spans: Spans in Hz.
        colors: Signal name to colour mapping.

    Returns:
        One row per span with lo_mhz, hi_mhz, signal, color, image,
        attenuated and height keys.
    """
    return [
        {
            "lo_mhz": s.lo / 1e6,
            "hi_mhz": s.hi / 1e6,
            "signal": s.signal,
            "color": colors.get(s.signal, "#6b7280"),
            "image": s.image,
            "attenuated": s.attenuated,
            "height": 0.6 if s.image else 1.0,
        }
        for s in spans
    ]


def _error_chart(message: str) -> alt.LayerChart:
    """Build a placeholder chart showing an error message.

    Args:
        message: Error text.

    Returns:
        A layer chart with one text mark.
    """
    text = (
        alt.Chart(alt.Data(values=[{"x": 0, "y": 0, "msg": message}]))
        .mark_text(color="#ef4444", align="center")
        .encode(x=alt.X("x:Q", axis=None), y=alt.Y("y:Q", axis=None))
        .encode(text="msg:N")
    )
    return alt.layer(text).properties(height=CHART_HEIGHT, width="container")


def _clip_rows(rows: list[dict], lo: float, hi: float) -> list[dict]:
    """Clip rows to a domain, dropping those entirely outside it.

    Args:
        rows: Chart rows.
        lo: Domain lower bound in MHz.
        hi: Domain upper bound in MHz.

    Returns:
        Clipped copies of the rows that overlap the domain.
    """
    out = []
    for r in rows:
        if r["hi_mhz"] < lo or r["lo_mhz"] > hi:
            continue
        out.append(
            {
                **r,
                "lo_mhz": max(r["lo_mhz"], lo),
                "hi_mhz": min(r["hi_mhz"], hi),
            }
        )
    return out


def stage_chart(
    stage: StageOutput,
    colors: dict[str, str],
    show_passband: bool,
    show_alias: bool,
) -> alt.LayerChart:
    """Build a compact spectrum chart for one stage.

    Args:
        stage: Stage output to draw.
        colors: Signal name to colour mapping.
        show_passband: Draw dashed passband bracket.
        show_alias: Shade the guard regions outside the passband.

    Returns:
        A layered Altair chart.
    """
    if stage.error:
        return _error_chart(stage.error)

    half = stage.rate_hz / 2e6
    real = stage.kind in _REAL_KINDS
    dom_lo = 0.0 if real else -half
    scale = alt.Scale(domain=[dom_lo, half], nice=False)
    pb = stage.passband_hz / 1e6
    ax = alt.Axis(title="MHz")
    x = alt.X("lo_mhz:Q", scale=scale, axis=ax)
    x2 = alt.X2("hi_mhz:Q")
    y = alt.Y("y0:Q", axis=None, scale=alt.Scale(domain=[0, 1.1]))
    y2 = alt.Y2("height:Q")

    rows = _clip_rows(spans_to_rows(stage.spans, colors), dom_lo, half)
    for r in rows:
        r["y0"] = 0
    wide = [r for r in rows if r["hi_mhz"] > r["lo_mhz"]]
    ticks = [r for r in rows if r["hi_mhz"] == r["lo_mhz"]]
    color = alt.Color("color:N", scale=None)
    tip = ["signal:N", "lo_mhz:Q", "hi_mhz:Q"]

    layers: list[alt.Chart] = []
    if show_alias and not real and pb < half:
        guards = [
            {"lo_mhz": pb, "hi_mhz": half, "y0": 0, "height": 1.1},
            {"lo_mhz": -half, "hi_mhz": -pb, "y0": 0, "height": 1.1},
        ]
        layers.append(
            alt.Chart(alt.Data(values=guards))
            .mark_rect(color="#9ca3af", opacity=0.15)
            .encode(x=x, x2=x2, y=y, y2=y2)
        )

    def rects(sel: list[dict], opacity: float, dash: bool) -> None:
        if not sel:
            return
        mark = alt.Chart(alt.Data(values=sel)).mark_rect(
            opacity=opacity,
            stroke=None,
            **({"strokeDash": [4, 3], "strokeWidth": 1.5} if dash else {}),
        )
        enc = mark.encode(x=x, x2=x2, y=y, y2=y2, color=color, tooltip=tip)
        if dash:
            enc = enc.encode(stroke=alt.Stroke("color:N", scale=None))
        layers.append(enc)

    rects(
        [r for r in wide if not r["image"] and not r["attenuated"]],
        _OPACITY_PRIMARY,
        False,
    )
    rects(
        [r for r in wide if r["image"] and not r["attenuated"]],
        _OPACITY_IMAGE,
        False,
    )
    rects([r for r in wide if r["attenuated"]], _OPACITY_ATTENUATED, True)

    if ticks:
        layers.append(
            alt.Chart(alt.Data(values=ticks))
            .mark_rule(strokeWidth=2)
            .encode(
                x=x,
                y=y,
                y2=y2,
                color=color,
                opacity=alt.condition(
                    alt.datum.image,
                    alt.value(_OPACITY_IMAGE),
                    alt.value(1.0),
                ),
                tooltip=tip,
            )
        )

    if show_passband:
        edges = [pb] if real else [-pb, pb]
        edges = [e for e in edges if dom_lo <= e < half]
        if edges:
            layers.append(
                alt.Chart(alt.Data(values=[{"e": e} for e in edges]))
                .mark_rule(strokeDash=[5, 4], color="#374151")
                .encode(x=alt.X("e:Q", scale=scale, axis=ax))
            )

    if not layers:
        # Empty spectrum: keep the axis visible with an invisible rule.
        layers.append(
            alt.Chart(alt.Data(values=[{"e": dom_lo}]))
            .mark_rule(opacity=0)
            .encode(x=alt.X("e:Q", scale=scale, axis=ax))
        )
    return alt.layer(*layers).properties(height=CHART_HEIGHT, width="container")
