"""Scalar filter-chain models for standalone converters and transceivers.

These deliberately describe only the modeled modes: AD9680 uses one DDC
per ADC (or real bypass), AD9144/AD9152 use real interpolation without
modulation, and transceivers use a shared analog LO plus a complex filter
chain. They do not pretend these parts contain MxFE coarse/fine stages.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any

from .adc import adc_spectrum
from .spectrum import Span, ddc_stage, duc_stage, shift_spans, wrap_spans


@dataclass
class SimpleDatapath:
    """Independent channel enables and a shared scalar rate-change factor.

    ``nco_hz`` is empty when the modeled path has no digital mixer.
    ``profile_constraints`` optionally locks ``converter_rate_hz``,
    ``sample_rate_hz``, ``factor`` and ``lo_hz`` from an imported profile.
    """

    factor: int = 1
    enabled: list[bool] = field(default_factory=list)
    nco_hz: list[float] = field(default_factory=list)
    lo_hz: float = 0.0
    profile_constraints: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, channels: int, nco: bool = False) -> SimpleDatapath:
        """Create private mutable settings for a part's physical channels."""
        return cls(
            enabled=[True] * channels, nco_hz=[0.0] * channels if nco else []
        )

    def get_config(self) -> dict[str, Any]:
        """Return JSON-compatible settings without shared mutable objects."""
        return copy.deepcopy(self.__dict__)


def validate_simple(plan: Any, direction: str) -> None:
    """Check shape and finite numeric inputs before spectrum arithmetic.

    Physical rate limits remain visible through JESD/device validation so
    manual editing can show spectra for an out-of-range rate.
    """
    from .parts import get_adapter

    a = get_adapter(plan.part)
    dp = plan.datapath
    if direction not in a.directions:
        raise ValueError(f"{plan.part} does not support {direction.title()}")
    n = a.num_adcs if direction == "rx" else a.num_dacs
    if not isinstance(dp, SimpleDatapath):
        raise ValueError("Expected a scalar datapath")
    if len(dp.enabled) != n or any(type(v) is not bool for v in dp.enabled):
        raise ValueError(f"Expected {n} channel enable booleans")
    if type(dp.factor) is not int or dp.factor not in getattr(
        a, f"{direction}_factors"
    ):
        raise ValueError(
            f"Unsupported {direction} rate-change factor {dp.factor}"
        )
    bits = getattr(a, f"{direction}_nco_bits")
    if len(dp.nco_hz) != (n if bits else 0):
        raise ValueError("NCO settings do not match this part's capabilities")
    fs = plan.adc_rate_hz if direction == "rx" else plan.dac_rate_hz
    if not math.isfinite(fs) or fs <= 0:
        raise ValueError("Converter rate must be finite and positive")
    if not math.isfinite(plan.alpha) or not 0 < plan.alpha <= 1:
        raise ValueError("Passband fraction must be in (0, 1]")
    if any(not math.isfinite(f) or abs(f) > fs / 2 for f in dp.nco_hz):
        raise ValueError("NCO frequency is outside the sampled Nyquist band")
    if a.topology == "adc" and dp.factor == 1 and any(dp.nco_hz):
        raise ValueError("Real bypass at decimation 1 requires zero NCO")
    if not math.isfinite(dp.lo_hz):
        raise ValueError("LO frequency must be finite")
    if a.lo_bounds_hz:
        if not a.lo_bounds_hz[0] <= dp.lo_hz <= a.lo_bounds_hz[1]:
            raise ValueError("LO frequency is outside the device tuning range")
    elif dp.lo_hz != 0:
        raise ValueError("This part does not have an analog LO")
    names = set()
    for s in plan.signals:
        if not s.name or s.name in names:
            raise ValueError("Signal names must be nonempty and unique")
        names.add(s.name)
        if type(s.source) is not int or not 0 <= s.source < n:
            raise ValueError(f"Signal {s.name}: source must be in 0..{n - 1}")
        if (
            not math.isfinite(s.center_hz)
            or not math.isfinite(s.bandwidth_hz)
            or s.bandwidth_hz < 0
        ):
            raise ValueError(
                "Signal frequencies must be finite; bandwidth must be nonnegative"
            )
    known = {"converter_rate_hz", "sample_rate_hz", "factor", "lo_hz"}
    if (
        not isinstance(dp.profile_constraints, dict)
        or set(dp.profile_constraints) - known
    ):
        raise ValueError("Unknown profile constraint")
    actual = {
        "converter_rate_hz": fs,
        "sample_rate_hz": fs / dp.factor,
        "factor": dp.factor,
        "lo_hz": dp.lo_hz,
    }
    profile_rates = a.profile_rate_factors(direction)
    if profile_rates and not any(
        math.isclose(actual["sample_rate_hz"], rate, rel_tol=1e-12)
        and dp.factor == factor
        for rate, factor in profile_rates.items()
    ):
        raise ValueError(
            f"Unsupported {plan.part} {direction} profile rate/factor pair"
        )
    for key, value in dp.profile_constraints.items():
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"Invalid profile constraint {key}")
        if not math.isclose(actual[key], value, rel_tol=1e-12, abs_tol=1e-6):
            raise ValueError(
                f"{key} conflicts with imported profile constraint"
            )


