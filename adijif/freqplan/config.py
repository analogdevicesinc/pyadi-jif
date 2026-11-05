"""JSON export/import of frequency plans."""

from __future__ import annotations

import copy
import json
from typing import Any

from .adc import rf_to_nco
from .parts import get_adapter
from .rx import RxPlan, Signal
from .spectrum import wrap_frequency
from .tx import TxPlan

CONFIG_VERSION = 1

_RX_CDDC = ("enabled", "decimations", "nco_frequencies", "nco_phases")
_RX_FDDC = (*_RX_CDDC, "source")
_TX_CDUC = ("enabled", "nco_frequencies", "nco_phases", "sources")
_TX_FDUC = ("enabled", "nco_frequencies", "nco_phases", "sources")


def _signals_to_list(signals: list[Signal]) -> list[dict[str, Any]]:
    return [
        {
            "name": s.name,
            "center_hz": float(s.center_hz),
            "bandwidth_hz": float(s.bandwidth_hz),
            "source": int(s.source),
        }
        for s in signals
    ]


def _wrap_fddc(rx: RxPlan, j: int, f: float) -> float:
    """Wrap an FDDC NCO into its source CDDC's output Nyquist band.

    Args:
        rx: Rx plan.
        j: FDDC index.
        f: FDDC NCO frequency in Hz.

    Returns:
        The NCO wrapped into [-fs_cddc_out/2, fs_cddc_out/2), or unchanged
        if the FDDC's source CDDC is out of range.
    """
    dp = rx.datapath
    c = dp.fddc_source[j] - 1
    if not 0 <= c < len(dp.cddc_decimations):
        return float(f)
    return float(wrap_frequency(f, rx.adc_rate_hz / dp.cddc_decimations[c]))


def _rx_to_dict(rx: RxPlan) -> dict[str, Any]:
    fs = rx.adc_rate_hz
    dp = copy.deepcopy(rx.datapath.get_config())
    folded = [rf_to_nco(f, fs) for f in rx.cddc_rf_hz]
    dp["cddc"]["nco_frequencies"] = [float(n) for n, _ in folded]
    dp["cddc"]["nyquist_zones"] = [int(z) for _, z in folded]
    fddc = dp["fddc"]
    fddc["nco_frequencies"] = [
        _wrap_fddc(rx, j, f) for j, f in enumerate(fddc["nco_frequencies"])
    ]
    return {
        "adc_rate_hz": float(fs),
        "signals": _signals_to_list(rx.signals),
        "adc_to_cddc": [int(a) for a in rx.adc_to_cddc],
        "cddc_rf_hz": [float(f) for f in rx.cddc_rf_hz],
        "targets": copy.deepcopy(rx.targets),
        "datapath": dp,
    }


def _tx_to_dict(tx: TxPlan) -> dict[str, Any]:
    fs = tx.dac_rate_hz
    dp = copy.deepcopy(tx.datapath.get_config())
    dp["fduc"]["sources"] = list(tx.datapath.fduc_source)
    dp["cduc"]["nco_frequencies"] = [
        float(wrap_frequency(f, fs)) for f in tx.cduc_dac_hz
    ]
    fduc_out = fs / tx.datapath.cduc_interpolation
    dp["fduc"]["nco_frequencies"] = [
        float(wrap_frequency(f, fduc_out))
        for f in dp["fduc"]["nco_frequencies"]
    ]
    return {
        "dac_rate_hz": float(fs),
        "signals": _signals_to_list(tx.signals),
        "cduc_dac_hz": [float(f) for f in tx.cduc_dac_hz],
        "datapath": dp,
    }


def plan_to_dict(
    rx: RxPlan | None, tx: TxPlan | None, view: dict | None = None
) -> dict:
    """Serialize plans to a JSON-compatible dict.

    Args:
        rx: Rx plan, or None.
        tx: Tx plan, or None.
        view: Optional UI view state.

    Returns:
        JSON-serializable config dict.

    Raises:
        ValueError: If both plans are None.
    """
    first = rx if rx is not None else tx
    if first is None:
        raise ValueError("Nothing to export: both rx and tx are None")
    out: dict[str, Any] = {
        "version": CONFIG_VERSION,
        "part": first.part,
        "alpha": float(first.alpha),
    }
    if rx is not None:
        out["rx"] = _rx_to_dict(rx)
    if tx is not None:
        out["tx"] = _tx_to_dict(tx)
    out["view"] = copy.deepcopy(view) if view else {}
    return out


def _check_len(name: str, value: Any, expected: int) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    if len(value) != expected:
        raise ValueError(
            f"{name} has {len(value)} entries, expected {expected}"
        )
    return value


def _signals_from_list(name: str, raw: Any) -> list[Signal]:
    if not isinstance(raw, list):
        raise ValueError(f"{name} must be a list")
    return [
        Signal(
            str(s["name"]),
            float(s["center_hz"]),
            float(s["bandwidth_hz"]),
            int(s["source"]),
        )
        for s in raw
    ]


