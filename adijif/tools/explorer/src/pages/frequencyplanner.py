"""Frequency Planner page: datapath diagram, block settings and paths."""

from __future__ import annotations

import dataclasses
import zlib
from collections.abc import Callable
from typing import Any, Optional

import pandas as pd
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
from .helpers.freqplan_diagram import (
    ROUTING_LABELS,
    clicked_block,
    diagram_chart,
    rx_layout,
    tx_layout,
)
from .helpers.freqplan_frames import (
    SIGNAL_COLUMNS,
    apply_editor_delta,
    fmt_num,
    merge_input_signals,
    rx_frames_from_plan,
    rx_index_problem,
    rx_plan_from_frames,
    rx_stage_info,
    set_block_field,
    stage_caption,
    tx_frames_from_plan,
    tx_index_problem,
    tx_plan_from_frames,
    tx_stage_info,
    verdict_line,
)
from .helpers.freqplan_paths import (
    Path,
    path_status,
    resolve_path_id,
    rx_paths,
    select_path_for_block,
    tx_paths,
)

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
    "fp_rx_path",
    "fp_tx_path",
)
# Source column of each tab's signals table.
_SOURCE_COL = {"rx": "adc", "tx": "fduc"}


# Errors a malformed but parseable config can raise while building state.
_LOAD_ERRORS = (ValueError, TypeError, KeyError, AttributeError)


def _rx_updates(rx: Any) -> dict[str, Any]:
    """Session-state values that seed the Rx editors from a plan.

    Args:
        rx: The Rx plan.

    Returns:
        Key to value updates for the Rx frames and rate.
    """
    return {
        "fp_rx_frames": rx_frames_from_plan(rx),
        "fp_rx_rate": float(rx.adc_rate_hz) / 1e6,
    }


def _tx_updates(tx: Any) -> dict[str, Any]:
    """Session-state values that seed the Tx editors from a plan.

    Args:
        tx: The Tx plan.

    Returns:
        Key to value updates for the Tx frames, rate and interpolations.
    """
    fr = tx_frames_from_plan(tx)
    return {
        "fp_tx_frames": fr,
        "fp_tx_rate": float(tx.dac_rate_hz) / 1e6,
        "fp_tx_cduc_interp": fr["cduc_interp"],
        "fp_tx_fduc_interp": fr["fduc_interp"],
    }


def _view_updates(view: Any) -> tuple[dict[str, Any], list[str]]:
    """Session-state values for the overlay toggles and selected paths.

    Legacy ``hidden_kinds``/``hidden_channels`` entries are ignored. The
    path id is validated against the plan at render time, so a stale id
    is not an error here.

    Args:
        view: View dict with optional ``rx``/``tx`` sub-dicts.

    Returns:
        Tuple of (key to value updates, keys to remove).

    Raises:
        ValueError: If the view or a tab entry is not a dict, or a path
            is neither a string nor null.
    """
    if not isinstance(view, dict):
        raise ValueError("view must be an object")
    updates: dict[str, Any] = {}
    drop: list[str] = []
    for tab in ("rx", "tx"):
        v = view.get(tab) or {}
        if not isinstance(v, dict):
            raise ValueError(f"view.{tab} must be an object")
        updates[f"fp_{tab}_passband"] = bool(v.get("show_passband", True))
        updates[f"fp_{tab}_alias"] = bool(v.get("show_alias", True))
        path = v.get("path")
        if path is not None and not isinstance(path, str):
            raise ValueError(f"view.{tab}.path must be a string or null")
        updates[f"fp_{tab}_path"] = path
        # The selected block falls back to the new path's output.
        drop.append(f"fp_{tab}_block")
    return updates, drop


def _apply(updates: dict[str, Any], drop: list[str] | None = None) -> None:
    """Write session-state updates and remove keys.

    Args:
        updates: Key to value updates.
        drop: Keys to remove.
    """
    for k, v in updates.items():
        _SS[k] = v
    for k in drop or []:
        _SS.pop(k, None)


def _seed_view(view: dict) -> None:
    """Apply a view dict to the overlay toggles and selected paths.

    Args:
        view: View dict with optional ``rx``/``tx`` sub-dicts.
    """
    _apply(*_view_updates(view))