def compute_simple_rx(plan: Any) -> Any:
    """Compute either real ADC sampling or complex LO downconversion."""
    from .parts import get_adapter
    from .rx import RxResult, StageOutput

    validate_simple(plan, "rx")
    a, dp, fs = get_adapter(plan.part), plan.datapath, plan.adc_rate_hz
    stages = {}
    warnings = []
    for i, enabled in enumerate(dp.enabled):
        signals = [s for s in plan.signals if s.source == i]
        bands = [(s.name, s.center_hz, s.bandwidth_hz) for s in signals]
        if a.topology == "transceiver":
            rf = [Span(c - bw / 2, c + bw / 2, name) for name, c, bw in bands]
            stages[f"input{i}"] = StageOutput(
                f"input{i}", "rf", fs, fs / 2, rf, None, False
            )
            spans = wrap_spans(shift_spans(rf, -dp.lo_hz), fs)
            for s in signals:
                if abs(s.center_hz - dp.lo_hz) + s.bandwidth_hz / 2 > fs / 2:
                    warnings.append(
                        f"{s.name} exceeds the analog baseband Nyquist band"
                    )
        else:
            spans = adc_spectrum(bands, fs)
        stages[f"adc{i}"] = StageOutput(
            f"adc{i}", "adc", fs, fs / 2, spans, None, False
        )
        if not enabled:
            continue
        out = ddc_stage(
            spans, fs, dp.nco_hz[i] if dp.nco_hz else 0, dp.factor, plan.alpha
        )
        stages[f"ddc{i}"] = StageOutput(
            f"ddc{i}",
            "ddc",
            fs / dp.factor,
            plan.alpha * fs / dp.factor / 2,
            out,
            f"adc{i}",
            True,
        )
    return RxResult(stages, warnings)


def compute_simple_tx(plan: Any) -> Any:
    """Compute real interpolation or complex interpolation and RF mixing."""
    from .parts import get_adapter
    from .rx import StageOutput
    from .tx import TxResult, _mirror_to_real

    validate_simple(plan, "tx")
    a, dp, fs = get_adapter(plan.part), plan.datapath, plan.dac_rate_hz
    rate = fs / dp.factor
    stages, warnings = {}, []
    for i, enabled in enumerate(dp.enabled):
        if not enabled:
            continue
        signals = [s for s in plan.signals if s.source == i]
        spans = [
            Span(
                s.center_hz - s.bandwidth_hz / 2,
                s.center_hz + s.bandwidth_hz / 2,
                s.name,
            )
            for s in signals
        ]
        for s in signals:
            if abs(s.center_hz) + s.bandwidth_hz / 2 > plan.alpha * rate / 2:
                warnings.append(f"{s.name} exceeds channel {i} input passband")
        stages[f"input{i}"] = StageOutput(
            f"input{i}",
            "input",
            rate,
            plan.alpha * rate / 2,
            spans,
            None,
            False,
        )
        out = duc_stage(spans, rate, dp.factor, 0, plan.alpha)
        stages[f"interpolator{i}"] = StageOutput(
            f"interpolator{i}",
            "interpolator",
            fs,
            plan.alpha * rate / 2,
            out,
            f"input{i}",
            False,
        )
        rf = a.topology == "transceiver"
        out = shift_spans(out, dp.lo_hz) if rf else _mirror_to_real(out, fs)
        stages[f"dac{i}"] = StageOutput(
            f"dac{i}",
            "rf" if rf else "dac",
            fs,
            fs / 2,
            out,
            f"interpolator{i}",
            True,
        )
    return TxResult(stages, warnings)
