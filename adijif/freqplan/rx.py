"""Rx stage chain (ADC, CDDC, FDDC) for frequency planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .adc import adc_spectrum, rf_to_nco, straddles_nyquist
from .parts import get_adapter
from .spectrum import Span, ddc_stage


@dataclass
class Signal:
    """A signal of interest.

    Attributes:
        name: Signal name.
        center_hz: Center frequency in Hz.
        bandwidth_hz: Bandwidth in Hz.
        source: 0-indexed ADC for Rx, or FDUC for Tx.
    """

    name: str
    center_hz: float
    bandwidth_hz: float
    source: int


@dataclass
class RxPlan:
    """Inputs for an Rx frequency plan.

    Attributes:
        part: Part name.
        adc_rate_hz: ADC sample rate in Hz.
        signals: Signals of interest.
        datapath: Rx datapath instance.
        cddc_rf_hz: RF frequency each CDDC NCO targets, in Hz.
        adc_to_cddc: ADC index feeding each CDDC.
        targets: Output channel name to signal names.
        alpha: Passband fraction of the output Nyquist band.
    """

    part: str
    adc_rate_hz: float
    signals: list[Signal]
    datapath: Any  # adapter.rx_datapath instance, e.g. ad9084_dp_rx
    cddc_rf_hz: list[float]
    adc_to_cddc: list[int]
    targets: dict[str, list[str]] = field(default_factory=dict)
    alpha: float = 0.8


@dataclass
class StageOutput:
    """Spectrum at the output of one stage.

    Attributes:
        channel: Stage name, e.g. ``"cddc0"``.
        kind: One of adc, cddc, fddc, fduc, cduc, dac.
        rate_hz: Sample rate at the stage output in Hz.
        passband_hz: Passband edge in Hz.
        spans: Output spans.
        parent: Name of the feeding stage, if any.
        is_output: True if the stage is a final output.
        error: Error message if the stage could not be computed.
    """

    channel: str
    kind: str
    rate_hz: float
    passband_hz: float
    spans: list[Span]
    parent: str | None
    is_output: bool
    error: str | None = None


@dataclass
class RxResult:
    """Result of an Rx plan computation.

    Attributes:
        stages: Stage outputs in insertion order (adc, cddc, fddc).
        warnings: Plan warnings.
    """

    stages: dict[str, StageOutput]
    warnings: list[str]


def rx_plan_warnings(plan: RxPlan) -> list[str]:
    """Return Nyquist-related warnings for an Rx plan.

    Args:
        plan: The Rx plan.

    Returns:
        Warning strings.
    """
    out: list[str] = []
    for sig in plan.signals:
        if straddles_nyquist(sig.center_hz, sig.bandwidth_hz, plan.adc_rate_hz):
            out.append(f"{sig.name} straddles a Nyquist boundary")
    dp = plan.datapath
    adapter = get_adapter(plan.part)
    for a in range(adapter.num_adcs):
        zones = {
            rf_to_nco(plan.cddc_rf_hz[i], plan.adc_rate_hz)[1]
            for i, en in enumerate(dp.cddc_enabled)
            if en and plan.adc_to_cddc[i] == a
        }
        if len(zones) > 1:
            out.append(
                f"ADC{a} CDDCs target different Nyquist zones {sorted(zones)}"
            )
    return out


def compute_rx(plan: RxPlan) -> RxResult:
    """Compute per-stage spectra for an Rx plan.

    Args:
        plan: The Rx plan.

    Returns:
        Stage outputs and warnings.
    """
    dp = plan.datapath
    fs = plan.adc_rate_hz
    adapter = get_adapter(plan.part)
    stages: dict[str, StageOutput] = {}

    for a in range(adapter.num_adcs):
        bands = [
            (s.name, s.center_hz, s.bandwidth_hz)
            for s in plan.signals
            if s.source == a
        ]
        stages[f"adc{a}"] = StageOutput(
            f"adc{a}", "adc", fs, fs / 2, adc_spectrum(bands, fs), None, False
        )

    for i, en in enumerate(dp.cddc_enabled):
        if not en:
            continue
        a = plan.adc_to_cddc[i]
        dec = dp.cddc_decimations[i]
        nco = rf_to_nco(plan.cddc_rf_hz[i], fs)[0]
        rate = fs / dec
        spans = ddc_stage(stages[f"adc{a}"].spans, fs, nco, dec, plan.alpha)
        stages[f"cddc{i}"] = StageOutput(
            f"cddc{i}",
            "cddc",
            rate,
            plan.alpha * rate / 2,
            spans,
            f"adc{a}",
            True,
        )

    for j, en in enumerate(dp.fddc_enabled):
        if not en:
            continue
        c = dp.fddc_source[j] - 1
        parent = stages.get(f"cddc{c}")
        if parent is None:
            stages[f"fddc{j}"] = StageOutput(
                f"fddc{j}",
                "fddc",
                0.0,
                0.0,
                [],
                f"cddc{c}",
                True,
                error=f"source CDDC{c + 1} is disabled",
            )
            continue
        parent.is_output = False
        dec = dp.fddc_decimations[j]
        rate = parent.rate_hz / dec
        spans = ddc_stage(
            parent.spans,
            parent.rate_hz,
            dp.fddc_nco_frequencies[j],
            dec,
            plan.alpha,
        )
        stages[f"fddc{j}"] = StageOutput(
            f"fddc{j}",
            "fddc",
            rate,
            plan.alpha * rate / 2,
            spans,
            f"cddc{c}",
            True,
        )

    return RxResult(stages, rx_plan_warnings(plan))


def default_rx_plan() -> RxPlan:
    """Build the default AD9084 Rx plan at 20 GSPS.

    Returns:
        A fresh default plan.
    """
    adapter = get_adapter("AD9084")
    dp = adapter.rx_datapath()
    dp.cddc_enabled = [True] * 4
    dp.cddc_decimations = [4, 4, 4, 4]
    dp.fddc_enabled = [True, False, True, False, True, False, True, False]
    dp.fddc_decimations = [4, 1, 8, 1, 2, 1, 8, 1]
    dp.fddc_nco_frequencies = [0] * 8
    return RxPlan(
        part="AD9084",
        adc_rate_hz=20e9,
        signals=[
            Signal("S1", 1.2e9, 400e6, 0),
            Signal("S2", 2.0e9, 100e6, 1),
            Signal("S3", 5.5e9, 800e6, 2),
            Signal("S4", 7.8e9, 200e6, 3),
        ],
        datapath=dp,
        cddc_rf_hz=[1.2e9, 2.0e9, 5.5e9, 7.8e9],
        adc_to_cddc=list(adapter.default_adc_to_cddc),
        targets={
            "fddc0": ["S1"],
            "fddc2": ["S2"],
            "fddc4": ["S3"],
            "fddc6": ["S4"],
        },
    )
