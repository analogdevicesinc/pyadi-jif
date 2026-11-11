"""Constraint-based frequency planning using IBM CP Optimizer.

This module is independent of Streamlit. Automatic setting names are returned by
:func:`available_settings`; every other setting and all routing remain fixed.
Rates can be lists or integer-indexed grids without materializing the grid.
The MxFE RF-frequency search grid defaults to 1 Hz; physical NCO quantization is
applied before independent spectrum and JESD validation. Simple ADC NCOs are
solved directly as tuning words, which matters for the AD9680's 12-bit NCO.
"""

from __future__ import annotations

import copy
import math
import time
from dataclasses import dataclass, field
from typing import Any

from .adc import rf_to_nco
from .checks import evaluate_dac, evaluate_output
from .jesd import FpgaLimits, rx_link, solve_link, tx_link
from .parts import get_adapter
from .rx import RxPlan, compute_rx
from .spectrum import TOL_HZ
from .tx import TxPlan, compute_tx


@dataclass(frozen=True)
class RateDomain:
    """Allowed rates in Hz: either a finite list or an inclusive stepped range."""

    values_hz: tuple[float, ...] | None = None
    minimum_hz: float | None = None
    maximum_hz: float | None = None
    step_hz: float = 1.0

    def __post_init__(self) -> None:
        """Validate a bounded finite domain without expanding a range."""
        if self.values_hz is not None:
            values = tuple(float(v) for v in self.values_hz)
            if not values or any(
                not math.isfinite(v) or v <= 0 for v in values
            ):
                raise ValueError(
                    "Rate list must contain finite positive values"
                )
            if self.minimum_hz is not None or self.maximum_hz is not None:
                raise ValueError("Specify a rate list or a range, not both")
            object.__setattr__(self, "values_hz", tuple(sorted(set(values))))
        else:
            if self.minimum_hz is None or self.maximum_hz is None:
                raise ValueError("Rate range needs minimum_hz and maximum_hz")
            if any(
                not math.isfinite(v) or v <= 0
                for v in (self.minimum_hz, self.maximum_hz, self.step_hz)
            ):
                raise ValueError(
                    "Rate range and step must be finite and positive"
                )
            if self.minimum_hz > self.maximum_hz:
                raise ValueError("Minimum rate exceeds maximum rate")
            if (self.maximum_hz - self.minimum_hz) / self.step_hz > 2**52:
                raise ValueError(
                    "Rate grid has too many steps; increase step_hz"
                )


@dataclass(frozen=True)
class SignalTarget:
    """Desired Rx output offset or Tx RF center for a signal on a fixed path."""

    direction: str
    signal: str
    path: str
    frequency_hz: float = 0.0


@dataclass
class SolveRequest:
    """Immutable-by-convention input to :func:`solve_plan`.

    ``automatic`` contains setting keys from :func:`available_settings`.
    Signals in each included plan must all have targets. ``jesd_modes`` can pin
    a direction to a ``(jesd_class, mode)`` pair. An imported simple-device
    profile remains a hard constraint, even when its settings are automatic.
    """

    rx: RxPlan | None = None
    tx: TxPlan | None = None
    targets: list[SignalTarget] = field(default_factory=list)
    automatic: set[str] = field(default_factory=set)
    rate_domains: dict[str, RateDomain] = field(default_factory=dict)
    fpga: FpgaLimits | None = None
    timeout_s: float = 30.0
    tolerance_hz: float = 1.0
    frequency_step_hz: float = 1.0
    jesd_modes: dict[str, tuple[str, str]] = field(default_factory=dict)


@dataclass
class SolveResult:
    """A validated solution or an explicit non-success outcome.

    Status is optimal, feasible, infeasible, timeout, unavailable or invalid.
    Optimality is with respect to the requested rate/frequency grids. A timeout
    with a validated incumbent returns feasible and explains the time limit.
    ``rx`` and ``tx`` are fresh copies and are absent when no solution exists.
    """

    status: str
    rx: RxPlan | None = None
    tx: TxPlan | None = None
    message: str = ""
    objective_bps: float | None = None
    achieved: list[dict[str, Any]] = field(default_factory=list)
    settings: dict[str, float] = field(default_factory=dict)
    elapsed_s: float = 0.0
    modes: dict[str, tuple[str, str]] = field(default_factory=dict)


def _topology(adapter: Any) -> str:
    return getattr(adapter, "topology", "mxfe")


def available_settings(
    plan: RxPlan | TxPlan, direction: str
) -> dict[str, float]:
    """Current values of scalar settings that may be marked automatic."""
    if direction not in ("rx", "tx"):
        raise ValueError("Direction must be rx or tx")
    is_rx = direction == "rx"
    adapter, dp = get_adapter(plan.part), plan.datapath
    values = {
        f"{direction}.rate": float(
            plan.adc_rate_hz if is_rx else plan.dac_rate_hz
        )
    }
    if _topology(adapter) != "mxfe":
        values[f"{direction}.factor"] = float(dp.factor)
        bits = getattr(adapter, f"{direction}_nco_bits", None)
        if bits:
            values.update(
                {
                    f"{direction}.nco.{i}": float(dp.nco_hz[i])
                    for i, enabled in enumerate(dp.enabled)
                    if enabled
                }
            )
        if getattr(adapter, "lo_bounds_hz", None):
            values[f"{direction}.lo"] = float(dp.lo_hz)
        return values
    if is_rx:
        for kind in ("cddc", "fddc"):
            for i, enabled in enumerate(getattr(dp, f"{kind}_enabled")):
                if enabled:
                    values[f"rx.{kind}.{i}.decimation"] = float(
                        getattr(dp, f"{kind}_decimations")[i]
                    )
                    values[f"rx.{kind}.{i}.nco"] = float(
                        plan.cddc_rf_hz[i]
                        if kind == "cddc"
                        else dp.fddc_nco_frequencies[i]
                    )
    else:
        for kind in ("cduc", "fduc"):
            values[f"tx.{kind}.interpolation"] = float(
                getattr(dp, f"{kind}_interpolation")
            )
            for i, enabled in enumerate(getattr(dp, f"{kind}_enabled")):
                if enabled:
                    values[f"tx.{kind}.{i}.nco"] = float(
                        plan.cduc_dac_hz[i]
                        if kind == "cduc"
                        else dp.fduc_nco_frequencies[i]
                    )
    return values


