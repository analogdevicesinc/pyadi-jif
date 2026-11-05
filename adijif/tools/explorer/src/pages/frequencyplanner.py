"""Frequency Planner page: per-stage DDC/DUC spectra and verdicts."""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from adijif.freqplan import (
    ADAPTERS,
    compute_rx,
    compute_tx,
    default_rx_plan,
    default_tx_plan,
    dumps,
    evaluate_dac,
    evaluate_output,
    get_adapter,
    loads,
)

from ..utils import Page
from .helpers.freqplan_charts import signal_colors, stage_chart
from .helpers.freqplan_frames import (
    rx_frames_from_plan,
    rx_index_problem,
    rx_plan_from_frames,
    rx_stage_info,
    stage_caption,
    tx_frames_from_plan,
    tx_index_problem,
    tx_plan_from_frames,
    tx_stage_info,
    verdict_line,
)

RX_KINDS = ["adc", "cddc", "fddc"]
TX_KINDS = ["fduc", "cduc", "dac"]
ALPHA_MIN = 0.5
ALPHA_MAX = 0.95
RATE_MIN_MHZ = 1.0
# Errors a bad editor value can raise while building or computing a plan.
_PLAN_ERRORS = (
    ValueError,
    TypeError,
    ZeroDivisionError,
    KeyError,
    IndexError,
)
_SS = st.session_state
# Widget keys whose values are saved so they survive page switches.
_SAVED = (
    "fp_part",
    "fp_alpha",
    "fp_rx_rate",
    "fp_tx_rate",
    "fp_tx_cduc_interp",
    "fp_tx_fduc_interp",
    "fp_rx_passband",
    "fp_rx_alias",
    "fp_tx_passband",
    "fp_tx_alias",
)


def _seed_rx(rx: Any) -> None:
    """Replace the Rx editor sources and rate from a plan.

    Args:
        rx: The Rx plan.
    """
    _SS["fp_rx_frames"] = rx_frames_from_plan(rx)
    _SS["fp_rx_rate"] = float(rx.adc_rate_hz) / 1e6


def _seed_tx(tx: Any) -> None:
    """Replace the Tx editor sources, rate and interpolations from a plan.

    Args:
        tx: The Tx plan.
    """
    fr = tx_frames_from_plan(tx)
    _SS["fp_tx_frames"] = fr
    _SS["fp_tx_rate"] = float(tx.dac_rate_hz) / 1e6
    _SS["fp_tx_cduc_interp"] = fr["cduc_interp"]
    _SS["fp_tx_fduc_interp"] = fr["fduc_interp"]


def _seed_view(view: dict) -> None:
    """Apply a view dict to the overlay toggles and pill selections.

    Args:
        view: View dict with optional ``rx``/``tx`` sub-dicts.
    """
    for tab in ("rx", "tx"):
        v = view.get(tab) or {}
        _SS[f"fp_{tab}_passband"] = bool(v.get("show_passband", True))
        _SS[f"fp_{tab}_alias"] = bool(v.get("show_alias", True))
        for name in ("kinds", "channels"):
            field = f"hidden_{name}"
            key = f"fp_{tab}_{name}"
            _SS[f"{key}_hidden"] = [str(x) for x in v.get(field) or []]
            _SS.pop(f"{key}_opts", None)
            _SS.pop(key, None)


def _bump_gen() -> None:
    """Advance the editor generation so every editor resets."""
    _SS["fp_editor_gen"] = int(_SS.get("fp_editor_gen", 0)) + 1


def _reset() -> None:
    """Reseed everything from the default plans (button callback)."""
    rx = default_rx_plan()
    _seed_rx(rx)
    _seed_tx(default_tx_plan())
    _SS["fp_part"] = rx.part
    _SS["fp_alpha"] = float(rx.alpha)
    _seed_view({})
    _SS.pop("fp_load_error", None)
    _bump_gen()