def _bump_gen() -> None:
    """Advance the editor generation so every editor resets.

    The live editor tables are dropped too, so a reset or load is not
    overridden by edits made before it.
    """
    _SS["fp_editor_gen"] = int(_SS.get("fp_editor_gen", 0)) + 1
    _SS.pop("fp_rx_live", None)
    _SS.pop("fp_tx_live", None)


def _restore_live() -> None:
    """Promote the last edited tables after returning from another page.

    Streamlit drops the state of widgets that were not rendered, so on
    return from another page the editors would show their last seed. The
    tables each editor returned on the last run are kept in
    ``fp_rx_live``/``fp_tx_live``; promote them to the editor sources and
    start a new generation. A return is detected by the alpha slider's
    key being gone (call this before saved widget values are restored).
    Normal reruns leave the sources alone so editing does not lag.
    """
    if "fp_alpha" in _SS:
        return
    if _commit_live():
        _bump_gen()


def _commit_live() -> bool:
    """Copy the last run's editor tables into the editor sources.

    Both tabs are committed, because the generation bump that follows a
    commit resets every editor on both tabs.

    Returns:
        True if any table was copied.
    """
    promoted = False
    for tab in ("rx", "tx"):
        live = _SS.get(f"fp_{tab}_live")
        if live:
            frames = dict(_SS[f"fp_{tab}_frames"])
            frames.update({k: v.copy() for k, v in live.items()})
            _SS[f"fp_{tab}_frames"] = frames
            promoted = True
    return promoted


def _block_kind(block: str) -> str:
    """Kind prefix of a block id.

    Args:
        block: Block id such as ``cddc2`` or ``mux``.

    Returns:
        The id without its trailing index.
    """
    return block.rstrip("0123456789")


def _block_index(block: str) -> int:
    """Trailing index of a block id.

    Args:
        block: Block id such as ``adc1``.

    Returns:
        The index.
    """
    return int(block[len(_block_kind(block)) :])


def _panel_key(tab: str, block: str, field: str) -> str:
    """Session key prefix of a settings-panel widget.

    Args:
        tab: ``"rx"`` or ``"tx"``.
        block: Block id.
        field: Frame column (or ``"signals"``).

    Returns:
        Key unique to the block, field and editor generation.
    """
    return f"fp_{tab}_pn_{block}_{field}_{_SS.get('fp_editor_gen', 0)}"


def _on_panel(tab: str, block: str, field: str, key: str) -> None:
    """Write a settings-panel change into the source frames (callback).

    Args:
        tab: ``"rx"`` or ``"tx"``.
        block: Block id.
        field: Frame column.
        key: Widget key holding the new value.
    """
    value = _SS.get(key)
    if value is None:
        return
    _commit_live()
    frames = dict(_SS[f"fp_{tab}_frames"])
    kind = _block_kind(block)
    frames[kind] = frames[kind].copy()
    try:
        set_block_field(frames, block, field, value)
    except _PLAN_ERRORS:
        return
    _SS[f"fp_{tab}_frames"] = frames
    _bump_gen()


def _input_signals(signals: pd.DataFrame, col: str, source: int) -> Any:
    """The signals on one input, without the source column.

    Args:
        signals: Full signals frame.
        col: Source column.
        source: Input index.

    Returns:
        Frame of that input's signals with a fresh RangeIndex.
    """
    sub = signals.loc[signals[col] == source, SIGNAL_COLUMNS]
    return sub.reset_index(drop=True)


def _on_signals_edit(tab: str, source: int, key: str) -> None:
    """Merge a panel signals-editor change into the source frames.

    Args:
        tab: ``"rx"`` or ``"tx"``.
        source: Input (ADC or FDUC) index the editor shows.
        key: Editor key holding the delta.
    """
    delta = _SS.get(key) or {}
    _commit_live()
    frames = dict(_SS[f"fp_{tab}_frames"])
    col = _SOURCE_COL[tab]
    sig = frames["signals"]
    edited = apply_editor_delta(_input_signals(sig, col, source), delta)
    frames["signals"] = merge_input_signals(sig, col, source, edited)
    _SS[f"fp_{tab}_frames"] = frames
    _bump_gen()


