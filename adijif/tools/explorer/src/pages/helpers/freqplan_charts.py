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
_CHANNEL_PALETTE = PALETTE + [
    "#9ecae9",
    "#fdae6b",
    "#a1d99b",
    "#fc9272",
    "#bcbddc",
    "#e7ba52",
    "#9edae5",
    "#c5b0d5",
]
CHART_HEIGHT = 220
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


def _stage_domain(stage: StageOutput) -> tuple[float, float]:
    """Return a stage's displayed Nyquist interval in MHz."""
    half = stage.rate_hz / 2e6
    return (
        0.0 if stage.kind in _REAL_KINDS else -half,
        2 * half if stage.kind == "dac" else half,
    )


def _overlay_data(stage: StageOutput) -> tuple[list, list, list]:
    """Build channel-tagged spectra, guard bands and passband edges."""
    lo, hi = _stage_domain(stage)
    pb = stage.passband_hz / 1e6
    common = {
        "stage": stage.channel.upper(),
        "rate_mhz": stage.rate_hz / 1e6,
        "y0": 0,
    }
    rows = [
        {**row, **common}
        for row in _clip_rows(spans_to_rows(stage.spans, {}), lo, hi)
    ]
    real = stage.kind in _REAL_KINDS
    guards = []
    if not real and pb < hi:
        guards = [
            {
                **common,
                "lo_mhz": left,
                "hi_mhz": right,
                "height": 1.2,
                "guide": "Guard band",
            }
            for left, right in ((lo, -pb), (pb, hi))
        ]
    edges = [
        {**common, "lo_mhz": edge, "guide": "Passband edge"}
        for edge in ([pb] if real else [-pb, pb])
        if lo <= edge < hi
    ]
    return rows, guards, edges


