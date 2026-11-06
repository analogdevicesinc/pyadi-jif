"""JESD204 link sizing for a frequency plan.

The planner's enabled outputs set the link: every complex output (an Rx
FDDC, or a CDDC with no FDDC behind it; a Tx FDUC, or a CDUC when no FDUC
is used) carries I and Q, so ``M = 2 * outputs``. Outputs may run at
different rates; the link runs at the fastest one (smallest overall
decimation or interpolation), as the converter does. The part's quick
configuration mode table is then filtered on that M and each mode's lane
rate is checked against the converter and, optionally, an FPGA's
transceivers. No solver is used.
"""

from __future__ import annotations

import copy
import functools
import re
from dataclasses import dataclass
from typing import Any

from .parts import get_adapter
from .rx import RxPlan, RxResult
from .tx import TxPlan, TxResult

JESD_CLASSES = ("jesd204b", "jesd204c")
# Dev kits with transceiver presets in adijif's Xilinx model.
DEV_KITS = ("zcu102", "zc706", "vcu118", "adsy1100", "vck190")
# Most lanes a custom FPGA may declare (the page's lane input limit).
MAX_FPGA_LANES = 64
# Rate comparisons tolerate float rounding.
_REL_TOL = 1e-9


@dataclass(frozen=True)
class LinkRequirement:
    """What one direction's enabled outputs need from the JESD204 link.

    Attributes:
        direction: ``"rx"`` or ``"tx"``.
        part: Part name.
        M: Converter count on the link (two per complex output).
        sample_rate_hz: Link sample rate, the fastest output rate.
        channels: Output block ids carried, e.g. ``("fddc0", "fddc2")``.
        rate_set_by: Channels running at the link rate.
        excluded: Enabled outputs left out, as ``"FDDC0: reason"``.
        converter_rate_hz: ADC or DAC sample rate.
        dropped: Block ids of the excluded outputs, e.g. ``("fduc4",)``.
    """

    direction: str
    part: str
    M: int
    sample_rate_hz: float
    channels: tuple[str, ...]
    rate_set_by: tuple[str, ...]
    excluded: tuple[str, ...]
    converter_rate_hz: float
    dropped: tuple[str, ...] = ()


@dataclass(frozen=True)
class FpgaLimits:
    """Transceiver limits an FPGA puts on the link.

    Attributes:
        name: Dev kit name, or ``"custom"``.
        transceiver: Xilinx transceiver type, e.g. ``"GTYE4"``.
        max_lane_rate_hz: Highest lane rate the transceiver supports.
        max_lanes: Lanes available to the converter.
    """

    name: str
    transceiver: str
    max_lane_rate_hz: float
    max_lanes: int


@dataclass(frozen=True)
class ModeFit:
    """One quick configuration mode checked against a link requirement.

    Attributes:
        mode: Quick configuration mode id, e.g. ``"23"``.
        jesd_class: ``"jesd204b"`` or ``"jesd204c"``.
        M: Converters.
        L: Lanes.
        F: Octets per frame per lane.
        S: Samples per converter per frame.
        Np: Bits per sample on the link.
        HD: High density flag (0 if the table has none).
        sample_rate_hz: Link sample rate the mode was checked at.
        lane_rate_hz: Resulting lane rate (bit clock).
        converter_ok: Whether the converter accepts the configuration.
        converter_reason: Why not, if ``converter_ok`` is False.
        fpga_ok: Whether the FPGA can take it; None with no FPGA chosen.
        fpga_reason: Why not, if ``fpga_ok`` is False.
    """

    mode: str
    jesd_class: str
    M: int
    L: int
    F: int
    S: int
    Np: int
    HD: int
    sample_rate_hz: float
    lane_rate_hz: float
    converter_ok: bool
    converter_reason: str | None
    fpga_ok: bool | None
    fpga_reason: str | None

    @property
    def ok(self) -> bool:
        """Whether the mode fits the converter and, if given, the FPGA."""
        return self.converter_ok and self.fpga_ok is not False

    @property
    def key(self) -> tuple[str, str]:
        """``(jesd_class, mode)``, unique within a part and direction."""
        return (self.jesd_class, self.mode)

    def label(self) -> str:
        """Short human-readable description of the mode.

        Returns:
            Text like ``"204C mode 23 · L=12 Np=12 · 20.625 Gbps"``.
        """
        return (
            f"{_class_label(self.jesd_class)} mode {self.mode} · "
            f"L={self.L} Np={self.Np} · {self.lane_rate_hz / 1e9:.5g} Gbps"
        )