def _set_value(plan: Any, key: str, value: float) -> None:
    parts = key.split(".")
    dp = plan.datapath
    if parts[1] == "rate":
        setattr(
            plan, "adc_rate_hz" if parts[0] == "rx" else "dac_rate_hz", value
        )
    elif parts[1] == "factor":
        dp.factor = int(round(value))
    elif parts[1] == "lo":
        dp.lo_hz = value
    elif parts[1] == "nco":
        dp.nco_hz[int(parts[2])] = value
    elif parts[-1] == "interpolation":
        setattr(dp, f"{parts[1]}_interpolation", int(round(value)))
    elif parts[-1] == "decimation":
        getattr(dp, f"{parts[1]}_decimations")[int(parts[2])] = int(
            round(value)
        )
    elif parts[1] == "cddc":
        plan.cddc_rf_hz[int(parts[2])] = value
    elif parts[1] == "cduc":
        plan.cduc_dac_hz[int(parts[2])] = value
    else:
        getattr(dp, f"{parts[1]}_nco_frequencies")[int(parts[2])] = value


def _bounds(adapter: Any, direction: str) -> tuple[float, float]:
    bounds = getattr(adapter, f"{direction}_rate_bounds_hz", None)
    if bounds:
        return bounds
    conv = getattr(adapter, f"{direction}_converter")()
    return float(conv.converter_clock_min), float(conv.converter_clock_max)


def _targets(request: SolveRequest, direction: str) -> list[SignalTarget]:
    return [
        target for target in request.targets if target.direction == direction
    ]


def _bands_overlap(
    center: float, bandwidth: float, other_center: float, other_bandwidth: float
) -> bool:
    """Detect interval collisions, including coincident tones and tone-in-band."""
    distance = abs(center - other_center)
    half_width = (bandwidth + other_bandwidth) / 2
    if bandwidth == 0 or other_bandwidth == 0:
        return distance <= half_width + 1e-6
    return distance < half_width - 1e-6


def _validate_request(request: SolveRequest) -> dict[str, float]:
    if request.rx is None and request.tx is None:
        raise ValueError("Include an Rx or Tx plan")
    for value, label in (
        (request.timeout_s, "timeout"),
        (request.tolerance_hz, "tolerance"),
        (request.frequency_step_hz, "frequency step"),
    ):
        if (
            not math.isfinite(value)
            or value < 0
            or (label != "tolerance" and value == 0)
        ):
            raise ValueError(f"Invalid {label}")
    settings: dict[str, float] = {}
    for direction in ("rx", "tx"):
        plan = getattr(request, direction)
        if plan is not None:
            settings.update(available_settings(plan, direction))
    unknown = request.automatic - settings.keys()
    if unknown:
        raise ValueError(
            f"Unknown or inactive automatic setting: {sorted(unknown)}"
        )
    if any(not math.isfinite(v) for v in settings.values()):
        raise ValueError("Settings must be finite")
    if any(
        value <= 0 for key, value in settings.items() if key.endswith(".rate")
    ):
        raise ValueError("Sample rates must be positive")
    if request.fpga and (
        type(request.fpga.max_lanes) is not int
        or request.fpga.max_lanes <= 0
        or not math.isfinite(request.fpga.max_lane_rate_hz)
        or request.fpga.max_lane_rate_hz <= 0
    ):
        raise ValueError("FPGA limits must be finite and positive")
    if set(request.rate_domains) - {"rx", "tx"}:
        raise ValueError("Unknown rate-domain direction")
    for direction, domain in request.rate_domains.items():
        if getattr(request, direction) is None or not isinstance(
            domain, RateDomain
        ):
            raise ValueError(
                "Rate domains must refer to included plans and use RateDomain"
            )
    for direction in request.jesd_modes:
        if direction not in ("rx", "tx") or getattr(request, direction) is None:
            raise ValueError("JESD restriction refers to an absent direction")
    for direction in ("rx", "tx"):
        plan = getattr(request, direction)
        if plan is None:
            continue
        if not 0 < plan.alpha <= 1:
            raise ValueError("Passband fraction must be in (0, 1]")
        names = [signal.name for signal in plan.signals]
        if (
            not names
            or any(not isinstance(name, str) or not name for name in names)
            or len(names) != len(set(names))
        ):
            raise ValueError("Plans need signals with unique names")
        adapter = get_adapter(plan.part)
        if direction not in adapter.directions:
            raise ValueError(f"{plan.part} has no {direction.upper()} path")
        source_count = (
            adapter.num_adcs
            if direction == "rx"
            else len(plan.datapath.fduc_enabled)
            if adapter.topology == "mxfe"
            else adapter.num_dacs
        )
        for signal in plan.signals:
            if (
                not math.isfinite(signal.center_hz)
                or not math.isfinite(signal.bandwidth_hz)
                or signal.bandwidth_hz < 0
            ):
                raise ValueError(
                    "Signal frequencies must be finite and bandwidth nonnegative"
                )
            if (
                type(signal.source) is not int
                or not 0 <= signal.source < source_count
            ):
                raise ValueError(f"Signal {signal.name}: invalid source index")
        selected = _targets(request, direction)
        if set(names) != {target.signal for target in selected}:
            raise ValueError(
                f"Targets must cover every {direction.upper()} signal exactly by name"
            )
    identities = set()
    for target in request.targets:
        if (
            target.direction not in ("rx", "tx")
            or getattr(request, target.direction) is None
        ):
            raise ValueError("Target refers to an absent direction")
        if not math.isfinite(target.frequency_hz):
            raise ValueError("Target frequency must be finite")
        identity = (target.direction, target.signal, target.path)
        if identity in identities:
            raise ValueError("Duplicate signal/path target")
        identities.add(identity)
    if request.rx and request.tx and request.rx.part != request.tx.part:
        raise ValueError(
            "Combined solving requires the same part in both directions"
        )
    return settings