def stage_overlay_chart(
    stages: list[StageOutput],
    show_passband: bool,
    show_alias: bool,
    capture_regions: list[dict] | None = None,
) -> alt.LayerChart:
    """Overlay one stage family, with an interactive channel legend.

    Args:
        stages: Computed channels from the same stage family.
        show_passband: Draw each channel's dashed passband edges.
        show_alias: Shade each channel's guard bands.
        capture_regions: Optional composite ADC capture regions in MHz.

    Returns:
        A shared-frequency chart; errored channels are omitted.
    """
    valid = [stage for stage in stages if not stage.error and stage.rate_hz > 0]
    if not valid:
        return _error_chart("No valid spectra")
    domains = [_stage_domain(stage) for stage in valid]
    domain = [min(d[0] for d in domains), max(d[1] for d in domains)]
    channels = [stage.channel.upper() for stage in valid]
    color_scale = alt.Scale(
        domain=channels, range=_CHANNEL_PALETTE[: len(channels)]
    )
    color = alt.Color(
        "stage:N",
        scale=color_scale,
        legend=alt.Legend(
            title="Channel",
            orient="bottom",
            columns=4,
            symbolOpacity=1,
            symbolStrokeWidth=3,
        ),
    )
    selection = alt.selection_point(
        name=f"{valid[0].kind}_channels",
        fields=["stage"],
        bind="legend",
        # Keep selection on the legend. A chart click must not replace the
        # clicked mask before the second click can clear the selection.
        on="click[false]",
        clear="dblclick",
    )
    x = alt.X(
        "lo_mhz:Q",
        scale=alt.Scale(domain=domain, nice=False),
        axis=alt.Axis(title="MHz", tickCount=5, labelOverlap=True),
    )
    y = alt.Y("y0:Q", axis=None, scale=alt.Scale(domain=[0, 1.2]))
    rows, guards, edges = [], [], []
    for stage in valid:
        bands, guard_rows, edge_rows = _overlay_data(stage)
        rows.extend(bands)
        guards.extend(guard_rows)
        edges.extend(edge_rows)

    def chart(data: list[dict]) -> alt.Chart:
        return alt.Chart(alt.Data(values=data)).transform_filter(selection)

    # Keep empty channels in the legend and retain the common axis when filtered.
    anchors = [{"stage": channel, "lo_mhz": domain[0]} for channel in channels]
    layers = [chart(anchors).mark_rule(opacity=0).encode(x=x, color=color)]
    if capture_regions:
        capture_tip = [
            alt.Tooltip("stage:N", title="ADC"),
            alt.Tooltip("region:N", title="Composite capture"),
            alt.Tooltip("lo_mhz:Q", title="Low (MHz)"),
            alt.Tooltip("hi_mhz:Q", title="High (MHz)"),
            alt.Tooltip("captured_mhz:Q", title="Total captured (MHz)"),
            alt.Tooltip("fddcs:N", title="Connected FDDCs"),
        ]
        for region, fill, stroke_width, dash in (
            ("Blocked", 0.06, 0, [1, 0]),
            ("Transition", 0.1, 1, [4, 3]),
            ("Captured", 0.08, 2, [1, 0]),
        ):
            bands = [
                {**r, "y0": 0, "height": 1.2}
                for r in capture_regions
                if r["region"] == region and r["stage"] in channels
            ]
            if bands:
                layers.append(
                    chart(bands)
                    .mark_rect(
                        fillOpacity=fill,
                        strokeWidth=stroke_width,
                        strokeDash=dash,
                    )
                    .encode(
                        x=x,
                        x2="hi_mhz:Q",
                        y=y,
                        y2="height:Q",
                        color=color,
                        stroke=alt.Stroke(
                            "stage:N", scale=color_scale, legend=None
                        ),
                        tooltip=capture_tip,
                    )
                )
    guide_tip = ["stage:N", "guide:N", "lo_mhz:Q", "rate_mhz:Q"]
    if show_alias and guards:
        layers.append(
            chart(guards)
            .mark_rect(opacity=0.06)
            .encode(
                x=x,
                x2="hi_mhz:Q",
                y=y,
                y2="height:Q",
                color=color,
                tooltip=guide_tip,
            )
        )
    tip = [
        alt.Tooltip("stage:N", title="Channel"),
        alt.Tooltip("signal:N", title="Signal"),
        alt.Tooltip("lo_mhz:Q", title="Low (MHz)"),
        alt.Tooltip("hi_mhz:Q", title="High (MHz)"),
        alt.Tooltip("rate_mhz:Q", title="Rate (MSPS)"),
        alt.Tooltip("image:N", title="Image"),
        alt.Tooltip("attenuated:N", title="Attenuated"),
    ]
    wide = [r for r in rows if r["hi_mhz"] > r["lo_mhz"]]
    ticks = [r for r in rows if r["hi_mhz"] == r["lo_mhz"]]
    opacity = alt.condition(
        alt.datum.attenuated, alt.value(0.25), alt.value(0.85)
    )
    if wide:
        layers.append(
            chart(wide)
            .mark_rect(fillOpacity=0.16, strokeWidth=1.5)
            .encode(
                x=x,
                x2="hi_mhz:Q",
                y=y,
                y2="height:Q",
                color=color,
                stroke=alt.Stroke("stage:N", scale=color_scale, legend=None),
                strokeDash=alt.condition(
                    alt.datum.attenuated, alt.value([4, 3]), alt.value([1, 0])
                ),
                opacity=opacity,
                tooltip=tip,
            )
        )
    if ticks:
        layers.append(
            chart(ticks)
            .mark_rule(strokeWidth=2)
            .encode(
                x=x,
                y=y,
                y2="height:Q",
                color=color,
                opacity=opacity,
                tooltip=tip,
            )
        )
    if show_passband and edges:
        layers.append(
            chart(edges)
            .mark_rule(strokeDash=[5, 4], opacity=0.5)
            .encode(
                x=x,
                color=color,
                tooltip=guide_tip,
            )
        )
    return (
        alt.layer(*layers)
        .add_params(selection)
        .properties(height=CHART_HEIGHT + 80, width="container")
    )