def _reset() -> None:
    """Reseed everything from the default plans (button callback)."""
    rx = default_rx_plan()
    _apply(_rx_updates(rx))
    _apply(_tx_updates(default_tx_plan()))
    _SS["fp_part"] = rx.part
    _SS["fp_alpha"] = float(rx.alpha)
    _seed_view({})
    _SS.pop("fp_load_error", None)
    _remount_diagram("rx")
    _remount_diagram("tx")
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
    # Build and validate everything before touching session state, so a
    # failure part way through leaves the current plan intact.
    try:
        problem = _widget_range_problem(rx, tx)
        if problem:
            _SS["fp_load_error"] = problem
            return
        updates: dict[str, Any] = {}
        if rx is not None:
            updates.update(_rx_updates(rx))
        if tx is not None:
            updates.update(_tx_updates(tx))
        updates["fp_part"] = first.part
        updates["fp_alpha"] = float(first.alpha)
        view_updates, drop = _view_updates(view)
        updates.update(view_updates)
    except _LOAD_ERRORS as e:
        _SS["fp_load_error"] = f"Malformed config: {e}"
        return
    _apply(updates, drop)
    _SS.pop("fp_load_error", None)
    _remount_diagram("rx")
    _remount_diagram("tx")
    _bump_gen()


def _init_state() -> None:
    """Seed state on first visit and restore saved widget values."""
    if "fp_rx_frames" not in _SS or "fp_tx_frames" not in _SS:
        _reset()
    else:
        _restore_live()
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


def _view(tab: str) -> dict:
    """Current view settings for one tab.

    Args:
        tab: ``"rx"`` or ``"tx"``.

    Returns:
        View dict for the config.
    """
    return {
        "path": _SS.get(f"fp_{tab}_path"),
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


def _theme() -> str | None:
    """Active Streamlit theme type, if known.

    Returns:
        ``"light"``, ``"dark"`` or None.
    """
    theme = getattr(st.context, "theme", None)
    kind = getattr(theme, "type", None)
    return kind if kind in ("light", "dark") else None


def _widget_key(tab: str, block: str, field: str, value: Any) -> str:
    """Key of a panel widget showing ``value``.

    The value's fingerprint is part of the key, so a table edit that
    changes the value gives the widget a fresh state.

    Args:
        tab: ``"rx"`` or ``"tx"``.
        block: Block id.
        field: Frame column.
        value: Value the widget shows.

    Returns:
        The widget key.
    """
    tag = zlib.crc32(repr(value).encode())
    return f"{_panel_key(tab, block, field)}_{tag:08x}"


class _Panel:
    """Settings-panel widgets bound to one block's frame row."""

    def __init__(self, tab: str, block: str, row: pd.Series) -> None:
        """Bind the panel.

        Args:
            tab: ``"rx"`` or ``"tx"``.
            block: Block id.
            row: The block's row in its effective (live) frame.
        """
        self.tab = tab
        self.block = block
        self.row = row

    def _kw(self, field: str, value: Any) -> dict[str, Any]:
        """Key and callback arguments for one widget.

        Args:
            field: Frame column.
            value: Value shown.

        Returns:
            Widget keyword arguments.
        """
        key = _widget_key(self.tab, self.block, field, value)
        return {
            "key": key,
            "on_change": _on_panel,
            "args": (self.tab, self.block, field, key),
        }

    def checkbox(self, field: str, label: str) -> None:
        """Boolean field.

        Args:
            field: Frame column.
            label: Widget label.
        """
        value = bool(self.row[field])
        st.checkbox(label, value=value, **self._kw(field, value))

    def number(self, field: str, label: str, **kw: Any) -> None:
        """MHz field.

        Args:
            field: Frame column.
            label: Widget label.
            **kw: Extra ``number_input`` arguments.
        """
        value = float(self.row[field])
        st.number_input(
            label,
            value=value,
            step=10.0,
            format="%.3f",
            **kw,
            **self._kw(field, value),
        )

    def select(
        self,
        field: str,
        label: str,
        options: list[int],
        fmt: Callable[[Any], str] = str,
    ) -> None:
        """Integer choice field.

        Args:
            field: Frame column.
            label: Widget label.
            options: Allowed values.
            fmt: Option label function.
        """
        value = int(self.row[field])
        index = options.index(value) if value in options else 0
        st.selectbox(
            label,
            options,
            index=index,
            format_func=fmt,
            **self._kw(field, value),
        )

    def text(self, field: str, label: str, help: str | None = None) -> None:
        """Free-text field.

        Args:
            field: Frame column.
            label: Widget label.
            help: Tooltip.
        """
        raw = self.row[field]
        value = "" if raw is None or pd.isna(raw) else str(raw)
        st.text_input(label, value=value, help=help, **self._kw(field, value))


def _signals_panel(tab: str, block: str, signals: pd.DataFrame) -> None:
    """Editor for the signals on one input (ADC or FDUC).

    Args:
        tab: ``"rx"`` or ``"tx"``.
        block: Block id (``adcN``, ``inputN`` or ``fducN``).
        signals: Effective signals frame.
    """
    source = _block_index(block)
    sub = _input_signals(signals, _SOURCE_COL[tab], source)
    key = _panel_key(tab, block, "signals")
    where = f"ADC{source}" if tab == "rx" else f"FDUC{source}"
    st.markdown(f"**Signals on {where}**")
    st.data_editor(
        sub,
        key=key,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "name": st.column_config.TextColumn("Name", required=True),
            "center_mhz": _num_col("Center (MHz)", required=True),
            "bw_mhz": _num_col("BW (MHz)", min_value=0.0, required=True),
        },
        on_change=_on_signals_edit,
        args=(tab, source, key),
    )