def _rx_from_dict(part: str, alpha: float, r: dict) -> RxPlan:
    adapter = get_adapter(part)
    dp = adapter.rx_datapath()
    sec = r["datapath"]
    for grp, keys in (("cddc", _RX_CDDC), ("fddc", _RX_FDDC)):
        for k in keys:
            fresh = getattr(dp, f"{grp}_{k}")
            _check_len(f"rx.datapath.{grp}.{k}", sec[grp][k], len(fresh))
    n_cddc = len(dp.cddc_enabled)
    rf = _check_len("rx.cddc_rf_hz", r["cddc_rf_hz"], n_cddc)
    a2c = _check_len("rx.adc_to_cddc", r["adc_to_cddc"], n_cddc)
    for grp, keys in (("cddc", _RX_CDDC), ("fddc", _RX_FDDC)):
        for k in keys:
            setattr(dp, f"{grp}_{k}", copy.deepcopy(sec[grp][k]))
    return RxPlan(
        part=part,
        adc_rate_hz=float(r["adc_rate_hz"]),
        signals=_signals_from_list("rx.signals", r["signals"]),
        datapath=dp,
        cddc_rf_hz=[float(f) for f in rf],
        adc_to_cddc=[int(a) for a in a2c],
        targets=copy.deepcopy(dict(r.get("targets") or {})),
        alpha=alpha,
    )


def _tx_from_dict(part: str, alpha: float, t: dict) -> TxPlan:
    adapter = get_adapter(part)
    dp = adapter.tx_datapath()
    sec = t["datapath"]
    for k in _TX_CDUC:
        attr = f"cduc_{k}"
        _check_len(
            f"tx.datapath.cduc.{k}", sec["cduc"][k], len(getattr(dp, attr))
        )
    for k in _TX_FDUC:
        attr = "fduc_source" if k == "sources" else f"fduc_{k}"
        _check_len(
            f"tx.datapath.fduc.{k}", sec["fduc"][k], len(getattr(dp, attr))
        )
    cd = _check_len("tx.cduc_dac_hz", t["cduc_dac_hz"], len(dp.cduc_enabled))
    dp.cduc_enabled = copy.deepcopy(sec["cduc"]["enabled"])
    dp.cduc_interpolation = copy.deepcopy(sec["cduc"]["interpolation"])
    dp.cduc_nco_frequencies = copy.deepcopy(sec["cduc"]["nco_frequencies"])
    dp.cduc_nco_phases = copy.deepcopy(sec["cduc"]["nco_phases"])
    dp.cduc_sources = copy.deepcopy(sec["cduc"]["sources"])
    dp.fduc_enabled = copy.deepcopy(sec["fduc"]["enabled"])
    dp.fduc_interpolation = copy.deepcopy(sec["fduc"]["interpolation"])
    dp.fduc_nco_frequencies = copy.deepcopy(sec["fduc"]["nco_frequencies"])
    dp.fduc_nco_phases = copy.deepcopy(sec["fduc"]["nco_phases"])
    dp.fduc_source = copy.deepcopy(sec["fduc"]["sources"])
    return TxPlan(
        part=part,
        dac_rate_hz=float(t["dac_rate_hz"]),
        signals=_signals_from_list("tx.signals", t["signals"]),
        datapath=dp,
        cduc_dac_hz=[float(f) for f in cd],
        alpha=alpha,
    )


def plan_from_dict(d: dict) -> tuple[RxPlan | None, TxPlan | None, dict]:
    """Rebuild plans from a config dict.

    Args:
        d: Config dict as produced by :func:`plan_to_dict`.

    Returns:
        Tuple of (rx plan or None, tx plan or None, view dict).

    Raises:
        ValueError: If the config is malformed, has an unknown version, an
            unsupported part, or mismatched list lengths.
    """
    if not isinstance(d, dict):
        raise ValueError("Config must be a JSON object")
    if d.get("version") != CONFIG_VERSION:
        raise ValueError(
            f"Unsupported or missing config version {d.get('version')!r}; "
            f"expected {CONFIG_VERSION}"
        )
    try:
        part = d["part"]
    except KeyError:
        raise ValueError("Config is missing key 'part'") from None
    if not isinstance(part, str):
        raise ValueError(f"Config 'part' must be a string, got {part!r}")
    get_adapter(part)
    section = "config"
    try:
        alpha = float(d.get("alpha", 0.8))
        rx = tx = None
        if d.get("rx") is not None:
            section = "rx"
            rx = _rx_from_dict(part, alpha, d["rx"])
        if d.get("tx") is not None:
            section = "tx"
            tx = _tx_from_dict(part, alpha, d["tx"])
        view = copy.deepcopy(d.get("view") or {})
    except KeyError as exc:
        raise ValueError(
            f"Malformed {section} config: missing key {exc}"
        ) from None
    except (TypeError, AttributeError) as exc:
        raise ValueError(f"Malformed {section} config: {exc}") from None
    return rx, tx, view


def dumps(
    rx: RxPlan | None, tx: TxPlan | None, view: dict | None = None
) -> str:
    """Serialize plans to a JSON string.

    Args:
        rx: Rx plan, or None.
        tx: Tx plan, or None.
        view: Optional UI view state.

    Returns:
        JSON text with indent 2.
    """
    return json.dumps(plan_to_dict(rx, tx, view), indent=2)


def loads(s: str) -> tuple[RxPlan | None, TxPlan | None, dict]:
    """Parse plans from a JSON string.

    Args:
        s: JSON text.

    Returns:
        Tuple of (rx plan or None, tx plan or None, view dict).

    Raises:
        ValueError: If the text is not valid JSON or the config is invalid.
    """
    try:
        d = json.loads(s)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from None
    return plan_from_dict(d)