def stage_chart(
    stage: StageOutput,
    colors: dict[str, str],
    show_passband: bool,
    show_alias: bool,
    downstream_regions: list[dict] | None = None,
) -> alt.LayerChart:
    """Build a compact spectrum chart for one stage.

    Args:
        stage: Stage output to draw.
        colors: Signal name to colour mapping.
        show_passband: Draw dashed passband bracket.
        show_alias: Shade the guard regions outside the passband.
        downstream_regions: Optional next-DDC transition/rejection masks in MHz.

    Returns:
        A layered Altair chart.
    """
    if stage.error:
        return _error_chart(stage.error)

    half = stage.rate_hz / 2e6
    real = stage.kind in _REAL_KINDS
    # The DAC row also shows the second Nyquist zone, up to fs.
    dom_lo, dom_hi = _stage_domain(stage)
    scale = alt.Scale(domain=[dom_lo, dom_hi], nice=False)
    pb = stage.passband_hz / 1e6
    ax = alt.Axis(title="MHz", tickCount=5, labelOverlap=True)
    x = alt.X("lo_mhz:Q", scale=scale, axis=ax)
    x2 = alt.X2("hi_mhz:Q")
    y_scale = alt.Scale(domain=[0, 1.2])
    y = alt.Y("y0:Q", axis=None, scale=y_scale)
    y2 = alt.Y2("height:Q")

    rows = _clip_rows(spans_to_rows(stage.spans, colors), dom_lo, dom_hi)
    for r in rows:
        r["y0"] = 0
    wide = [r for r in rows if r["hi_mhz"] > r["lo_mhz"]]
    ticks = [r for r in rows if r["hi_mhz"] == r["lo_mhz"]]
    color = alt.Color("color:N", scale=None)
    tip = ["signal:N", "lo_mhz:Q", "hi_mhz:Q"]

    layers: list[alt.Chart] = []
    if show_alias and not real and pb < half:
        guards = [
            {"lo_mhz": pb, "hi_mhz": half, "y0": 0, "height": 1.2},
            {"lo_mhz": -half, "hi_mhz": -pb, "y0": 0, "height": 1.2},
        ]
        layers.append(
            alt.Chart(alt.Data(values=guards))
            .mark_rect(color="#9ca3af", opacity=0.15)
            .encode(x=x, x2=x2, y=y, y2=y2)
        )

    if downstream_regions:
        filter_colors = {"Transition": "#f59e0b", "Rejected": "#64748b"}
        regions = [
            {
                **r,
                "y0": 0,
                "height": 1.2,
                "filter_color": filter_colors[r["region"]],
            }
            for r in _clip_rows(downstream_regions, dom_lo, dom_hi)
        ]
        layers.append(
            alt.Chart(alt.Data(values=regions))
            .mark_rect(opacity=0.22, strokeWidth=1, strokeDash=[4, 3])
            .encode(
                x=x,
                x2=x2,
                y=y,
                y2=y2,
                color=alt.Color("filter_color:N", scale=None),
                stroke=alt.Stroke("filter_color:N", scale=None),
                tooltip=[
                    alt.Tooltip("filter:N", title="Downstream filter"),
                    alt.Tooltip("region:N", title="Region"),
                    alt.Tooltip("lo_mhz:Q", title="Low (MHz)"),
                    alt.Tooltip("hi_mhz:Q", title="High (MHz)"),
                ],
            )
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

    named = [r for r in wide if not r["image"] and not r["attenuated"]]
    if named:
        for r in named:
            r["mid_mhz"] = (r["lo_mhz"] + r["hi_mhz"]) / 2
            r["label_y"] = r["height"] + 0.04
        layers.append(
            alt.Chart(alt.Data(values=named))
            .mark_text(baseline="bottom", fontSize=12, fontWeight="bold")
            .encode(
                x=alt.X("mid_mhz:Q", scale=scale, axis=ax),
                y=alt.Y("label_y:Q", axis=None, scale=y_scale),
                text="signal:N",
                color=color,
            )
        )

    if show_passband:
        edges = [pb] if real else [-pb, pb]
        edges = [e for e in edges if dom_lo <= e < dom_hi]
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