def _widget_range_problem(rx: Any, tx: Any) -> str | None:
    """Check loaded values against the page's widget bounds.

    Args:
        rx: Loaded Rx plan, or None.
        tx: Loaded Tx plan, or None.

    Returns:
        A readable problem description, or None if all values fit.
    """
    first = rx if rx is not None else tx
    alpha = float(first.alpha)
    if not ALPHA_MIN <= alpha <= ALPHA_MAX:
        return f"alpha {alpha:g} is outside {ALPHA_MIN:g} to {ALPHA_MAX:g}"
    if rx is not None and rx.adc_rate_hz / 1e6 < RATE_MIN_MHZ:
        return f"ADC rate must be at least {RATE_MIN_MHZ:g} MHz"
    if tx is not None:
        if tx.dac_rate_hz / 1e6 < RATE_MIN_MHZ:
            return f"DAC rate must be at least {RATE_MIN_MHZ:g} MHz"
    if rx is not None:
        problem = rx_index_problem(rx)
        if problem:
            return f"Rx config: {problem}"
    if tx is not None:
        problem = tx_index_problem(tx)
        if problem:
            return f"Tx config: {problem}"
    return None


def _on_upload() -> None:
    """Load an uploaded config once per file (uploader callback)."""
    apply_upload(_SS.get("fp_load"))


def apply_upload(f: Any) -> None:
    """Load an uploaded config unless this file was already processed.

    On success the editor sources, part, alpha, rates and view state are
    replaced and the editor generation is bumped. On a bad config the
    error is stored for display and the current plan is kept.

    Args:
        f: Uploaded file (``file_id`` and ``getvalue()``), or None.
    """
    if f is None:
        _SS.pop("fp_load_error", None)
        return
    if f.file_id == _SS.get("fp_loaded_file_id"):
        return
    _SS["fp_loaded_file_id"] = f.file_id
    try:
        rx, tx, view = loads(f.getvalue().decode("utf-8", errors="replace"))
    except ValueError as e:
        _SS["fp_load_error"] = str(e)
        return
    first = rx if rx is not None else tx
    if first is None:
        _SS["fp_load_error"] = "Config contains neither an rx nor a tx plan"
        return
    problem = _widget_range_problem(rx, tx)
    if problem:
        _SS["fp_load_error"] = problem
        return
    if rx is not None:
        _seed_rx(rx)
    if tx is not None:
        _seed_tx(tx)
    _SS["fp_part"] = first.part
    _SS["fp_alpha"] = float(first.alpha)
    _seed_view(view if isinstance(view, dict) else {})
    _SS.pop("fp_load_error", None)
    _bump_gen()


def _init_state() -> None:
    """Seed state on first visit and restore saved widget values."""
    if "fp_rx_frames" not in _SS or "fp_tx_frames" not in _SS:
        _reset()
    saved = _SS.get("fp_saved", {})
    for k in _SAVED:
        if k not in _SS and k in saved:
            _SS[k] = saved[k]
    defaults = {
        "fp_part": "AD9084",
        "fp_alpha": 0.8,
        "fp_rx_rate": 20000.0,
        "fp_tx_rate": 20000.0,
        "fp_tx_cduc_interp": _SS["fp_tx_frames"]["cduc_interp"],
        "fp_tx_fduc_interp": _SS["fp_tx_frames"]["fduc_interp"],
        "fp_rx_passband": True,
        "fp_rx_alias": True,
        "fp_tx_passband": True,
        "fp_tx_alias": True,
    }
    for k, v in defaults.items():
        _SS.setdefault(k, v)


def _save_state() -> None:
    """Remember widget values so they survive switching pages."""
    _SS["fp_saved"] = {k: _SS[k] for k in _SAVED if k in _SS}


def _pills(label: str, options: list[str], key: str) -> list[str]:
    """Multi-select pills that remember hidden items as options change.

    New options start selected; an option the user deselected stays
    hidden even if it disappears and comes back.

    Args:
        label: Widget label.
        options: Current options.
        key: Widget key.

    Returns:
        Selected options.
    """
    hidden = set(_SS.get(f"{key}_hidden", []))
    prev = _SS.get(f"{key}_opts")
    if key in _SS and prev is not None:
        cur = set(_SS[key] or [])
        hidden = (hidden - set(prev)) | (set(prev) - cur)
    _SS[f"{key}_hidden"] = sorted(hidden)
    _SS[f"{key}_opts"] = list(options)
    _SS[key] = [o for o in options if o not in hidden]
    sel = st.pills(label, options, selection_mode="multi", key=key)
    return list(sel or [])