@dataclass(frozen=True)
class LinkSolution:
    """Modes checked for one link requirement.

    Attributes:
        requirement: The link requirement.
        fpga: FPGA limits used, or None.
        modes: Every table mode with the requirement's M, in table order.
        message: Why no mode could be listed, or None.
    """

    requirement: LinkRequirement
    fpga: FpgaLimits | None
    modes: list[ModeFit]
    message: str | None

    @property
    def fits(self) -> list[ModeFit]:
        """Modes that fit."""
        return [m for m in self.modes if m.ok]


def _class_label(jesd_class: str) -> str:
    return jesd_class.replace("jesd", "").upper()


def _requirement(
    direction: str,
    part: str,
    rates: dict[str, float],
    dropped: dict[str, str],
    converter_rate_hz: float,
) -> LinkRequirement:
    fs = max(rates.values(), default=0.0)
    fastest = tuple(
        c for c, r in rates.items() if abs(r - fs) <= _REL_TOL * max(fs, 1.0)
    )
    return LinkRequirement(
        direction=direction,
        part=part,
        M=2 * len(rates),
        sample_rate_hz=float(fs),
        channels=tuple(rates),
        rate_set_by=fastest if rates else (),
        excluded=tuple(f"{c.upper()}: {why}" for c, why in dropped.items()),
        converter_rate_hz=float(converter_rate_hz),
        dropped=tuple(dropped),
    )


def rx_link(plan: RxPlan, result: RxResult) -> LinkRequirement:
    """Size the Rx link from the plan's outputs.

    Every output stage (an FDDC, or a CDDC no enabled FDDC uses) is one
    complex channel. Outputs in error, such as an FDDC whose CDDC is
    disabled, are left out and listed in ``excluded``.

    Args:
        plan: Rx plan.
        result: Its computed result.

    Returns:
        The link requirement.
    """
    rates: dict[str, float] = {}
    dropped: dict[str, str] = {}
    for name, stage in result.stages.items():
        if not stage.is_output:
            continue
        if stage.error:
            dropped[name] = stage.error
        else:
            rates[name] = float(stage.rate_hz)
    return _requirement("rx", plan.part, rates, dropped, plan.adc_rate_hz)


def tx_link(plan: TxPlan, result: TxResult) -> LinkRequirement:
    """Size the Tx link from the plan's enabled FDUCs (or CDUCs).

    Each enabled FDUC is one complex channel at its input rate, the DAC
    rate over CDUC x FDUC interpolation. With no FDUC enabled the enabled
    CDUCs are the channels, at the DAC rate over CDUC interpolation.

    Args:
        plan: Tx plan.
        result: Its computed result.

    Returns:
        The link requirement.
    """
    dp = plan.datapath
    rates: dict[str, float] = {}
    dropped: dict[str, str] = {}
    if any(dp.fduc_enabled):
        fs = plan.dac_rate_hz / (dp.cduc_interpolation * dp.fduc_interpolation)
        for i, en in enumerate(dp.fduc_enabled):
            if not en:
                continue
            name = f"fduc{i}"
            stage = result.stages.get(name)
            if stage is None or stage.error:
                dropped[name] = stage.error if stage else "not computed"
            else:
                rates[name] = float(fs)
    else:
        fs = plan.dac_rate_hz / dp.cduc_interpolation
        for i, en in enumerate(dp.cduc_enabled):
            if en:
                rates[f"cduc{i}"] = float(fs)
    return _requirement("tx", plan.part, rates, dropped, plan.dac_rate_hz)


@functools.lru_cache(maxsize=None)
def _xcvr_max_rate(transceiver: str) -> float:
    from adijif.fpgas.xilinx import xilinx

    f = xilinx()
    f.transceiver_type = transceiver
    return float(f.max_lane_rate)


def _transceivers() -> tuple[str, ...]:
    from adijif.fpgas.xilinx import xilinx

    return tuple(xilinx.available_transceiver_types)