def _block_title(block: str) -> str:
    """Panel heading for a block.

    Args:
        block: Block id.

    Returns:
        Readable block name.
    """
    if block in ROUTING_LABELS:
        return ROUTING_LABELS[block]
    if _block_kind(block) == "input":
        return f"ADC{_block_index(block)} input"
    return block.upper()


def _bullets(lines: list[str]) -> None:
    """Show lines as a markdown list.

    Args:
        lines: List items.
    """
    st.markdown("\n".join(f"- {line}" for line in lines) or "- none")


def _rx_routing(block: str, plan: Any, result: Any) -> None:
    """Read-only description of an Rx routing block.

    Args:
        block: ``mux``, ``xbar`` or ``jesd``.
        plan: The Rx plan.
        result: The Rx result.
    """
    dp = plan.datapath
    if block == "mux":
        st.caption("Each CDDC takes one ADC. Set it in the CDDC's panel.")
        _bullets(
            [
                f"CDDC{c} ← ADC{a}" + ("" if dp.cddc_enabled[c] else " (off)")
                for c, a in enumerate(plan.adc_to_cddc)
            ]
        )
    elif block == "xbar":
        st.caption("Each FDDC takes one CDDC. Set it in the FDDC's panel.")
        _bullets(
            [
                f"FDDC{j} ← CDDC{s - 1}"
                + ("" if dp.fddc_enabled[j] else " (off)")
                for j, s in enumerate(dp.fddc_source)
            ]
        )
    else:
        st.caption("Outputs carried over the JESD204 link.")
        _bullets(
            [
                f"{name.upper()} · {fmt_num(s.rate_hz / 1e6)} MSPS"
                for name, s in result.stages.items()
                if s.is_output and not s.error
            ]
        )


def _tx_routing(block: str, plan: Any) -> None:
    """Read-only description of a Tx routing block.

    Args:
        block: ``xbar``, ``route`` or ``rfout``.
        plan: The Tx plan.
    """
    dp = plan.datapath
    if block == "xbar":
        st.caption("Each FDUC feeds one CDUC. Set it in the FDUC's panel.")
        _bullets(
            [
                f"FDUC{i} → CDUC{s - 1}"
                + ("" if dp.fduc_enabled[i] else " (off)")
                for i, s in enumerate(dp.fduc_source)
            ]
        )
    elif block == "route":
        st.caption("Each DAC sums its CDUCs. Set them in the DAC's panel.")
        _bullets(
            [
                f"DAC{j} ← "
                + (", ".join(f"CDUC{c - 1}" for c in srcs) or "nothing")
                for j, srcs in enumerate(dp.cduc_sources)
            ]
        )
    else:
        st.caption("Each DAC drives its own RF output.")
        _bullets([f"DAC{j} → RF out {j}" for j in range(len(dp.cduc_sources))])