def _view(tab: str) -> dict:
    """Current view toggles for one tab.

    Args:
        tab: ``"rx"`` or ``"tx"``.

    Returns:
        View dict for the config.
    """
    return {
        "hidden_kinds": list(_SS.get(f"fp_{tab}_kinds_hidden", [])),
        "hidden_channels": list(_SS.get(f"fp_{tab}_channels_hidden", [])),
        "show_passband": bool(_SS.get(f"fp_{tab}_passband", True)),
        "show_alias": bool(_SS.get(f"fp_{tab}_alias", True)),
    }


def _num_col(label: str, **kw: Any) -> Any:
    """MHz number column.

    Args:
        label: Column label.
        **kw: Extra NumberColumn arguments.

    Returns:
        Column config.
    """
    return st.column_config.NumberColumn(label, format="%.3f", **kw)


def _signal_cols(source: str, n_sources: int) -> dict:
    """Column config for a signals editor.

    Args:
        source: Source column name.
        n_sources: Number of sources (0-indexed options).

    Returns:
        Column config mapping.
    """
    return {
        "name": st.column_config.TextColumn("Name", required=True),
        "center_mhz": _num_col("Center (MHz)", required=True),
        "bw_mhz": _num_col("BW (MHz)", min_value=0.0, required=True),
        source: st.column_config.SelectboxColumn(
            source.upper(), options=list(range(n_sources)), required=True
        ),
    }


def _render_stages(
    result: Any, plan: Any, info: dict, kinds: list[str], tab: str
) -> None:
    """Render view controls, warnings and the stacked stage rows.

    Args:
        result: RxResult or TxResult.
        plan: The plan the result was computed from.
        info: Channel to (NCO MHz, ratio label).
        kinds: Stage kinds for this tab, in order.
        tab: ``"rx"`` or ``"tx"``.
    """
    sel_kinds = _pills("Stages", kinds, f"fp_{tab}_kinds")
    sel_ch = _pills("Channels", list(result.stages), f"fp_{tab}_channels")
    t1, t2 = st.columns(2)
    with t1:
        show_pb = st.toggle("Passband edges", key=f"fp_{tab}_passband")
    with t2:
        show_alias = st.toggle("Guard bands", key=f"fp_{tab}_alias")
    for w in result.warnings:
        st.warning(w)
    colors = signal_colors([s.name for s in plan.signals])
    sigs = {s.name: s for s in plan.signals}
    for ch, stage in result.stages.items():
        if stage.kind not in sel_kinds or ch not in sel_ch:
            continue
        nco, ratio = info.get(ch, (None, None))
        st.caption(stage_caption(stage, nco, ratio))
        st.altair_chart(
            stage_chart(stage, colors, show_pb, show_alias), width="stretch"
        )
        if not (stage.is_output or stage.error):
            continue
        if tab == "rx":
            v = evaluate_output(stage, sigs, plan.targets.get(ch, []))
        else:
            v = evaluate_dac(stage, sigs)
        st.markdown(verdict_line(v))


