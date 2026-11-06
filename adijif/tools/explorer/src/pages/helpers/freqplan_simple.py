"""Controls and diagrams for converters without MxFE coarse/fine stages."""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from adijif.freqplan import (
    Signal,
    compute_rx,
    compute_tx,
    evaluate_output,
    get_adapter,
)

from .freqplan_charts import signal_colors, stage_chart
from .freqplan_frames import verdict_line


def simple_updates(plan: Any, direction: str) -> dict:
    """Seed a simple editor without sharing mutable datapath lists."""
    return {
        f"fp_{direction}_simple": copy.deepcopy(plan),
        f"fp_{direction}_frames": {},
    }


def simple_diagram(plan: Any, direction: str) -> alt.LayerChart:
    """Draw real converter/filter/LO blocks instead of coarse/fine placeholders."""
    adapter = get_adapter(plan.part)
    dp = plan.datapath
    transceiver = adapter.topology == "transceiver"
    if direction == "rx":
        labels = (
            ["RF input", "LO mixer", "ADC", f"Filter ÷{dp.factor}", "JESD204"]
            if transceiver
            else ["RF input", "ADC", f"DDC ÷{dp.factor}", "JESD204"]
        )
    else:
        labels = (
            ["JESD204", f"Filter ×{dp.factor}", "DAC", "LO mixer", "RF output"]
            if transceiver
            else ["JESD204", f"Interpolator ×{dp.factor}", "DAC", "RF output"]
        )
    blocks = []
    wires = []
    for channel, enabled in enumerate(dp.enabled):
        for index, label in enumerate(labels):
            x = index * 170
            if index == 0:
                label = f"{label} · ch{channel}"
            blocks.append(
                {
                    "x": x,
                    "x2": x + 140,
                    "y": channel * 80,
                    "y2": channel * 80 + 44,
                    "cx": x + 70,
                    "cy": channel * 80 + 22,
                    "label": label,
                    "channel": channel,
                    "enabled": enabled,
                    "color": "#334155" if enabled else "#64748b",
                }
            )
            if index:
                wires.append({"x": x - 30, "x2": x, "y": channel * 80 + 22})
    rects = (
        alt.Chart(alt.Data(values=blocks))
        .mark_rect(cornerRadius=4)
        .encode(
            x=alt.X("x:Q", axis=None),
            x2="x2:Q",
            y=alt.Y("y:Q", axis=None, scale=alt.Scale(reverse=True)),
            y2="y2:Q",
            color=alt.Color("color:N", scale=None),
            opacity=alt.condition(
                alt.datum.enabled, alt.value(1), alt.value(0.5)
            ),
            tooltip=["label:N", "channel:Q", "enabled:N"],
        )
    )
    labels_chart = (
        alt.Chart(alt.Data(values=blocks))
        .mark_text(color="white", fontSize=12)
        .encode(
            x=alt.X("cx:Q", axis=None),
            y=alt.Y("cy:Q", axis=None),
            text="label:N",
        )
    )
    lines = (
        alt.Chart(alt.Data(values=wires))
        .mark_rule(color="#64748b", strokeWidth=2)
        .encode(x="x:Q", x2="x2:Q", y="y:Q")
    )
    return (
        alt.layer(rects, labels_chart, lines)
        .properties(height=max(100, len(dp.enabled) * 70), width="container")
        .configure_view(stroke=None)
    )


def _rf_chart(stage: Any, colors: dict) -> alt.Chart:
    rows = [
        {
            "lo": s.lo / 1e6,
            "hi": s.hi / 1e6,
            "signal": s.signal,
            "color": colors[s.signal],
        }
        for s in stage.spans
        if not s.image
    ]
    return (
        alt.Chart(alt.Data(values=rows))
        .mark_bar(size=32)
        .encode(
            x=alt.X(
                "lo:Q", title="RF frequency (MHz)", scale=alt.Scale(zero=False)
            ),
            x2="hi:Q",
            y=alt.Y("signal:N", title=None),
            color=alt.Color("color:N", scale=None),
            tooltip=["signal:N", "lo:Q", "hi:Q"],
        )
        .properties(height=220)
    )