def _rx_panel(block: str, live: dict, plan: Any, result: Any) -> None:
    """Settings panel for one Rx block.

    Args:
        block: Block id.
        live: Effective Rx frames.
        plan: The Rx plan.
        result: The Rx result.
    """
    dp = plan.datapath
    kind = _block_kind(block)
    st.subheader(_block_title(block))
    if kind == "cddc":
        p = _Panel("rx", block, live["cddc"].loc[block])
        p.checkbox("enabled", "On")
        p.number("rf_mhz", "RF NCO (MHz)", min_value=0.0)
        p.select("decimation", "Dec", list(dp.cddc_decimations_available))
        n_adc = get_adapter(plan.part).num_adcs
        p.select("adc", "ADC", list(range(n_adc)), lambda a: f"ADC{a}")
        p.text("targets", "Targets", help="Comma-separated signal names")
    elif kind == "fddc":
        p = _Panel("rx", block, live["fddc"].loc[block])
        p.checkbox("enabled", "On")
        n_c = len(dp.cddc_enabled)
        p.select(
            "source",
            "CDDC source (1-indexed)",
            list(range(1, n_c + 1)),
            lambda c: f"{c} (CDDC{c - 1})",
        )
        p.number("nco_mhz", "NCO (MHz)")
        p.select("decimation", "Dec", list(dp.fddc_decimations_available))
        p.text("targets", "Targets", help="Comma-separated signal names")
    elif kind in ("adc", "input"):
        st.caption(f"{fmt_num(plan.adc_rate_hz / 1e6)} MSPS")
        _signals_panel("rx", block, live["signals"])
    else:
        _rx_routing(block, plan, result)


def _tx_panel(block: str, live: dict, plan: Any) -> None:
    """Settings panel for one Tx block.

    Args:
        block: Block id.
        live: Effective Tx frames.
        plan: The Tx plan.
    """
    dp = plan.datapath
    kind = _block_kind(block)
    st.subheader(_block_title(block))
    if kind == "cduc":
        p = _Panel("tx", block, live["cduc"].loc[block])
        p.checkbox("enabled", "On")
        p.number("dac_nco_mhz", "DAC NCO (MHz)")
    elif kind == "fduc":
        p = _Panel("tx", block, live["fduc"].loc[block])
        p.checkbox("enabled", "On")
        n_c = len(dp.cduc_enabled)
        p.select(
            "source",
            "CDUC source (1-indexed)",
            list(range(1, n_c + 1)),
            lambda c: f"{c} (CDUC{c - 1})",
        )
        p.number("nco_mhz", "NCO (MHz)")
        _signals_panel("tx", block, live["signals"])
    elif kind == "dac":
        p = _Panel("tx", block, live["dac"].loc[block])
        p.text(
            "cducs",
            "CDUCs (1-indexed, comma-separated)",
            help="CDUCs summed into this DAC, e.g. 1, 3",
        )
        st.caption(f"{fmt_num(plan.dac_rate_hz / 1e6)} MSPS")
    else:
        _tx_routing(block, plan)


def _lead_with(v: Any, name: str) -> Any:
    """Put a signal's own messages first in a verdict.

    Args:
        v: The verdict.
        name: Signal name.

    Returns:
        A copy of the verdict with reordered messages.
    """
    msgs = sorted(v.messages, key=lambda m: not m.startswith(f"{name}:"))
    return dataclasses.replace(v, messages=msgs)


def _path_verdict(tab: str, path: Path, plan: Any, result: Any) -> Any:
    """Verdict for a path's output.

    Args:
        tab: ``"rx"`` or ``"tx"``.
        path: The path.
        plan: The plan.
        result: The result.

    Returns:
        The verdict; on Tx the path's own signal leads.
    """
    stage = result.stages[path.output]
    sigs = {s.name: s for s in plan.signals}
    if tab == "rx":
        return evaluate_output(stage, sigs, plan.targets.get(path.output, []))
    v = evaluate_dac(stage, sigs)
    return _lead_with(v, path.signals[0]) if path.signals else v


def _diagram_key(tab: str) -> str:
    """Widget key of a tab's diagram chart.

    Streamlit keeps a chart's selection across reruns, and clicking the
    already-selected block sends no new event. The key carries a counter
    that advances after each applied click and on Reset/Load, so the
    chart remounts with an empty selection and every click is new.

    Args:
        tab: ``"rx"`` or ``"tx"``.

    Returns:
        The current diagram key.
    """
    return f"fp_{tab}_diagram_{int(_SS.get(f'fp_{tab}_diagram_n', 0))}"


def _remount_diagram(tab: str) -> None:
    """Advance a tab's diagram key so its selection starts empty.

    Args:
        tab: ``"rx"`` or ``"tx"``.
    """
    _SS[f"fp_{tab}_diagram_n"] = int(_SS.get(f"fp_{tab}_diagram_n", 0)) + 1