TRANSCEIVERS = _transceivers()


@functools.lru_cache(maxsize=None)
def fpga_from_devkit(name: str) -> FpgaLimits:
    """Transceiver limits of a dev kit known to adijif's Xilinx model.

    Args:
        name: Dev kit name, one of :data:`DEV_KITS`.

    Returns:
        The kit's limits.

    Raises:
        ValueError: If the kit is unknown.
    """
    if name not in DEV_KITS:
        raise ValueError(f"Unknown dev kit {name!r}; known: {list(DEV_KITS)}")
    from adijif.fpgas.xilinx import xilinx

    f = xilinx()
    f.setup_by_dev_kit_name(name)
    return FpgaLimits(
        name=name,
        transceiver=str(f.transceiver_type),
        max_lane_rate_hz=float(f.max_lane_rate),
        max_lanes=int(f.max_serdes_lanes),
    )


def fpga_custom(transceiver: str, lanes: int) -> FpgaLimits:
    """Limits for a transceiver type and a lane count.

    Args:
        transceiver: Xilinx transceiver type, one of :data:`TRANSCEIVERS`.
        lanes: Lanes available, 1 to :data:`MAX_FPGA_LANES`.

    Returns:
        The limits.

    Raises:
        ValueError: If the transceiver is unknown or lanes is out of range.
    """
    if transceiver not in TRANSCEIVERS:
        raise ValueError(
            f"Unknown transceiver {transceiver!r}; known: {list(TRANSCEIVERS)}"
        )
    if (
        not isinstance(lanes, int)
        or isinstance(lanes, bool)
        or not 1 <= lanes <= MAX_FPGA_LANES
    ):
        raise ValueError(
            f"lanes must be an integer from 1 to {MAX_FPGA_LANES}, got {lanes!r}"
        )
    return FpgaLimits("custom", transceiver, _xcvr_max_rate(transceiver), lanes)


def fpga_from_choice(choice: dict | None) -> FpgaLimits | None:
    """FPGA limits from a config choice.

    Args:
        choice: None, ``{"devkit": name}`` or
            ``{"transceiver": type, "lanes": n}``.

    Returns:
        The limits, or None for no FPGA.
    """
    if not choice:
        return None
    if "devkit" in choice:
        return fpga_from_devkit(choice["devkit"])
    return fpga_custom(choice["transceiver"], choice["lanes"])


def _converter_class(part: str, direction: str) -> Any:
    adapter = get_adapter(part)
    return adapter.rx_converter if direction == "rx" else adapter.tx_converter


def mode_table_values(part: str, direction: str, field: str) -> list[int]:
    """Sorted distinct values of one mode-table field, e.g. ``"Np"``.

    Args:
        part: Part name.
        direction: ``"rx"`` or ``"tx"``.
        field: Mode-table field name.

    Returns:
        The values, or an empty list if the part has no JESD204 model.
    """
    cls = _converter_class(part, direction)
    if cls is None:
        return []
    table = cls().quick_configuration_modes
    return sorted(
        {int(c[field]) for t in table.values() for c in t.values() if field in c}
    )


def solve_link(
    plan: RxPlan | TxPlan,
    req: LinkRequirement,
    fpga: FpgaLimits | None = None,
) -> LinkSolution:
    """Check every mode with the requirement's M.

    A fresh converter model gets a copy of the plan's datapath, so its
    clock checks use the plan's real decimation or interpolation.

    Args:
        plan: The plan the requirement came from.
        req: Link requirement.
        fpga: Optional FPGA limits.

    Returns:
        The checked modes.
    """
    cls = _converter_class(req.part, req.direction)
    if cls is None:
        msg = f"No JESD204 model for {req.part} {req.direction.upper()}"
        return LinkSolution(req, fpga, [], msg)
    if req.M == 0:
        what = "an FDDC or CDDC" if req.direction == "rx" else "an FDUC or CDUC"
        msg = f"No active outputs: enable {what} to size the link."
        return LinkSolution(req, fpga, [], msg)
    conv = cls()
    table = conv.quick_configuration_modes
    rows = [
        (jc, mode, cfg)
        for jc in JESD_CLASSES
        for mode, cfg in table.get(jc, {}).items()
        if cfg.get("M") == req.M
    ]
    if not rows:
        ms = sorted({c["M"] for t in table.values() for c in t.values()})
        msg = (
            f"No single-link {req.part} mode for M={req.M} "
            f"(the mode table has M in {ms}); dual-link is not modelled."
        )
        return LinkSolution(req, fpga, [], msg)
    conv.datapath = _datapath_without(plan.datapath, req.dropped)
    modes = [_check(conv, jc, mode, cfg, req, fpga) for jc, mode, cfg in rows]
    return LinkSolution(req, fpga, modes, None)