class FrequencyPlanner(Page):
    """Converter DDC/DUC frequency planner page."""

    name = "Frequency Planner"
    tagline = (
        "Place signals through the converter's DDC/DUC chains and check "
        "what each output captures."
    )
    help_text = (
        "Edit the signals and the AD9084 DDC/DUC settings on the left; "
        "the right shows the spectrum after every stage, top to bottom, "
        "with a verdict (ok, warn or error) under each output.\n\n"
        "**Alpha** is the usable fraction of each stage's output Nyquist "
        "band: a stage at rate R passes +/- alpha*R/2. Energy beyond that "
        "edge lies in the filter transition band and is drawn faded as "
        "attenuated. One alpha applies to both Rx and Tx.\n\n"
        "**NCO conventions.** All frequencies are in MHz. A CDDC's RF NCO "
        "is the RF frequency to centre on; it is folded into the first "
        "Nyquist zone of the ADC for you. FDDC NCOs are offsets from the "
        "CDDC output centre. On Tx, signal centres are baseband offsets "
        "at the FDUC input, FDUC NCOs are offsets at the CDUC input and a "
        "CDUC's DAC NCO is the output frequency at the DAC. Signal "
        "sources (ADC, FDUC) are 0-indexed; FDDC and FDUC source columns "
        "are 1-indexed CDDC/CDUC numbers, as in adijif.\n\n"
        "**Targets** are comma-separated signal names an output should "
        "capture; leave empty to use every signal that lands there.\n\n"
        "**Partial capture.** If only part of a target's bandwidth falls "
        "inside an output's passband, the verdict is a warning that "
        "states how many MHz were captured. Unwanted signals or images "
        "inside the passband make it an error; ones only in the "
        "transition band make it a warning.\n\n"
        "Use Export to save the plan and view as JSON, and Load to "
        "restore it."
    )

    def __init__(self, state: Optional[object]) -> None:
        """Initialize the frequency planner page.

        Args:
            state: Application state object
        """
        self.state = state

    def write(self) -> None:
        """Render the frequency planner page."""
        _init_state()
        self.header()

        c1, c2 = st.columns([1, 2])
        with c1:
            part = st.selectbox("Part", list(ADAPTERS), key="fp_part")
        with c2:
            alpha = st.slider(
                "Alpha (passband fraction)",
                min_value=ALPHA_MIN,
                max_value=ALPHA_MAX,
                step=0.01,
                key="fp_alpha",
            )
        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            st.file_uploader(
                "Load config",
                type="json",
                key="fp_load",
                on_change=_on_upload,
            )
        with f2:
            export_slot = st.empty()
        with f3:
            st.button("Reset to defaults", key="fp_reset", on_click=_reset)
        if _SS.get("fp_load_error"):
            st.error(_SS["fp_load_error"])

        rx_tab, tx_tab = st.tabs(["Rx", "Tx"])
        with rx_tab:
            rx = self._rx(part, alpha)
        with tx_tab:
            tx = self._tx(part, alpha)

        view = {"rx": _view("rx"), "tx": _view("tx")}
        with export_slot:
            if rx is None and tx is None:
                st.button("Export config", disabled=True, key="fp_export")
            else:
                st.download_button(
                    "Export config",
                    dumps(rx, tx, view),
                    file_name="freqplan.json",
                    mime="application/json",
                    key="fp_export",
                    on_click="ignore",
                )
        _save_state()

    def _rx(self, part: str, alpha: float) -> Any:
        """Render the Rx tab.

        Args:
            part: Part name.
            alpha: Passband fraction.

        Returns:
            The Rx plan, or None if the inputs are invalid.
        """
        adapter = get_adapter(part)
        dp = adapter.rx_datapath()
        fr = _SS["fp_rx_frames"]
        gen = _SS["fp_editor_gen"]
        left, right = st.columns([1, 2])
        with left:
            rate = st.number_input(
                "ADC rate (MHz)",
                min_value=RATE_MIN_MHZ,
                step=100.0,
                key="fp_rx_rate",
            )
            st.markdown("**Signals**")
            sig = st.data_editor(
                fr["signals"],
                key=f"fp_rx_signals_{gen}",
                num_rows="dynamic",
                hide_index=True,
                column_config=_signal_cols("adc", adapter.num_adcs),
            )
            st.markdown("**CDDC**")
            cddc = st.data_editor(
                fr["cddc"],
                key=f"fp_rx_cddc_{gen}",
                num_rows="fixed",
                column_config={
                    "enabled": st.column_config.CheckboxColumn("On"),
                    "rf_mhz": _num_col("RF NCO (MHz)", min_value=0.0),
                    "decimation": st.column_config.SelectboxColumn(
                        "Dec",
                        options=list(dp.cddc_decimations_available),
                        required=True,
                    ),
                    "adc": st.column_config.SelectboxColumn(
                        "ADC",
                        options=list(range(adapter.num_adcs)),
                        required=True,
                    ),
                    "targets": st.column_config.TextColumn("Targets"),
                },
            )
            st.markdown("**FDDC**")
            fddc = st.data_editor(
                fr["fddc"],
                key=f"fp_rx_fddc_{gen}",
                num_rows="fixed",
                column_config={
                    "enabled": st.column_config.CheckboxColumn("On"),
                    "source": st.column_config.SelectboxColumn(
                        "CDDC",
                        options=list(range(1, len(dp.cddc_enabled) + 1)),
                        required=True,
                    ),
                    "nco_mhz": _num_col("NCO (MHz)"),
                    "decimation": st.column_config.SelectboxColumn(
                        "Dec",
                        options=list(dp.fddc_decimations_available),
                        required=True,
                    ),
                    "targets": st.column_config.TextColumn("Targets"),
                },
            )
        with right:
            try:
                plan = rx_plan_from_frames(
                    part, rate, alpha, sig, cddc, fddc, fr
                )
                result = compute_rx(plan)
            except _PLAN_ERRORS as e:
                st.error(f"Invalid Rx plan: {e!s}")
                return None
            _render_stages(result, plan, rx_stage_info(plan), RX_KINDS, "rx")
        return plan

    def _tx(self, part: str, alpha: float) -> Any:
        """Render the Tx tab.

        Args:
            part: Part name.
            alpha: Passband fraction.

        Returns:
            The Tx plan, or None if the inputs are invalid.
        """
        adapter = get_adapter(part)
        dp = adapter.tx_datapath()
        fr = _SS["fp_tx_frames"]
        gen = _SS["fp_editor_gen"]
        left, right = st.columns([1, 2])
        with left:
            rate = st.number_input(
                "DAC rate (MHz)",
                min_value=RATE_MIN_MHZ,
                step=100.0,
                key="fp_tx_rate",
            )
            i1, i2 = st.columns(2)
            with i1:
                ci = st.selectbox(
                    "CDUC interpolation",
                    list(dp.cduc_interpolation_available),
                    key="fp_tx_cduc_interp",
                )
            with i2:
                fi = st.selectbox(
                    "FDUC interpolation",
                    list(dp.fduc_interpolation_available),
                    key="fp_tx_fduc_interp",
                )
            st.markdown("**Signals**")
            sig = st.data_editor(
                fr["signals"],
                key=f"fp_tx_signals_{gen}",
                num_rows="dynamic",
                hide_index=True,
                column_config=_signal_cols("fduc", len(dp.fduc_enabled)),
            )
            st.markdown("**CDUC**")
            cduc = st.data_editor(
                fr["cduc"],
                key=f"fp_tx_cduc_{gen}",
                num_rows="fixed",
                column_config={
                    "enabled": st.column_config.CheckboxColumn("On"),
                    "dac_nco_mhz": _num_col("DAC NCO (MHz)"),
                },
            )
            st.markdown("**DAC routing**")
            dac = st.data_editor(
                fr["dac"],
                key=f"fp_tx_dac_{gen}",
                num_rows="fixed",
                column_config={
                    "cducs": st.column_config.TextColumn(
                        "CDUCs (1-indexed, comma-separated)"
                    ),
                },
            )
            st.markdown("**FDUC**")
            fduc = st.data_editor(
                fr["fduc"],
                key=f"fp_tx_fduc_{gen}",
                num_rows="fixed",
                column_config={
                    "enabled": st.column_config.CheckboxColumn("On"),
                    "source": st.column_config.SelectboxColumn(
                        "CDUC",
                        options=list(range(1, len(dp.cduc_enabled) + 1)),
                        required=True,
                    ),
                    "nco_mhz": _num_col("NCO (MHz)"),
                },
            )
        with right:
            notes: list[str] = []
            try:
                plan = tx_plan_from_frames(
                    part,
                    rate,
                    alpha,
                    ci,
                    fi,
                    sig,
                    cduc,
                    fduc,
                    fr,
                    dac=dac,
                    notes=notes,
                )
                result = compute_tx(plan)
            except _PLAN_ERRORS as e:
                st.error(f"Invalid Tx plan: {e!s}")
                return None
            for n in notes:
                st.warning(n)
            _render_stages(result, plan, tx_stage_info(plan), TX_KINDS, "tx")
        return plan