def _diagram_click(tab: str) -> str | None:
    """Block id selected in a tab's diagram, if any.

    Args:
        tab: ``"rx"`` or ``"tx"``.

    Returns:
        The clicked block id, or None.
    """
    return clicked_block(_SS.get(_diagram_key(tab)))


def _select_path(tab: str, paths: list[Path]) -> str:
    """Apply a diagram click, then validate the path selection.

    An applied click remounts the diagram (see ``_diagram_key``), so the
    selection does not linger and override later path choices.

    Args:
        tab: ``"rx"`` or ``"tx"``.
        paths: Available paths.

    Returns:
        The selected path id or ``"all"``, also stored in
        ``fp_{tab}_path`` (before its widget is created).
    """
    key = f"fp_{tab}_path"
    current = resolve_path_id(paths, _SS.get(key))
    click = _diagram_click(tab)
    if click:
        _remount_diagram(tab)
        _SS[f"fp_{tab}_block"] = click
        current = select_path_for_block(paths, current, click) or current
    _SS[key] = current
    return current


def _path_charts(
    tab: str, path: Path, plan: Any, result: Any, info: dict
) -> None:
    """Draw one path's stage spectra side by side, then its verdict.

    Args:
        tab: ``"rx"`` or ``"tx"``.
        path: The path.
        plan: The plan.
        result: The result.
        info: Stage id to (NCO MHz, ratio label).
    """
    colors = signal_colors([s.name for s in plan.signals])
    show_pb = bool(_SS.get(f"fp_{tab}_passband", True))
    show_alias = bool(_SS.get(f"fp_{tab}_alias", True))
    cols = st.columns(3)
    for col, sid in zip(cols, path.stages, strict=False):
        with col:
            stage = result.stages.get(sid)
            if stage is None:
                st.caption(f"{sid} · disabled, no spectrum")
                continue
            nco, ratio = info.get(sid, (None, None))
            st.caption(stage_caption(stage, nco, ratio))
            st.altair_chart(
                stage_chart(stage, colors, show_pb, show_alias),
                width="stretch",
            )
    if len(path.stages) == 2:
        with cols[2]:
            st.caption("CDDC output, no FDDC")
    st.markdown(verdict_line(_path_verdict(tab, path, plan, result)))


def _render_tab(
    tab: str,
    plan: Any,
    result: Any,
    live: dict,
    top: Any,
    paths_box: Any,
    notes: list[str],
) -> None:
    """Draw the diagram, settings panel and path view for one tab.

    Args:
        tab: ``"rx"`` or ``"tx"``.
        plan: The plan.
        result: The result computed from it.
        live: Effective frames (sources plus this run's table edits).
        top: Container for the diagram and settings panel.
        paths_box: Container for the path selector and spectra.
        notes: Extra warnings (Tx routing notes).
    """
    if tab == "rx":
        paths = rx_paths(plan, result)
        layout, info = rx_layout, rx_stage_info(plan)
    else:
        paths = tx_paths(plan, result)
        layout, info = tx_layout, tx_stage_info(plan)
    status = {p.id: path_status(p, plan, result) for p in paths}
    statuses = {p.output: status[p.id] for p in paths}
    sel = _select_path(tab, paths)
    by_id = {p.id: p for p in paths}
    path = by_id.get(sel)

    block = _SS.get(f"fp_{tab}_block")
    blocks, wires = layout(plan, result, statuses, path, block)
    ids = [b["block_id"] for b in blocks]
    if block not in ids:
        if path is not None:
            block = path.stages[-1]
        else:
            block = paths[0].output if paths else ids[0]
        blocks, wires = layout(plan, result, statuses, path, block)
    _SS[f"fp_{tab}_block"] = block

    with top:
        left, right = st.columns([2, 1])
        with left:
            colors = signal_colors([s.name for s in plan.signals])
            st.altair_chart(
                diagram_chart(blocks, wires, colors, theme=_theme()),
                on_select="rerun",
                selection_mode="block",
                key=_diagram_key(tab),
                width="stretch",
            )
            for w in [*result.warnings, *notes]:
                st.warning(w)
        with right:
            if tab == "rx":
                _rx_panel(block, live, plan, result)
            else:
                _tx_panel(block, live, plan)

    def label(pid: str) -> str:
        """Selector label for a path id."""
        if pid == "all":
            return "All outputs"
        return f"{by_id[pid].label} ({status[pid]})"

    with paths_box:
        st.segmented_control(
            "Output path",
            [p.id for p in paths] + ["all"],
            selection_mode="single",
            required=True,
            format_func=label,
            key=f"fp_{tab}_path",
        )
        t1, t2 = st.columns(2)
        with t1:
            st.toggle("Passband edges", key=f"fp_{tab}_passband")
        with t2:
            st.toggle("Guard bands", key=f"fp_{tab}_alias")
        if path is not None:
            _path_charts(tab, path, plan, result, info)
        elif tab == "tx":
            # Every DAC is an output, including ones no path reaches.
            sigs = {s.name: s for s in plan.signals}
            for name, stage in result.stages.items():
                if stage.kind == "dac":
                    v = evaluate_dac(stage, sigs)
                    st.markdown(f"**{name.upper()}** — " + verdict_line(v))
        elif not paths:
            st.info("No outputs: enable an output stage to see a path.")
        else:
            for p in paths:
                v = _path_verdict(tab, p, plan, result)
                st.markdown(f"**{p.label}** — " + verdict_line(v))