def _datapath_without(datapath: Any, dropped: tuple[str, ...]) -> Any:
    """Copy of a datapath with the dropped outputs disabled.

    An output left off the link (e.g. an FDUC whose CDUC is disabled)
    would otherwise make the converter's overall-ratio maths raise.

    Args:
        datapath: Plan datapath.
        dropped: Block ids such as ``"fduc4"``.

    Returns:
        The copy.
    """
    dp = copy.deepcopy(datapath)
    for block in dropped:
        m = re.fullmatch(r"([a-z]+)(\d+)", block)
        if m is None:
            continue
        kind, idx = m.group(1), int(m.group(2))
        enabled = list(getattr(dp, f"{kind}_enabled"))
        enabled[idx] = False
        setattr(dp, f"{kind}_enabled", enabled)
    return dp


def _lane_rate_problem(conv: Any, jesd_class: str, lane: float) -> str | None:
    """The converter's lane-rate limit for this JESD204 class, if broken.

    Checked before ``validate_config``, whose generic check names the
    wrong class for 204B modes.

    Args:
        conv: Converter model with the mode applied.
        jesd_class: ``"jesd204b"`` or ``"jesd204c"``.
        lane: Lane rate in bits per second.

    Returns:
        A reason like ``"lane rate 400 Gbps > 204B max 20 Gbps"``, or None.
    """
    lo, hi = float(conv.bit_clock_min), float(conv.bit_clock_max)
    cls = _class_label(jesd_class)
    if lane > hi * (1 + _REL_TOL):
        return f"lane rate {lane / 1e9:.5g} Gbps > {cls} max {hi / 1e9:.5g} Gbps"
    if lane < lo * (1 - _REL_TOL):
        return f"lane rate {lane / 1e9:.5g} Gbps < {cls} min {lo / 1e9:.5g} Gbps"
    return None


def _check(
    conv: Any,
    jesd_class: str,
    mode: str,
    cfg: dict,
    req: LinkRequirement,
    fpga: FpgaLimits | None,
) -> ModeFit:
    conv.set_quick_configuration_mode(mode, jesd_class)
    conv.sample_clock = req.sample_rate_hz
    lane = float(conv.bit_clock)
    reason = _lane_rate_problem(conv, jesd_class, lane)
    if reason is None:
        try:
            conv.validate_config()
        except Exception as e:  # noqa: BLE001 - adijif raises bare Exceptions
            reason = str(e).strip() or type(e).__name__
    fpga_ok = fpga_reason = None
    if fpga is not None:
        why = []
        if lane > fpga.max_lane_rate_hz * (1 + _REL_TOL):
            why.append(
                f"over {fpga.transceiver} max "
                f"{fpga.max_lane_rate_hz / 1e9:.5g} Gbps"
            )
        if int(cfg["L"]) > fpga.max_lanes:
            why.append(f"L={cfg['L']} > {fpga.max_lanes} FPGA lanes")
        fpga_ok = not why
        fpga_reason = "; ".join(why) or None
    return ModeFit(
        mode=str(mode),
        jesd_class=jesd_class,
        M=int(cfg["M"]),
        L=int(cfg["L"]),
        F=int(cfg["F"]),
        S=int(cfg["S"]),
        Np=int(cfg["Np"]),
        HD=int(cfg.get("HD", 0)),
        sample_rate_hz=float(req.sample_rate_hz),
        lane_rate_hz=lane,
        converter_ok=reason is None,
        converter_reason=reason,
        fpga_ok=fpga_ok,
        fpga_reason=fpga_reason,
    )


