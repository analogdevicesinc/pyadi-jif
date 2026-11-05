"""Streamlit-free conversion between planner editor frames and plans.

Editor frames hold frequencies in MHz; plans hold Hz. Frame dicts also
carry datapath settings that have no editor (NCO phases, Tx CDUC-to-DAC
routing, Tx interpolations) so a loaded config survives re-export.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import pandas as pd

from adijif.freqplan import (
    RxPlan,
    Signal,
    StageOutput,
    TxPlan,
    Verdict,
    get_adapter,
    rf_to_nco,
    wrap_frequency,
)

GLYPHS = {"ok": "✓", "warn": "⚠", "error": "✗"}
SIGNAL_COLUMNS = ["name", "center_mhz", "bw_mhz"]


def _hz(mhz: float) -> float:
    """Convert MHz to Hz, rounded to the millihertz.

    Args:
        mhz: Frequency in MHz.

    Returns:
        Frequency in Hz.
    """
    return round(float(mhz) * 1e6, 3)


def _missing(v: Any) -> bool:
    """Return True for None, NaN or an empty string.

    Args:
        v: Cell value.

    Returns:
        Whether the cell is empty.
    """
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


def _num(v: Any, what: str) -> float:
    """Read a required numeric cell.

    Args:
        v: Cell value.
        what: Description used in the error message.

    Returns:
        The value as float.

    Raises:
        ValueError: If the cell is empty.
    """
    if _missing(v):
        raise ValueError(f"{what} is empty")
    return float(v)


def _targets_str(names: list[str]) -> str:
    """Join target names for a text cell.

    Args:
        names: Signal names.

    Returns:
        Comma-separated names.
    """
    return ", ".join(names)


def _parse_targets(v: Any) -> list[str]:
    """Parse a comma-separated targets cell.

    Args:
        v: Cell value.

    Returns:
        Non-empty stripped names.
    """
    if _missing(v):
        return []
    return [t.strip() for t in str(v).split(",") if t.strip()]


def _signals_frame(signals: list[Signal], source_col: str) -> pd.DataFrame:
    """Build the signals editor frame.

    Args:
        signals: Plan signals.
        source_col: Name of the source column (``adc`` or ``fduc``).

    Returns:
        Frame with name, center_mhz, bw_mhz and source columns.
    """
    return pd.DataFrame(
        {
            "name": [s.name for s in signals],
            "center_mhz": [float(s.center_hz) / 1e6 for s in signals],
            "bw_mhz": [float(s.bandwidth_hz) / 1e6 for s in signals],
            source_col: [int(s.source) for s in signals],
        },
        columns=[*SIGNAL_COLUMNS, source_col],
    )


def _signals_from_frame(df: pd.DataFrame, source_col: str) -> list[Signal]:
    """Read signals from an editor frame, skipping incomplete rows.

    Args:
        df: Signals editor frame.
        source_col: Name of the source column.

    Returns:
        Signals with frequencies in Hz.
    """
    out: list[Signal] = []
    for _, row in df.iterrows():
        vals = [row.get(c) for c in (*SIGNAL_COLUMNS, source_col)]
        if any(_missing(v) for v in vals):
            continue
        out.append(
            Signal(
                str(row["name"]).strip(),
                _hz(row["center_mhz"]),
                _hz(row["bw_mhz"]),
                int(row[source_col]),
            )
        )
    return out


def rx_frames_from_plan(plan: RxPlan) -> dict[str, Any]:
    """Build Rx editor frames from a plan.

    Args:
        plan: The Rx plan.

    Returns:
        Dict with ``signals``, ``cddc`` and ``fddc`` frames plus
        ``cddc_nco_phases`` and ``fddc_nco_phases``.
    """
    dp = plan.datapath
    n_c = len(dp.cddc_enabled)
    n_f = len(dp.fddc_enabled)
    cddc = pd.DataFrame(
        {
            "enabled": [bool(x) for x in dp.cddc_enabled],
            "rf_mhz": [float(f) / 1e6 for f in plan.cddc_rf_hz],
            "decimation": [int(x) for x in dp.cddc_decimations],
            "adc": [int(a) for a in plan.adc_to_cddc],
            "targets": [
                _targets_str(plan.targets.get(f"cddc{i}", []))
                for i in range(n_c)
            ],
        },
        index=[f"cddc{i}" for i in range(n_c)],
    )
    fddc = pd.DataFrame(
        {
            "enabled": [bool(x) for x in dp.fddc_enabled],
            "source": [int(x) for x in dp.fddc_source],
            "nco_mhz": [float(f) / 1e6 for f in dp.fddc_nco_frequencies],
            "decimation": [int(x) for x in dp.fddc_decimations],
            "targets": [
                _targets_str(plan.targets.get(f"fddc{j}", []))
                for j in range(n_f)
            ],
        },
        index=[f"fddc{j}" for j in range(n_f)],
    )
    return {
        "signals": _signals_frame(plan.signals, "adc"),
        "cddc": cddc,
        "fddc": fddc,
        "cddc_nco_phases": copy.deepcopy(list(dp.cddc_nco_phases)),
        "fddc_nco_phases": copy.deepcopy(list(dp.fddc_nco_phases)),
    }


def _check_rows(df: pd.DataFrame, n: int, what: str) -> None:
    """Raise if a fixed stage table has the wrong number of rows.

    Args:
        df: Stage frame.
        n: Expected row count.
        what: Table name for the message.

    Raises:
        ValueError: On a row-count mismatch.
    """
    if len(df) != n:
        raise ValueError(f"{what} table has {len(df)} rows, expected {n}")


def rx_plan_from_frames(
    part: str,
    rate_mhz: float,
    alpha: float,
    signals: pd.DataFrame,
    cddc: pd.DataFrame,
    fddc: pd.DataFrame,
    extras: dict[str, Any],
) -> RxPlan:
    """Build an Rx plan from editor frames.

    Args:
        part: Part name.
        rate_mhz: ADC rate in MHz.
        alpha: Passband fraction.
        signals: Signals frame.
        cddc: CDDC frame.
        fddc: FDDC frame.
        extras: Frame dict holding ``cddc_nco_phases``/``fddc_nco_phases``.

    Returns:
        A fresh Rx plan.

    Raises:
        ValueError: On empty cells, wrong table sizes or negative RF.
    """
    adapter = get_adapter(part)
    dp = adapter.rx_datapath()
    fs = _hz(rate_mhz)
    _check_rows(cddc, len(dp.cddc_enabled), "CDDC")
    _check_rows(fddc, len(dp.fddc_enabled), "FDDC")
    targets: dict[str, list[str]] = {}

    rf: list[float] = []
    a2c: list[int] = []
    c_en: list[bool] = []
    c_dec: list[int] = []
    for i in range(len(cddc)):
        row = cddc.iloc[i]
        name = f"cddc{i}"
        c_en.append(bool(row["enabled"]))
        rf.append(_hz(_num(row["rf_mhz"], f"{name} RF NCO")))
        c_dec.append(int(_num(row["decimation"], f"{name} decimation")))
        a2c.append(int(_num(row["adc"], f"{name} ADC")))
        t = _parse_targets(row["targets"])
        if t:
            targets[name] = t
    dp.cddc_enabled = c_en
    dp.cddc_decimations = c_dec
    dp.cddc_nco_frequencies = [rf_to_nco(f, fs)[0] for f in rf]

    f_en: list[bool] = []
    f_src: list[int] = []
    f_nco: list[float] = []
    f_dec: list[int] = []
    for j in range(len(fddc)):
        row = fddc.iloc[j]
        name = f"fddc{j}"
        f_en.append(bool(row["enabled"]))
        f_src.append(int(_num(row["source"], f"{name} source")))
        f_nco.append(_hz(_num(row["nco_mhz"], f"{name} NCO")))
        f_dec.append(int(_num(row["decimation"], f"{name} decimation")))
        t = _parse_targets(row["targets"])
        if t:
            targets[name] = t
    dp.fddc_enabled = f_en
    dp.fddc_source = f_src
    dp.fddc_nco_frequencies = f_nco
    dp.fddc_decimations = f_dec
    dp.cddc_nco_phases = copy.deepcopy(
        list(extras.get("cddc_nco_phases", dp.cddc_nco_phases))
    )
    dp.fddc_nco_phases = copy.deepcopy(
        list(extras.get("fddc_nco_phases", dp.fddc_nco_phases))
    )
    return RxPlan(
        part=part,
        adc_rate_hz=fs,
        signals=_signals_from_frame(signals, "adc"),
        datapath=dp,
        cddc_rf_hz=rf,
        adc_to_cddc=a2c,
        targets=targets,
        alpha=float(alpha),
    )


def tx_frames_from_plan(plan: TxPlan) -> dict[str, Any]:
    """Build Tx editor frames from a plan.

    Args:
        plan: The Tx plan.

    Returns:
        Dict with ``signals``, ``cduc``, ``fduc`` and ``dac`` frames
        plus ``cduc_interp``, ``fduc_interp``, ``cduc_sources``,
        ``cduc_nco_phases`` and ``fduc_nco_phases``.
    """
    dp = plan.datapath
    n_c = len(dp.cduc_enabled)
    n_f = len(dp.fduc_enabled)
    cduc = pd.DataFrame(
        {
            "enabled": [bool(x) for x in dp.cduc_enabled],
            "dac_nco_mhz": [float(f) / 1e6 for f in plan.cduc_dac_hz],
        },
        index=[f"cduc{i}" for i in range(n_c)],
    )
    fduc = pd.DataFrame(
        {
            "enabled": [bool(x) for x in dp.fduc_enabled],
            "source": [int(x) for x in dp.fduc_source],
            "nco_mhz": [float(f) / 1e6 for f in dp.fduc_nco_frequencies],
        },
        index=[f"fduc{j}" for j in range(n_f)],
    )
    dac = pd.DataFrame(
        {
            "cducs": [
                ", ".join(str(int(c)) for c in srcs) for srcs in dp.cduc_sources
            ]
        },
        index=[f"dac{j}" for j in range(len(dp.cduc_sources))],
    )
    return {
        "signals": _signals_frame(plan.signals, "fduc"),
        "cduc": cduc,
        "fduc": fduc,
        "dac": dac,
        "cduc_interp": int(dp.cduc_interpolation),
        "fduc_interp": int(dp.fduc_interpolation),
        "cduc_sources": copy.deepcopy([list(s) for s in dp.cduc_sources]),
        "cduc_nco_phases": copy.deepcopy(list(dp.cduc_nco_phases)),
        "fduc_nco_phases": copy.deepcopy(list(dp.fduc_nco_phases)),
    }


def tx_plan_from_frames(
    part: str,
    rate_mhz: float,
    alpha: float,
    cduc_interp: int,
    fduc_interp: int,
    signals: pd.DataFrame,
    cduc: pd.DataFrame,
    fduc: pd.DataFrame,
    extras: dict[str, Any],
    dac: pd.DataFrame | None = None,
    notes: list[str] | None = None,
) -> TxPlan:
    """Build a Tx plan from editor frames.

    Args:
        part: Part name.
        rate_mhz: DAC rate in MHz.
        alpha: Passband fraction.
        cduc_interp: CDUC interpolation.
        fduc_interp: FDUC interpolation.
        signals: Signals frame.
        cduc: CDUC frame.
        fduc: FDUC frame.
        extras: Frame dict holding ``cduc_sources`` and NCO phases.
        dac: DAC routing frame; when given it overrides
            ``extras["cduc_sources"]``.
        notes: If given, receives messages about ignored routing entries.

    Returns:
        A fresh Tx plan.

    Raises:
        ValueError: On empty cells or wrong table sizes.
    """
    adapter = get_adapter(part)
    dp = adapter.tx_datapath()
    fs = _hz(rate_mhz)
    _check_rows(cduc, len(dp.cduc_enabled), "CDUC")
    _check_rows(fduc, len(dp.fduc_enabled), "FDUC")

    dac_hz = [
        _hz(_num(cduc.iloc[i]["dac_nco_mhz"], f"cduc{i} DAC NCO"))
        for i in range(len(cduc))
    ]
    dp.cduc_enabled = [bool(x) for x in cduc["enabled"]]
    dp.cduc_interpolation = int(cduc_interp)
    dp.cduc_nco_frequencies = [wrap_frequency(f, fs) for f in dac_hz]
    dp.fduc_enabled = [bool(x) for x in fduc["enabled"]]
    dp.fduc_interpolation = int(fduc_interp)
    dp.fduc_source = [
        int(_num(fduc.iloc[j]["source"], f"fduc{j} source"))
        for j in range(len(fduc))
    ]
    dp.fduc_nco_frequencies = [
        _hz(_num(fduc.iloc[j]["nco_mhz"], f"fduc{j} NCO"))
        for j in range(len(fduc))
    ]
    if dac is not None:
        _check_rows(dac, adapter.num_dacs, "DAC")
        routing, msgs = parse_dac_routing(dac, len(dp.cduc_enabled))
        dp.cduc_sources = routing
        if notes is not None:
            notes.extend(msgs)
    elif "cduc_sources" in extras:
        dp.cduc_sources = copy.deepcopy(extras["cduc_sources"])
    dp.cduc_nco_phases = copy.deepcopy(
        list(extras.get("cduc_nco_phases", dp.cduc_nco_phases))
    )
    dp.fduc_nco_phases = copy.deepcopy(
        list(extras.get("fduc_nco_phases", dp.fduc_nco_phases))
    )
    return TxPlan(
        part=part,
        dac_rate_hz=fs,
        signals=_signals_from_frame(signals, "fduc"),
        datapath=dp,
        cduc_dac_hz=dac_hz,
        alpha=float(alpha),
    )


def parse_dac_routing(
    dac: pd.DataFrame, n_cduc: int
) -> tuple[list[list[int]], list[str]]:
    """Parse the DAC routing table into ``cduc_sources``.

    Args:
        dac: Frame with a ``cducs`` column of comma-separated 1-indexed
            CDUC numbers, one row per DAC.
        n_cduc: Number of CDUCs.

    Returns:
        Tuple of (per-DAC CDUC lists, messages about ignored entries).
    """
    routing: list[list[int]] = []
    notes: list[str] = []
    for j in range(len(dac)):
        srcs: list[int] = []
        for tok in _parse_targets(dac.iloc[j]["cducs"]):
            try:
                c = int(tok)
            except ValueError:
                notes.append(f"dac{j}: ignored CDUC {tok!r} (not a number)")
                continue
            if not 1 <= c <= n_cduc:
                notes.append(f"dac{j}: ignored CDUC {c} (valid 1 to {n_cduc})")
                continue
            if c not in srcs:
                srcs.append(c)
        routing.append(srcs)
    return routing, notes


def _range(what: str, v: Any, lo: int, hi: int) -> str | None:
    """Describe an index outside [lo, hi], or None.

    Args:
        what: Item description.
        v: Value.
        lo: Lowest valid value.
        hi: Highest valid value.

    Returns:
        Problem text or None.
    """
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        return f"{what} {v} is out of range {lo} to {hi}"
    return None


def _choice(what: str, v: Any, opts: list[int]) -> str | None:
    """Describe a value not among the allowed options, or None.

    Args:
        what: Item description.
        v: Value.
        opts: Allowed values.

    Returns:
        Problem text or None.
    """
    if v not in opts:
        return f"{what} {v} is not one of {list(opts)}"
    return None


def rx_index_problem(plan: RxPlan) -> str | None:
    """Find the first out-of-range index or ratio in an Rx plan.

    Args:
        plan: The Rx plan, e.g. freshly loaded from a config.

    Returns:
        Problem text, or None if every index and ratio is valid.
    """
    adapter = get_adapter(plan.part)
    dp = plan.datapath
    n_adc = adapter.num_adcs
    n_c = len(dp.cddc_enabled)
    checks: list[str | None] = []
    for s in plan.signals:
        checks.append(_range(f"signal {s.name} ADC", s.source, 0, n_adc - 1))
    for i in range(n_c):
        checks.append(_range(f"cddc{i} ADC", plan.adc_to_cddc[i], 0, n_adc - 1))
        checks.append(
            _choice(
                f"cddc{i} decimation",
                dp.cddc_decimations[i],
                dp.cddc_decimations_available,
            )
        )
    for j in range(len(dp.fddc_enabled)):
        checks.append(_range(f"fddc{j} source CDDC", dp.fddc_source[j], 1, n_c))
        checks.append(
            _choice(
                f"fddc{j} decimation",
                dp.fddc_decimations[j],
                dp.fddc_decimations_available,
            )
        )
    return next((c for c in checks if c), None)


def tx_index_problem(plan: TxPlan) -> str | None:
    """Find the first out-of-range index or ratio in a Tx plan.

    Args:
        plan: The Tx plan, e.g. freshly loaded from a config.

    Returns:
        Problem text, or None if every index and ratio is valid.
    """
    adapter = get_adapter(plan.part)
    dp = plan.datapath
    n_c = len(dp.cduc_enabled)
    n_f = len(dp.fduc_enabled)
    checks: list[str | None] = [
        _choice(
            "CDUC interpolation",
            dp.cduc_interpolation,
            dp.cduc_interpolation_available,
        ),
        _choice(
            "FDUC interpolation",
            dp.fduc_interpolation,
            dp.fduc_interpolation_available,
        ),
    ]
    for s in plan.signals:
        checks.append(_range(f"signal {s.name} FDUC", s.source, 0, n_f - 1))
    for j in range(n_f):
        checks.append(_range(f"fduc{j} source CDUC", dp.fduc_source[j], 1, n_c))
    srcs = dp.cduc_sources
    if not isinstance(srcs, list) or len(srcs) != adapter.num_dacs:
        checks.append(f"DAC routing must list {adapter.num_dacs} DACs")
    else:
        for j, lst in enumerate(srcs):
            if not isinstance(lst, list):
                checks.append(f"dac{j} routing must be a list")
                continue
            for c in lst:
                checks.append(_range(f"dac{j} CDUC", c, 1, n_c))
    return next((c for c in checks if c), None)


def rx_stage_info(plan: RxPlan) -> dict[str, tuple[float | None, str | None]]:
    """NCO (MHz) and ratio label for each Rx stage.

    Args:
        plan: The Rx plan.

    Returns:
        Channel to (NCO in MHz or None, ratio label or None).
    """
    dp = plan.datapath
    info: dict[str, tuple[float | None, str | None]] = {}
    for i, rf in enumerate(plan.cddc_rf_hz):
        info[f"cddc{i}"] = (rf / 1e6, f"÷{dp.cddc_decimations[i]}")
    for j, nco in enumerate(dp.fddc_nco_frequencies):
        info[f"fddc{j}"] = (nco / 1e6, f"÷{dp.fddc_decimations[j]}")
    return info


def tx_stage_info(plan: TxPlan) -> dict[str, tuple[float | None, str | None]]:
    """NCO (MHz) and ratio label for each Tx stage.

    Args:
        plan: The Tx plan.

    Returns:
        Channel to (NCO in MHz or None, ratio label or None).
    """
    dp = plan.datapath
    info: dict[str, tuple[float | None, str | None]] = {}
    for i, f in enumerate(plan.cduc_dac_hz):
        info[f"cduc{i}"] = (f / 1e6, f"×{dp.cduc_interpolation}")
    for j, nco in enumerate(dp.fduc_nco_frequencies):
        info[f"fduc{j}"] = (nco / 1e6, f"×{dp.fduc_interpolation}")
    return info


def fmt_num(v: float) -> str:
    """Format a number without trailing zeros.

    Args:
        v: Value.

    Returns:
        Integer text when integral, else up to three decimals.
    """
    if not math.isfinite(v):
        return str(v)
    if abs(v - round(v)) < 1e-9:
        return f"{round(v):d}"
    return f"{v:.3f}".rstrip("0").rstrip(".")


def stage_caption(
    stage: StageOutput, nco_mhz: float | None, ratio: str | None
) -> str:
    """Caption text for one stage row.

    Args:
        stage: Stage output.
        nco_mhz: NCO frequency in MHz, if the stage has one.
        ratio: Ratio label such as ``"÷4"``, if any.

    Returns:
        Channel, NCO, ratio and rate (or the error text) joined by dots.
    """
    parts = [stage.channel]
    if nco_mhz is not None:
        parts.append(f"NCO {fmt_num(nco_mhz)} MHz")
    if ratio:
        parts.append(ratio)
    if stage.error:
        parts.append(f"error: {stage.error}")
    else:
        parts.append(f"{fmt_num(stage.rate_hz / 1e6)} MSPS")
    return " · ".join(parts)


def verdict_line(v: Verdict) -> str:
    """One markdown line for a verdict, prefixed by its status glyph.

    Args:
        v: The verdict.

    Returns:
        Glyph followed by the messages joined with a middle dot.
    """
    msgs = " · ".join(v.messages) or "no signals"
    return f"{GLYPHS.get(v.status, GLYPHS['error'])} {msgs}"