class FrequencyPlanner(Page):
    """Converter DDC/DUC frequency planner page."""

    name = "Frequency Planner"
    tagline = (
        "Place signals through the converter's DDC/DUC chains and check "
        "what each output captures."
    )
    help_text = (
        "Each tab draws the converter's datapath like the datasheet "
        "block diagram, with a verdict badge (ok, warn or error) on every "
        "output. Click a block to edit it in the panel beside the "
        "diagram; click an ADC (or an FDUC on Tx) to edit the signals on "
        "that input. Pick an output path below the diagram to see its "
        "three spectra, left to right in signal order, with its verdict "
        "underneath, or pick All outputs for every verdict at once. "
        "All settings holds the rates and full tables for bulk edits "
        "and for adding or removing signals.\n\n"
        "**Alpha** is the usable fraction of a stage's Nyquist band. A "
        "decimating (DDC) stage at output rate R passes +/- alpha*R/2; an "
        "interpolating (DUC) stage at input rate R passes +/- alpha*R/2 "
        "and rejects images beyond R - alpha*R/2. The DAC row shows its "
        "first two Nyquist zones, 0 to fs, without alpha: the real output "
        "mirrors each signal across DC and across fs/2 (images drawn "
        "faded). Mirrored energy counts toward a signal's capture; the "
        "DAC verdict checks collisions within 0 to fs/2. Energy between "
        "the passband edge and the stopband lies in the transition band "
        "and is drawn faded as attenuated. One alpha applies to both Rx "
        "and Tx.\n\n"
        "**NCO conventions.** All frequencies are in MHz. A CDDC's RF NCO "
        "is the RF frequency to centre on; it is folded into the first "
        "Nyquist zone of the ADC for you. The exported Nyquist zone makes "
        "the hardware undo even-zone inversion, so CDDC outputs are drawn "
        "in RF order. FDDC NCOs are offsets from the "
        "CDDC output centre. On Tx, signal centres are baseband offsets "
        "at the FDUC input, FDUC NCOs are applied after FDUC "
        "interpolation as offsets at the CDUC input rate, and a "
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
        top = st.container()
        paths_box = st.container()
        with st.expander("All settings", expanded=False):
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
        live = {"signals": sig.copy(), "cddc": cddc.copy(), "fddc": fddc.copy()}
        _SS["fp_rx_live"] = live
        try:
            plan = rx_plan_from_frames(part, rate, alpha, sig, cddc, fddc, fr)
            result = compute_rx(plan)
        except _PLAN_ERRORS as e:
            with top:
                st.error(f"Invalid Rx plan: {e!s}; fix it under All settings.")
            return None
        _render_tab("rx", plan, result, live, top, paths_box, [])
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
        top = st.container()
        paths_box = st.container()
        with st.expander("All settings", expanded=False):
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
        live = {
            "signals": sig.copy(),
            "cduc": cduc.copy(),
            "dac": dac.copy(),
            "fduc": fduc.copy(),
        }
        _SS["fp_tx_live"] = live
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
            with top:
                st.error(f"Invalid Tx plan: {e!s}; fix it under All settings.")
            return None
        _render_tab("tx", plan, result, live, top, paths_box, notes)
        return plan