def _fmt_msps(hz: float) -> str:
    return f"{hz / 1e6:.6g} MSPS"


def link_summary(sol: LinkSolution) -> str:
    """One-line description of a link solution.

    Args:
        sol: The solution.

    Returns:
        Text like ``"M=8 from 4 complex outputs (FDDC0, …) · 2500 MSPS set
        by FDDC4 · 1 of 23 modes fit"``.
    """
    req = sol.requirement
    if req.M == 0:
        return sol.message or "No active outputs"
    n = len(req.channels)
    chans = ", ".join(c.upper() for c in req.channels)
    by = ", ".join(c.upper() for c in req.rate_set_by)
    text = (
        f"M={req.M} from {n} complex output{'s' if n != 1 else ''} "
        f"({chans}) · {_fmt_msps(req.sample_rate_hz)} set by {by}"
    )
    if sol.message:
        return f"{text} · {sol.message}"
    text += f" · {len(sol.fits)} of {len(sol.modes)} modes fit"
    if sol.fpga is not None:
        f = sol.fpga
        text += (
            f" · FPGA {f.name} ({f.transceiver} ≤ "
            f"{f.max_lane_rate_hz / 1e9:.5g} Gbps, {f.max_lanes} lanes)"
        )
    return text


# --- config ----------------------------------------------------------------


def jesd_to_dict(fpga: dict | None, chosen: dict[str, ModeFit | None]) -> dict:
    """Serialize the FPGA choice and the chosen mode per direction.

    Args:
        fpga: None, ``{"devkit": name}`` or
            ``{"transceiver": type, "lanes": n}``.
        chosen: ``"rx"``/``"tx"`` to the chosen mode, or None.

    Returns:
        The ``jesd`` config section.
    """
    out: dict[str, Any] = {"fpga": copy.deepcopy(fpga) if fpga else None}
    for d in ("rx", "tx"):
        m = chosen.get(d)
        out[d] = (
            None
            if m is None
            else {
                "mode": m.mode,
                "jesd_class": m.jesd_class,
                "M": m.M,
                "L": m.L,
                "F": m.F,
                "S": m.S,
                "Np": m.Np,
                "HD": m.HD,
                "sample_rate_hz": m.sample_rate_hz,
                "lane_rate_hz": m.lane_rate_hz,
            }
        )
    return out


def _fpga_from_raw(raw: Any) -> dict | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("jesd.fpga must be an object or null")
    if "devkit" in raw:
        name = raw["devkit"]
        if name not in DEV_KITS:
            raise ValueError(f"jesd.fpga.devkit {name!r} is not a known dev kit")
        return {"devkit": name}
    try:
        fpga_custom(raw["transceiver"], raw["lanes"])
    except KeyError as e:
        raise ValueError(f"jesd.fpga is missing {e}") from None
    return {"transceiver": raw["transceiver"], "lanes": raw["lanes"]}


def jesd_from_dict(
    d: Any,
) -> tuple[dict | None, dict[str, tuple[str, str] | None]]:
    """Parse the ``jesd`` config section.

    Only the FPGA choice and each mode's ``(jesd_class, mode)`` are read;
    the other stored mode fields are informational and recomputed.

    Args:
        d: The section, or None when the config has none.

    Returns:
        ``(fpga choice or None, {"rx": key or None, "tx": key or None})``.

    Raises:
        ValueError: If the section is malformed.
    """
    modes: dict[str, tuple[str, str] | None] = {"rx": None, "tx": None}
    if d is None:
        return None, modes
    if not isinstance(d, dict):
        raise ValueError("jesd must be an object")
    fpga = _fpga_from_raw(d.get("fpga"))
    for direction in ("rx", "tx"):
        m = d.get(direction)
        if m is None:
            continue
        if not isinstance(m, dict):
            raise ValueError(f"jesd.{direction} must be an object or null")
        mode, jc = m.get("mode"), m.get("jesd_class")
        if not isinstance(mode, str):
            raise ValueError(f"jesd.{direction}.mode must be a string")
        if jc not in JESD_CLASSES:
            raise ValueError(
                f"jesd.{direction}.jesd_class must be one of {list(JESD_CLASSES)}"
            )
        modes[direction] = (jc, mode)
    return fpga, modes