def render_simple(direction: str, part: str, alpha: float) -> tuple[Any, Any]:
    """Return the edited plan/result, or (None, None) for invalid inputs."""
    ss = st.session_state
    gen = ss.get("fp_editor_gen", 0)
    plan = copy.deepcopy(ss[f"fp_{direction}_simple"])
    plan.alpha = alpha
    adapter = get_adapter(part)
    dp = plan.datapath
    prefix = f"fp_{direction}_simple_{gen}"
    rate_attr = "adc_rate_hz" if direction == "rx" else "dac_rate_hz"
    factors = list(getattr(adapter, f"{direction}_factors"))
    top = st.container()
    with st.expander("All settings", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            rate = st.number_input(
                "ADC rate (MHz)" if direction == "rx" else "DAC rate (MHz)",
                min_value=0.000001,
                value=float(getattr(plan, rate_attr) / 1e6),
                key=prefix + "_rate",
            )
        with c2:
            factor = st.selectbox(
                "Decimation" if direction == "rx" else "Interpolation",
                factors,
                index=factors.index(dp.factor),
                key=prefix + "_factor",
            )
        setattr(plan, rate_attr, rate * 1e6)
        dp.factor = factor
        if adapter.topology == "transceiver":
            dp.lo_hz = (
                st.number_input(
                    "Analog LO (MHz)",
                    min_value=0.0,
                    value=float(dp.lo_hz / 1e6),
                    key=prefix + "_lo",
                )
                * 1e6
            )
        st.markdown("**Channels**")
        channels = pd.DataFrame(
            {"channel": range(len(dp.enabled)), "enabled": dp.enabled}
        )
        if dp.nco_hz:
            channels["nco_mhz"] = [v / 1e6 for v in dp.nco_hz]
        channels = st.data_editor(
            channels,
            key=prefix + "_channels",
            hide_index=True,
            disabled=["channel"],
            column_config={
                "enabled": st.column_config.CheckboxColumn("On"),
                "nco_mhz": st.column_config.NumberColumn(
                    "NCO (MHz)", required=True
                ),
            },
        )
        dp.enabled = [bool(v) for v in channels.enabled]
        if dp.nco_hz:
            try:
                dp.nco_hz = [float(v) * 1e6 for v in channels.nco_mhz]
            except (ValueError, TypeError):
                with top:
                    st.error(
                        "Each enabled NCO needs a numeric frequency in MHz."
                    )
                return None, None
        st.markdown("**Signals**")
        signals = pd.DataFrame(
            [
                {
                    "name": s.name,
                    "center_mhz": s.center_hz / 1e6,
                    "bw_mhz": s.bandwidth_hz / 1e6,
                    "channel": s.source,
                }
                for s in plan.signals
            ],
            columns=["name", "center_mhz", "bw_mhz", "channel"],
        )
        signals = st.data_editor(
            signals,
            key=prefix + "_signals",
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "name": st.column_config.TextColumn("Name", required=True),
                "center_mhz": st.column_config.NumberColumn(
                    "RF center (MHz)"
                    if direction == "rx"
                    else "Baseband center (MHz)",
                    required=True,
                ),
                "bw_mhz": st.column_config.NumberColumn(
                    "Bandwidth (MHz)", min_value=0.0, required=True
                ),
                "channel": st.column_config.SelectboxColumn(
                    "Channel",
                    options=list(range(len(dp.enabled))),
                    required=True,
                ),
            },
        )
    try:
        plan.signals = [
            Signal(
                str(row.name),
                float(row.center_mhz) * 1e6,
                float(row.bw_mhz) * 1e6,
                int(row.channel),
            )
            for row in signals.itertuples(index=False)
        ]
        if direction == "rx":
            plan.targets = {
                f"ddc{i}": [s.name for s in plan.signals if s.source == i]
                for i, enabled in enumerate(dp.enabled)
                if enabled
            }
        result = compute_rx(plan) if direction == "rx" else compute_tx(plan)
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        ZeroDivisionError,
    ) as exc:
        with top:
            st.error(
                f"Invalid {direction.upper()} plan: {exc}; fix it under All settings."
            )
        return None, None
    ss[f"fp_{direction}_simple_live"] = copy.deepcopy(plan)
    with top:
        st.altair_chart(simple_diagram(plan, direction), width="stretch")
        if dp.profile_constraints:
            st.caption(
                "Imported profile constraints are retained for automatic planning."
            )
        for warning in result.warnings:
            st.warning(warning)
        colors = signal_colors([s.name for s in plan.signals])
        stages = list(result.stages.items())
        for first in range(0, len(stages), 3):
            cols = st.columns(min(3, len(stages) - first), border=True)
            for col, (name, stage) in zip(
                cols, stages[first : first + 3], strict=False
            ):
                with col:
                    st.markdown(f"**{name.upper()}**")
                    st.caption(f"{stage.rate_hz / 1e6:.6g} MSPS")
                    display = (
                        replace(stage, kind="input")
                        if adapter.topology == "transceiver"
                        and stage.kind == "adc"
                        else stage
                    )
                    if (
                        adapter.topology == "adc"
                        and dp.factor == 1
                        and stage.is_output
                    ):
                        display = replace(stage, kind="adc")
                    chart = (
                        _rf_chart(stage, colors)
                        if stage.kind == "rf" or name.startswith("rf")
                        else stage_chart(display, colors, True, True)
                    )
                    st.altair_chart(chart, width="stretch")
                    if direction == "rx" and stage.is_output:
                        checked = stage
                        if adapter.topology == "adc" and dp.factor == 1:
                            # The conjugate of a real ADC output is expected,
                            # not a separate unwanted complex channel.
                            checked = replace(
                                stage,
                                spans=[s for s in stage.spans if not s.image],
                            )
                        st.markdown(
                            verdict_line(
                                evaluate_output(
                                    checked,
                                    {s.name: s for s in plan.signals},
                                    plan.targets.get(name, []),
                                )
                            )
                        )
    return plan, result
