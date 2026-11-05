"""Tx stage chain (FDUC, CDUC, DAC) for frequency planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .parts import get_adapter
from .rx import Signal, StageOutput
from .spectrum import Span, duc_stage, wrap_frequency


@dataclass
class TxPlan:
    """Inputs for a Tx frequency plan.

    Attributes:
        part: Part name.
        dac_rate_hz: DAC sample rate in Hz.
        signals: Signals; ``source`` is the FDUC index and ``center_hz``
            the baseband offset.
        datapath: Tx datapath instance.
        cduc_dac_hz: DAC-side NCO frequency of each CDUC, in Hz.
        alpha: Passband fraction of the input Nyquist band.
    """

    part: str
    dac_rate_hz: float
    signals: list[Signal]
    datapath: Any  # adapter.tx_datapath instance, e.g. ad9084_dp_tx
    cduc_dac_hz: list[float]
    alpha: float = 0.8


@dataclass
class TxResult:
    """Result of a Tx plan computation.

    Attributes:
        stages: Stage outputs in insertion order (fduc, cduc, dac).
        warnings: Plan warnings.
    """

    stages: dict[str, StageOutput]
    warnings: list[str]


def _mirror_to_real(spans: list[Span], fs: float) -> list[Span]:
    """Map complex spans onto the real DAC output over [0, fs].

    Negative-frequency parts are mirrored across DC and marked as images.
    Every piece in [0, fs/2] is then mirrored across fs/2 (f -> fs - f)
    into the second Nyquist zone, also marked as an image.

    Args:
        spans: Spans within [-fs/2, fs/2).
        fs: DAC sample rate in Hz.

    Returns:
        Spans covering the first two Nyquist zones.
    """
    first: list[Span] = []
    for sp in spans:
        if sp.hi > 0 or sp.lo >= 0:
            first.append(
                Span(max(sp.lo, 0.0), sp.hi, sp.signal, sp.image, sp.attenuated)
            )
        if sp.lo < 0:
            first.append(
                Span(-min(sp.hi, 0.0), -sp.lo, sp.signal, True, sp.attenuated)
            )
    second = [
        Span(fs - sp.hi, fs - sp.lo, sp.signal, True, sp.attenuated)
        for sp in first
    ]
    return first + second


def _unreachable(sig: Signal, dp: Any) -> str | None:
    """Explain why a signal cannot reach any DAC, if it cannot.

    Blocks are named 0-indexed, as in the diagram (``CDUC0`` is the
    first CDUC). The 1-indexed FDUC source value appears only as a bare
    number, when it is out of range.

    Args:
        sig: Tx signal; ``source`` is its 0-indexed FDUC.
        dp: Tx datapath.

    Returns:
        The first broken link as a warning, or None if the signal
        reaches a DAC.
    """
    f = sig.source
    if not 0 <= f < len(dp.fduc_enabled):
        return f"{sig.name}: FDUC{f} does not exist"
    if not dp.fduc_enabled[f]:
        return f"{sig.name}: FDUC{f} is disabled"
    c = dp.fduc_source[f]
    n_c = len(dp.cduc_enabled)
    if not 1 <= c <= n_c:
        return f"{sig.name}: FDUC{f} source {c} is out of range 1 to {n_c}"
    if not dp.cduc_enabled[c - 1]:
        return f"{sig.name}: CDUC{c - 1} is disabled"
    if not any(c in srcs for srcs in dp.cduc_sources):
        return f"{sig.name}: CDUC{c - 1} is not routed to any DAC"
    return None


def compute_tx(plan: TxPlan) -> TxResult:
    """Compute per-stage spectra for a Tx plan.

    Args:
        plan: The Tx plan.

    Returns:
        Stage outputs and warnings.
    """
    dp = plan.datapath
    fs = plan.dac_rate_hz
    adapter = get_adapter(plan.part)
    ci = dp.cduc_interpolation
    fi = dp.fduc_interpolation
    cduc_in = fs / ci
    fduc_in = fs / (ci * fi)
    stages: dict[str, StageOutput] = {}
    warnings: list[str] = []

    for sig in plan.signals:
        if abs(sig.center_hz) + sig.bandwidth_hz / 2 > (
            plan.alpha * fduc_in / 2
        ):
            warnings.append(f"{sig.name} exceeds FDUC{sig.source} passband")
        why = _unreachable(sig, dp)
        if why:
            warnings.append(why)

    for i, en in enumerate(dp.fduc_enabled):
        if not en:
            continue
        c = dp.fduc_source[i] - 1
        parent = f"cduc{c}"
        rate = fs / ci
        passband = plan.alpha * fduc_in / 2
        if not dp.cduc_enabled[c]:
            stages[f"fduc{i}"] = StageOutput(
                f"fduc{i}",
                "fduc",
                rate,
                passband,
                [],
                parent,
                False,
                error=f"source CDUC{c} is disabled",
            )
            continue
        inputs = [
            Span(
                s.center_hz - s.bandwidth_hz / 2,
                s.center_hz + s.bandwidth_hz / 2,
                s.name,
            )
            for s in plan.signals
            if s.source == i
        ]
        spans = duc_stage(
            inputs, fduc_in, fi, dp.fduc_nco_frequencies[i], plan.alpha
        )
        stages[f"fduc{i}"] = StageOutput(
            f"fduc{i}", "fduc", rate, passband, spans, parent, False
        )

    for c, en in enumerate(dp.cduc_enabled):
        if not en:
            continue
        merged: list[Span] = []
        for i in range(len(dp.fduc_enabled)):
            if dp.fduc_source[i] - 1 == c and f"fduc{i}" in stages:
                merged.extend(stages[f"fduc{i}"].spans)
        spans = duc_stage(
            merged,
            cduc_in,
            ci,
            wrap_frequency(plan.cduc_dac_hz[c], fs),
            plan.alpha,
        )
        stages[f"cduc{c}"] = StageOutput(
            f"cduc{c}",
            "cduc",
            fs,
            plan.alpha * cduc_in / 2,
            spans,
            None,
            False,
        )

    for j in range(adapter.num_dacs):
        merged = []
        for c in dp.cduc_sources[j]:
            st = stages.get(f"cduc{c - 1}")
            if st is not None:
                merged.extend(st.spans)
        stages[f"dac{j}"] = StageOutput(
            f"dac{j}",
            "dac",
            fs,
            fs / 2,
            _mirror_to_real(merged, fs),
            None,
            True,
        )

    return TxResult(stages, warnings)


def default_tx_plan() -> TxPlan:
    """Build the default AD9084 Tx plan at 20 GSPS.

    Returns:
        A fresh default plan.
    """
    adapter = get_adapter("AD9084")
    dp = adapter.tx_datapath()
    dp.cduc_interpolation = 4
    dp.fduc_interpolation = 2
    dp.fduc_enabled = [True, False, False, False, True, False, False, False]
    dp.fduc_nco_frequencies = [0] * 8
    return TxPlan(
        part="AD9084",
        dac_rate_hz=20e9,
        signals=[
            Signal("S1", 0, 400e6, 0),
            Signal("S2", 0, 100e6, 4),
        ],
        datapath=dp,
        cduc_dac_hz=[3e9, 0, 6e9, 0],
    )