class _Problem:
    def __init__(
        self, request: SolveRequest, initial: dict[str, float]
    ) -> None:
        from docplex.cp.model import CpoModel

        self.request, self.initial = request, initial
        self.model = CpoModel(name="frequency_plan")
        self.settings: dict[str, Any] = {}
        self.decisions: list[Any] = []
        self.link_rates: dict[str, Any] = {}
        self.mode_rows: dict[str, list[tuple[str, str, dict]]] = {}
        self.mode_indices: dict[str, Any] = {}
        self.objectives: list[Any] = []
        self.placements: dict[tuple[str, str, str], Any] = {}

    def integer(
        self, key: str, lo: int, hi: int, domain: list[int] | None = None
    ) -> Any:
        var = (
            self.model.integer_var(domain=domain, name=key)
            if domain is not None
            else self.model.integer_var(lo, hi, name=key)
        )
        self.decisions.append(var)
        return var

    def setting(
        self,
        key: str,
        lo: float,
        hi: float,
        choices: tuple[int, ...] | list[int] | None = None,
    ) -> Any:
        if key in self.settings:
            return self.settings[key]
        current = self.initial[key]
        if key not in self.request.automatic:
            value: Any = current
        elif choices is not None:
            value = self.integer(key, 0, 0, [int(c) for c in choices])
        else:
            step = self.request.frequency_step_hz
            value = (
                self.integer(key, math.ceil(lo / step), math.floor(hi / step))
                * step
            )
        self.model.add(value >= lo)
        self.model.add(value <= hi)
        if choices is not None:
            self.model.add(self.model.logical_or([value == c for c in choices]))
        self.settings[key] = value
        return value

    def rate(self, plan: Any, direction: str) -> Any:
        adapter = get_adapter(plan.part)
        lo, hi = _bounds(adapter, direction)
        key = f"{direction}.rate"
        if key not in self.request.automatic:
            rate: Any = self.initial[key]
            domain = self.request.rate_domains.get(direction)
            if domain is not None:
                if domain.values_hz is not None:
                    self.model.add(
                        any(
                            math.isclose(rate, v, rel_tol=0, abs_tol=1e-6)
                            for v in domain.values_hz
                        )
                    )
                else:
                    grid_index = (rate - domain.minimum_hz) / domain.step_hz
                    self.model.add(
                        domain.minimum_hz <= rate <= domain.maximum_hz
                        and math.isclose(
                            grid_index,
                            round(grid_index),
                            rel_tol=0,
                            abs_tol=1e-9,
                        )
                    )
        else:
            domain = self.request.rate_domains.get(direction)
            if domain is None:
                raise ValueError(
                    f"Automatic {direction} sample rate needs a rate domain"
                )
            if domain.values_hz is not None:
                idx = self.integer(key + ".index", 0, len(domain.values_hz) - 1)
                rate = self.model.element(list(domain.values_hz), idx)
            else:
                count = math.floor(
                    (domain.maximum_hz - domain.minimum_hz) / domain.step_hz
                    + 1e-9
                )
                idx = self.integer(key + ".index", 0, count)
                rate = domain.minimum_hz + idx * domain.step_hz
        self.model.add(rate >= lo)
        self.model.add(rate <= hi)
        self.settings[key] = rate
        return rate

    def band(
        self, center: Any, bandwidth: float, rate: Any, alpha: float
    ) -> None:
        self.model.add(
            self.model.abs(center) + bandwidth / 2 <= alpha * rate / 2
        )

    def target(self, target: SignalTarget, center: Any) -> None:
        self.model.add(
            self.model.abs(center - target.frequency_hz)
            <= self.request.tolerance_hz
        )
        self.placements[(target.direction, target.signal, target.path)] = center

    def coarse_tuning(
        self,
        key: str,
        requested: Any,
        fs: Any,
        bits: int,
        upper_hz: float,
        minimum_rate: float,
        rx: bool,
    ) -> Any:
        """Represent coarse tuning words exactly, including RF Nyquist zones."""
        if bits > 32:
            return requested
        if rx:
            zone = self.integer(
                key + ".zone", 0, math.ceil(2 * upper_hz / minimum_rate) + 1
            )
            word = self.integer(key + ".word", 0, 2 ** (bits - 1))
            self.model.add(requested >= zone * fs / 2)
            self.model.add(requested <= (zone + 1) * fs / 2)
            odd = zone % 2
            tune = word * (fs / float(2**bits))
            actual = (zone // 2) * fs + (1 - odd) * tune + odd * (fs - tune)
        else:
            word = self.integer(
                key + ".word", -(2 ** (bits - 1)), 2 ** (bits - 1) - 1
            )
            cycle = self.integer(key + ".cycle", -1, 1)
            actual = word * (fs / float(2**bits)) + cycle * fs
        self.model.add(
            self.model.abs(actual - requested) <= fs / float(2**bits) / 2
        )
        self.settings[key] = actual
        return actual

    def build_rx(self, plan: RxPlan) -> None:
        adapter, dp = get_adapter(plan.part), plan.datapath
        if _topology(adapter) != "mxfe":
            self.build_simple(plan, "rx")
            return
        fs = self.rate(plan, "rx")
        _, max_rate = _bounds(adapter, "rx")
        coarse, fine, out_rates = {}, {}, {}
        for i, enabled in enumerate(dp.cddc_enabled):
            if not enabled:
                continue
            if not 0 <= plan.adc_to_cddc[i] < adapter.num_adcs:
                raise ValueError("CDDC route references an invalid ADC")
            dec = self.setting(
                f"rx.cddc.{i}.decimation",
                min(dp.cddc_decimations_available),
                max(dp.cddc_decimations_available),
                dp.cddc_decimations_available,
            )
            upper = max(s.center_hz for s in plan.signals) + max_rate
            nco = self.setting(f"rx.cddc.{i}.nco", 0, upper)
            nco = self.coarse_tuning(
                f"rx.cddc.{i}.nco",
                nco,
                fs,
                getattr(adapter, "rx_coarse_nco_bits", 48),
                upper,
                _bounds(adapter, "rx")[0],
                True,
            )
            if plan.part in ("AD9081", "AD9082"):
                self.model.add(self.model.if_then(dec == 1, nco == 0))
            coarse[i] = (dec, nco, fs / dec)
            out_rates[f"cddc{i}"] = fs / dec
        for j, enabled in enumerate(dp.fddc_enabled):
            if not enabled:
                continue
            parent = dp.fddc_source[j] - 1
            if parent not in coarse:
                raise ValueError("Enabled FDDC has no enabled source CDDC")
            out_rates.pop(f"cddc{parent}", None)
            dec = self.setting(
                f"rx.fddc.{j}.decimation",
                min(dp.fddc_decimations_available),
                max(dp.fddc_decimations_available),
                dp.fddc_decimations_available,
            )
            nco = self.setting(f"rx.fddc.{j}.nco", -max_rate / 2, max_rate / 2)
            rate = coarse[parent][2]
            limit = getattr(adapter, "rx_fine_rate_max_hz", None)
            if limit:
                self.model.add(rate <= limit)
            self.model.add(nco >= -rate / 2)
            self.model.add(nco <= rate / 2)
            if plan.part in ("AD9081", "AD9082"):
                self.model.add(self.model.if_then(dec == 1, nco == 0))
            fine[j] = (dec, nco, rate / dec)
            out_rates[f"fddc{j}"] = rate / dec
        signals = {s.name: s for s in plan.signals}
        for target in _targets(self.request, "rx"):
            if target.path not in out_rates:
                raise ValueError(
                    f"Target path {target.path} is not an enabled Rx output"
                )
            signal = signals[target.signal]
            is_fine = target.path.startswith("fddc")
            idx = int(target.path[4:])
            ci = dp.fddc_source[idx] - 1 if is_fine else idx
            if plan.adc_to_cddc[ci] != signal.source:
                raise ValueError(
                    f"Signal {signal.name} is not routed to {target.path}"
                )
            _, nco, cr = coarse[ci]
            # A band and its coarse NCO must be in the same real-ADC zone.
            # This models the existing even-zone orientation correction.
            min_rate, _ = _bounds(adapter, "rx")
            z = self.integer(
                f"zone.{target.path}.{signal.name}",
                0,
                max(1, math.ceil(2 * (signal.center_hz + max_rate) / min_rate)),
            )
            self.model.add(
                signal.center_hz - signal.bandwidth_hz / 2 >= z * (fs / 2)
            )
            self.model.add(
                signal.center_hz + signal.bandwidth_hz / 2 <= (z + 1) * (fs / 2)
            )
            self.model.add(nco >= z * (fs / 2))
            self.model.add(nco <= (z + 1) * (fs / 2))
            center = signal.center_hz - nco
            self.band(center, signal.bandwidth_hz, cr, plan.alpha)
            if is_fine:
                _, fnco, fr = fine[idx]
                center = center - fnco
                self.band(center, signal.bandwidth_hz, fr, plan.alpha)
            self.target(target, center)
        if not out_rates:
            raise ValueError("No enabled Rx output")
        rate = self.model.max(list(out_rates.values()))
        self.link(plan, "rx", rate, 2 * len(out_rates), fs)

    def build_tx(self, plan: TxPlan) -> None:
        adapter, dp = get_adapter(plan.part), plan.datapath
        if _topology(adapter) != "mxfe":
            self.build_simple(plan, "tx")
            return
        fs = self.rate(plan, "tx")
        _, max_rate = _bounds(adapter, "tx")
        ci = self.setting(
            "tx.cduc.interpolation",
            min(dp.cduc_interpolation_available),
            max(dp.cduc_interpolation_available),
            dp.cduc_interpolation_available,
        )
        fi = self.setting(
            "tx.fduc.interpolation",
            min(dp.fduc_interpolation_available),
            max(dp.fduc_interpolation_available),
            dp.fduc_interpolation_available,
        )
        coarse, fine = {}, {}
        for i, enabled in enumerate(dp.cduc_enabled):
            if enabled:
                coarse[i] = self.setting(
                    f"tx.cduc.{i}.nco", -max_rate, max_rate
                )
                coarse[i] = self.coarse_tuning(
                    f"tx.cduc.{i}.nco",
                    coarse[i],
                    fs,
                    getattr(adapter, "tx_coarse_nco_bits", 48),
                    max_rate,
                    _bounds(adapter, "tx")[0],
                    False,
                )
                self.model.add(self.model.abs(coarse[i]) <= fs)
                if plan.part in ("AD9081", "AD9082"):
                    self.model.add(self.model.if_then(ci == 1, coarse[i] == 0))
        for i, enabled in enumerate(dp.fduc_enabled):
            if enabled:
                parent = dp.fduc_source[i] - 1
                if parent not in coarse:
                    raise ValueError(
                        "Enabled FDUC has no enabled destination CDUC"
                    )
                fine[i] = self.setting(
                    f"tx.fduc.{i}.nco", -max_rate / 2, max_rate / 2
                )
                self.model.add(self.model.abs(fine[i]) <= fs / ci / 2)
                limit = getattr(adapter, "tx_fine_rate_max_hz", None)
                if limit:
                    self.model.add(fs / ci <= limit)
                if plan.part in ("AD9081", "AD9082"):
                    self.model.add(self.model.if_then(fi == 1, fine[i] == 0))
        signals = {s.name: s for s in plan.signals}
        for target in _targets(self.request, "tx"):
            signal = signals[target.signal]
            if (
                not target.path.startswith("dac")
                or not target.path[3:].isdigit()
            ):
                raise ValueError("Tx target path must name a DAC")
            dac = int(target.path[3:])
            if not 0 <= dac < adapter.num_dacs or signal.source not in fine:
                raise ValueError(
                    "Tx target references an invalid or disabled path"
                )
            parent = dp.fduc_source[signal.source] - 1
            if parent + 1 not in dp.cduc_sources[dac]:
                raise ValueError(
                    f"Signal {signal.name} is not routed to {target.path}"
                )
            self.band(
                signal.center_hz,
                signal.bandwidth_hz,
                fs / (ci * fi),
                plan.alpha,
            )
            middle = signal.center_hz + fine[signal.source]
            self.band(middle, signal.bandwidth_hz, fs / ci, plan.alpha)
            raw = middle + coarse[parent]
            # Real DAC mirrors permit either sign; the selected RF band is
            # represented in [0, fs] just as compute_tx's DAC spectra are.
            wrap = self.integer(f"tx.wrap.{signal.name}.{dac}", -2, 2)
            mirror = self.integer(f"tx.mirror.{signal.name}.{dac}", 0, 1)
            rf = (1 - 2 * mirror) * raw - wrap * fs
            self.model.add(rf >= 0)
            self.model.add(rf <= fs)
            self.model.add(target.frequency_hz - signal.bandwidth_hz / 2 >= 0)
            self.model.add(target.frequency_hz + signal.bandwidth_hz / 2 <= fs)
            self.target(target, rf)
        count = len(fine) if fine else len(coarse)
        if not count:
            raise ValueError("No enabled Tx inputs")
        self.link(
            plan, "tx", fs / (ci * fi) if fine else fs / ci, 2 * count, fs
        )

    def build_simple(self, plan: Any, direction: str) -> None:
        adapter, dp = get_adapter(plan.part), plan.datapath
        fs = self.rate(plan, direction)
        factors = getattr(adapter, f"{direction}_factors")
        factor = self.setting(
            f"{direction}.factor", min(factors), max(factors), factors
        )
        rate = fs / factor
        lo: Any = 0.0
        if adapter.lo_bounds_hz:
            lo = self.setting(f"{direction}.lo", *adapter.lo_bounds_hz)
        bits = getattr(adapter, f"{direction}_nco_bits")
        ncos: dict[int, Any] = {}
        for i, enabled in enumerate(dp.enabled):
            if not enabled:
                continue
            key = f"{direction}.nco.{i}"
            if bits and key in self.request.automatic:
                word = self.integer(
                    key + ".word", -(2 ** (bits - 1)), 2 ** (bits - 1) - 1
                )
                ncos[i] = word * (fs / float(2**bits))
                self.settings[key] = ncos[i]
            elif bits:
                ncos[i] = self.initial[key]
                self.settings[key] = ncos[i]
            else:
                ncos[i] = 0.0
            if adapter.topology == "adc":
                self.model.add(self.model.if_then(factor == 1, ncos[i] == 0))
        profile = getattr(dp, "profile_constraints", {}) or {}
        allowed = adapter.profile_rate_factors(direction)
        if allowed:
            self.model.add(
                self.model.logical_or(
                    [
                        self.model.logical_and(rate == r, factor == f)
                        for r, f in allowed.items()
                    ]
                )
            )
        if profile:
            for key, value in profile.items():
                if key in ("sample_rate_hz", "sample_clock"):
                    self.model.add(rate == value)
                elif key in ("factor", "decimation", "interpolation"):
                    self.model.add(factor == value)
                elif key == "converter_rate_hz":
                    self.model.add(fs == value)
                elif key == "lo_hz":
                    self.model.add(lo == value)
                else:
                    raise ValueError(f"Unknown profile constraint {key!r}")
        signals = {s.name: s for s in plan.signals}
        for target in _targets(self.request, direction):
            signal = signals[target.signal]
            i = signal.source
            expected = f"ddc{i}" if direction == "rx" else f"dac{i}"
            if target.path != expected or i not in ncos:
                raise ValueError(
                    f"Signal {signal.name} is not routed to enabled path {target.path}"
                )
            if direction == "rx":
                center = signal.center_hz - lo
                if adapter.topology == "adc":
                    # Explicit sampling aliases, with an integer Nyquist zone.
                    minimum, _ = _bounds(adapter, direction)
                    zone = self.integer(
                        f"rx.zone.{signal.name}",
                        0,
                        max(1, math.ceil(2 * signal.center_hz / minimum)),
                    )
                    self.model.add(
                        signal.center_hz - signal.bandwidth_hz / 2
                        >= zone * fs / 2
                    )
                    self.model.add(
                        signal.center_hz + signal.bandwidth_hz / 2
                        <= (zone + 1) * fs / 2
                    )
                    pair = zone // 2
                    odd = zone % 2
                    center = (1 - odd) * (
                        signal.center_hz - pair * fs
                    ) + odd * ((pair + 1) * fs - signal.center_hz)
                center = center - ncos[i]
                self.band(center, signal.bandwidth_hz, rate, plan.alpha)
            else:
                self.band(
                    signal.center_hz, signal.bandwidth_hz, rate, plan.alpha
                )
                center = signal.center_hz + ncos[i] + lo
                if adapter.topology == "dac":
                    center = self.model.abs(center)
                    self.model.add(center - signal.bandwidth_hz / 2 >= 0)
                    self.model.add(center + signal.bandwidth_hz / 2 <= fs / 2)
            self.target(target, center)
        count = sum(bool(en) for en in dp.enabled)
        if not count:
            raise ValueError("No enabled channels")
        mult: Any = 2 if getattr(adapter, f"{direction}_complex") else 1
        if adapter.topology == "adc":
            mult = self.model.conditional(factor == 1, 1, 2)
        self.link(plan, direction, rate, count * mult, fs)

    def link(
        self, plan: Any, direction: str, rate: Any, count: Any, fs: Any
    ) -> None:
        adapter = get_adapter(plan.part)
        conv = getattr(adapter, f"{direction}_converter")()
        rows = []
        requested = self.request.jesd_modes.get(direction)
        for jc, table in conv.quick_configuration_modes.items():
            for mode, cfg in table.items():
                if cfg.get("DualLink", False):
                    continue
                if requested and (jc, str(mode)) != tuple(requested):
                    continue
                if isinstance(count, int) and cfg["M"] != count:
                    continue
                if self.request.fpga and cfg["L"] > self.request.fpga.max_lanes:
                    continue
                rows.append((jc, str(mode), cfg))
        if not rows:
            self.model.add(False)
            self.objectives.append(0.0)
            self.link_rates[direction] = rate
            return
        idx = self.integer(direction + ".mode", 0, len(rows) - 1)
        self.mode_rows[direction], self.mode_indices[direction] = rows, idx
        for i, (jc, mode, cfg) in enumerate(rows):
            conv.set_quick_configuration_mode(mode, jc)
            overhead = 10 / 8 if jc == "jesd204b" else 66 / 64
            lane = rate * cfg["M"] * cfg["Np"] * overhead / cfg["L"]
            upper = float(conv.bit_clock_max)
            if self.request.fpga:
                upper = min(upper, self.request.fpga.max_lane_rate_hz)
            minimum_rate = float(conv.sample_clock_min)
            if plan.part == "AD9680":
                minimum_rate = (
                    float(conv.converter_clock_min) / self.settings["rx.factor"]
                )
            valid = [
                count == cfg["M"],
                lane >= float(conv.bit_clock_min),
                lane <= upper,
                rate >= minimum_rate,
                rate <= float(conv.sample_clock_max),
            ]
            # Existing converter validators check allowed overall factors for
            # legacy MxFE mode tables; encode this before candidate validation.
            combos = cfg.get(
                "decimations" if direction == "rx" else "interpolations"
            )
            if combos:
                products = [c["coarse"] * c["fine"] for c in combos]
                valid.append(
                    self.model.logical_or([fs == rate * p for p in products])
                )
            self.model.add(
                self.model.if_then(idx == i, self.model.logical_and(valid))
            )
        widths = [cfg["M"] * cfg["Np"] for _, _, cfg in rows]
        self.objectives.append(rate * self.model.element(widths, idx))
        self.link_rates[direction] = rate

    def finish(self) -> None:
        request = self.request
        # Separation applies to achieved frequencies. Requested centers may
        # overlap while their tolerance intervals allow disjoint actual bands.
        for i, target in enumerate(request.targets):
            plan = getattr(request, target.direction)
            signals = {s.name: s for s in plan.signals}
            for other in request.targets[i + 1 :]:
                if (other.direction, other.path) == (
                    target.direction,
                    target.path,
                ) and other.signal != target.signal:
                    a = self.placements[
                        (target.direction, target.signal, target.path)
                    ]
                    b = self.placements[
                        (other.direction, other.signal, other.path)
                    ]
                    aw = signals[target.signal].bandwidth_hz
                    bw = signals[other.signal].bandwidth_hz
                    separation = self.model.abs(a - b)
                    if aw == 0 or bw == 0:
                        self.model.add(separation > (aw + bw) / 2 + 1e-6)
                    else:
                        self.model.add(separation >= (aw + bw) / 2)
        if request.rx and request.tx:
            part = request.rx.part
            rxfs, txfs = self.settings["rx.rate"], self.settings["tx.rate"]
            if part in ("AD9084", "AD9088"):
                self.model.add(
                    self.model.logical_or(txfs == rxfs, txfs == 2 * rxfs)
                )
            elif part in ("AD9081", "AD9082"):
                self.model.add(
                    self.model.logical_or(
                        [txfs == k * rxfs for k in (1, 2, 3, 4)]
                    )
                )
            elif _topology(get_adapter(part)) == "transceiver":
                rr, tr = self.link_rates["rx"], self.link_rates["tx"]
                self.model.add(
                    self.model.logical_or(
                        [tr == rr * k for k in (1, 2, 4)]
                        + [rr == tr * k for k in (2, 4)]
                    )
                )
                # Receive and transmit PLLs are independently tunable; channels
                # within each direction share the scalar LO setting.
        throughput = self.model.sum(self.objectives)
        rate_sum = self.model.sum(
            [
                value
                for key, value in self.settings.items()
                if key.endswith(".rate")
            ]
        )
        changes = self.model.sum(
            [
                self.model.abs(value - self.initial[key])
                for key, value in self.settings.items()
                if key in request.automatic
            ]
        )
        self.model.add(
            self.model.minimize_static_lex([throughput, rate_sum, changes])
        )

    def read_settings(self, solution: Any) -> dict[str, float]:
        # get_value accepts expressions only for named variables, so evaluate
        # expression trees through the model's solution evaluator.
        return {
            key: float(solution.get_value(value))
            if hasattr(value, "get_name") and value.get_name()
            else float(_eval(value, solution))
            for key, value in self.settings.items()
        }


def _eval(expr: Any, solution: Any) -> float:
    """Evaluate a CP expression through a named expression solution variable."""
    if isinstance(expr, (int, float)):
        return float(expr)
    from docplex.cp.expression import CpoValue

    if isinstance(expr, CpoValue):
        return float(expr.value)
    if expr.is_variable():
        return float(solution.get_value(expr))
    op = expr.operation.cpo_name
    args = expr.children
    values = [_eval(a, solution) for a in args] if op != "element" else []
    if op == "plus":
        return sum(values)
    if op == "minus":
        return values[0] - values[1]
    if op == "times":
        return math.prod(values)
    if op in ("floatDiv", "div"):
        return values[0] / values[1]
    if op == "intDiv":
        return values[0] // values[1]
    if op == "mod":
        return values[0] % values[1]
    if op == "element":
        array = args[0].value if hasattr(args[0], "value") else args[0].children
        return _eval(array[int(_eval(args[1], solution))], solution)
    raise ValueError(f"Cannot evaluate solver expression {op}")


def _quantize(
    plan: Any, direction: str, tolerance: float, automatic: set[str]
) -> None:
    adapter, dp = get_adapter(plan.part), plan.datapath
    bits = getattr(
        adapter,
        f"{direction}_nco_bits",
        48 if _topology(adapter) == "mxfe" else None,
    )
    if not bits:
        return
    fs = plan.adc_rate_hz if direction == "rx" else plan.dac_rate_hz
    if _topology(adapter) != "mxfe":
        for i, enabled in enumerate(dp.enabled):
            if enabled:
                old = dp.nco_hz[i]
                new = round(old / fs * 2**bits) * fs / 2**bits
                if (
                    f"{direction}.nco.{i}" not in automatic
                    and abs(new - old) > tolerance
                ):
                    raise ValueError(
                        f"Locked NCO {i} is not representable by its {bits}-bit tuning word"
                    )
                dp.nco_hz[i] = new
        return
    if direction == "rx":
        coarse_bits = getattr(adapter, "rx_coarse_nco_bits", bits)
        for i, enabled in enumerate(dp.cddc_enabled):
            if enabled:
                folded, zone = rf_to_nco(plan.cddc_rf_hz[i], fs)
                value = (
                    round(folded / fs * 2**coarse_bits) * fs / 2**coarse_bits
                )
                plan.cddc_rf_hz[i] = (
                    ((zone - 1) // 2 * fs + value)
                    if zone % 2
                    else (zone // 2 * fs - value)
                )
        for i, enabled in enumerate(dp.fddc_enabled):
            if enabled:
                rate = fs / dp.cddc_decimations[dp.fddc_source[i] - 1]
                dp.fddc_nco_frequencies[i] = (
                    round(dp.fddc_nco_frequencies[i] / rate * 2**bits)
                    * rate
                    / 2**bits
                )
    else:
        coarse_bits = getattr(adapter, "tx_coarse_nco_bits", bits)
        for i, enabled in enumerate(dp.cduc_enabled):
            if enabled:
                plan.cduc_dac_hz[i] = (
                    round(plan.cduc_dac_hz[i] / fs * 2**coarse_bits)
                    * fs
                    / 2**coarse_bits
                )
        rate = fs / dp.cduc_interpolation
        for i, enabled in enumerate(dp.fduc_enabled):
            if enabled:
                dp.fduc_nco_frequencies[i] = (
                    round(dp.fduc_nco_frequencies[i] / rate * 2**bits)
                    * rate
                    / 2**bits
                )


def _validate_candidate(
    request: SolveRequest, rx: Any, tx: Any, modes: dict[str, tuple[str, str]]
) -> tuple[float, list[dict]]:
    achieved = []
    throughput = 0.0
    for direction, plan in (("rx", rx), ("tx", tx)):
        if plan is None:
            continue
        result = compute_rx(plan) if direction == "rx" else compute_tx(plan)
        if any(stage.error for stage in result.stages.values()):
            raise ValueError("Computed datapath contains an invalid stage")
        requirements = (
            rx_link(plan, result)
            if direction == "rx"
            else tx_link(plan, result)
        )
        link = solve_link(plan, requirements, request.fpga)
        fit = next(
            (
                fit
                for fit in link.fits
                if (fit.jesd_class, fit.mode) == modes[direction]
            ),
            None,
        )
        if fit is None:
            raise ValueError(
                "Candidate does not pass converter/JESD validation"
            )
        throughput += fit.M * fit.Np * fit.sample_rate_hz
        signals = {s.name: s for s in plan.signals}
        for target in _targets(request, direction):
            stage = result.stages.get(target.path)
            if stage is None:
                raise ValueError(f"Missing output {target.path}")
            signal = signals[target.signal]
            # Verify the requested band in the computed spectrum itself,
            # independently of the expressions used by the solver.
            left = target.frequency_hz - signal.bandwidth_hz / 2
            right = target.frequency_hz + signal.bandwidth_hz / 2
            spans = [
                sp
                for sp in stage.spans
                if sp.signal == signal.name
                and not sp.attenuated
                and (direction == "tx" or not sp.image)
            ]
            candidates = [
                sp
                for sp in spans
                if sp.lo <= right + request.tolerance_hz
                and sp.hi >= left - request.tolerance_hz
            ]
            if not candidates:
                raise ValueError(
                    f"{signal.name} is absent at requested output frequency"
                )
            span = min(
                candidates,
                key=lambda sp: abs((sp.lo + sp.hi) / 2 - target.frequency_hz),
            )
            center = (span.lo + span.hi) / 2
            # Frequency-placement tolerance never relaxes the full-bandwidth
            # requirement. Only a complete clean span has a reportable center.
            if (
                span.hi - span.lo < signal.bandwidth_hz - TOL_HZ
                or abs(center - target.frequency_hz)
                > request.tolerance_hz + 1e-6
            ):
                raise ValueError(
                    f"{signal.name} is clipped or misplaced after hardware quantization"
                )
            if direction == "rx":
                target_names = [
                    t.signal
                    for t in _targets(request, direction)
                    if t.path == target.path
                ]
                adapter = get_adapter(plan.part)
                real_bypass = (
                    adapter.topology == "adc" and plan.datapath.factor == 1
                )
                verdict = (
                    evaluate_dac(stage, signals)
                    if real_bypass
                    else evaluate_output(stage, signals, target_names)
                )
                if any(
                    not interference.attenuated
                    for interference in verdict.interference
                ):
                    raise ValueError(
                        f"{target.path} contains an alias or unwanted signal"
                    )
            # Check actual clean spectrum independently of requested centers
            # and the model's placement expressions. Rx image interference is
            # checked by the verdict above; real DAC mirrors are included here.
            for other in stage.spans:
                if (
                    other.attenuated
                    or other is span
                    or (direction == "rx" and other.image)
                ):
                    continue
                overlap = _bands_overlap(
                    center,
                    signal.bandwidth_hz,
                    (other.lo + other.hi) / 2,
                    other.hi - other.lo,
                )
                same_tone = (
                    other.signal == span.signal and signal.bandwidth_hz == 0
                )
                if (
                    overlap
                    and not same_tone
                    and (
                        other.signal != span.signal or other.image != span.image
                    )
                ):
                    raise ValueError(
                        f"{target.path} contains overlapping signals or images"
                    )
            achieved.append(
                {
                    "direction": direction,
                    "signal": target.signal,
                    "path": target.path,
                    "target_hz": target.frequency_hz,
                    "achieved_hz": center,
                    "error_hz": center - target.frequency_hz,
                }
            )
    return throughput, achieved


def solve_plan(request: SolveRequest) -> SolveResult:
    """Find and independently validate settings without modifying the input.

    A failed post-check adds an exclusion for that discrete candidate and
    resumes solving within the same wall-clock budget. No arbitrary candidate
    cap is used and a time limit is never reported as proven infeasibility.
    """
    started = time.monotonic()

    def outcome(status: str, message: str, **kwargs: Any) -> SolveResult:
        return SolveResult(
            status=status,
            message=message,
            elapsed_s=time.monotonic() - started,
            **kwargs,
        )

    try:
        request = copy.deepcopy(request)
        initial = _validate_request(request)
        problem = _Problem(request, initial)
        if request.rx is not None:
            problem.build_rx(request.rx)
        if request.tx is not None:
            problem.build_tx(request.tx)
        problem.finish()
    except ImportError as exc:
        return outcome(
            "unavailable",
            f"Install docplex and configure IBM CP Optimizer: {exc}",
        )
    except (
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
        IndexError,
        ZeroDivisionError,
    ) as exc:
        return outcome("invalid", str(exc))
    last_rejection = ""
    while True:
        remaining = request.timeout_s - (time.monotonic() - started)
        if remaining <= 0:
            return outcome(
                "timeout",
                "Time limit reached without a validated solution"
                + (f": {last_rejection}" if last_rejection else ""),
            )
        try:
            solution = problem.model.solve(
                TimeLimit=remaining,
                Workers=1,
                LogVerbosity="Quiet",
                WarningLevel=0,
            )
        except Exception as exc:
            text = str(exc)
            if any(
                word in text.lower()
                for word in (
                    "executable",
                    "cpoptimizer",
                    "not found",
                    "license",
                    "solver agent",
                )
            ):
                return outcome(
                    "unavailable",
                    "IBM CP Optimizer is unavailable; install/configure its executable and license. "
                    + text,
                )
            return outcome(
                "invalid", f"CP Optimizer could not solve the model: {text}"
            )
        status = str(solution.get_solve_status())
        if not solution.is_solution():
            if status == "Infeasible":
                details = f": {last_rejection}" if last_rejection else ""
                if not last_rejection:
                    for direction in ("rx", "tx"):
                        plan = getattr(request, direction)
                        if plan is None:
                            continue
                        adapter = get_adapter(plan.part)
                        if (
                            adapter.topology == "mxfe"
                            and getattr(
                                adapter, f"{direction}_coarse_nco_bits", 48
                            )
                            == 32
                        ):
                            fs = (
                                plan.adc_rate_hz
                                if direction == "rx"
                                else plan.dac_rate_hz
                            )
                            details += (
                                f". {direction.upper()} coarse NCO resolution at the current rate is "
                                f"{fs / 2**32:.6g} Hz; unlock fine NCOs or choose a compatible frequency tolerance"
                            )
                return outcome(
                    "infeasible",
                    "No configuration satisfies the requested targets, locks and rate grids"
                    + details,
                )
            return outcome(
                "timeout", "CP Optimizer stopped without a feasible solution"
            )
        try:
            values = problem.read_settings(solution)
            rx, tx = copy.deepcopy(request.rx), copy.deepcopy(request.tx)
            for key, value in values.items():
                _set_value(rx if key.startswith("rx.") else tx, key, value)
            for direction, plan in (("rx", rx), ("tx", tx)):
                if plan is not None:
                    _quantize(
                        plan, direction, request.tolerance_hz, request.automatic
                    )
            modes = {
                d: problem.mode_rows[d][int(solution.get_value(v))][:2]
                for d, v in problem.mode_indices.items()
            }
            throughput, achieved = _validate_candidate(request, rx, tx, modes)
            settings = {}
            if rx is not None:
                settings.update(available_settings(rx, "rx"))
            if tx is not None:
                settings.update(available_settings(tx, "tx"))
            return outcome(
                "optimal" if status == "Optimal" else "feasible",
                "Validated configuration; optimal on the requested grids"
                if status == "Optimal"
                else "Validated configuration; optimality was not proved before stopping",
                rx=rx,
                tx=tx,
                objective_bps=throughput,
                achieved=achieved,
                settings=settings,
                modes=modes,
            )
        except (
            ValueError,
            TypeError,
            AttributeError,
            KeyError,
            IndexError,
            ZeroDivisionError,
        ) as exc:
            last_rejection = str(exc)
            exclusions = [
                var != solution.get_value(var) for var in problem.decisions
            ]
            if not exclusions:
                return outcome("infeasible", last_rejection)
            problem.model.add(problem.model.logical_or(exclusions))
