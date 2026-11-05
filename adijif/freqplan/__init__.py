"""Streamlit-free frequency planning for converter DDC/DUC chains."""

from .adc import (
    adc_spectrum,
    fold_to_first_nyquist,
    nyquist_zone,
    rf_to_nco,
    straddles_nyquist,
)
from .checks import (
    Interference,
    SignalCapture,
    Verdict,
    evaluate_dac,
    evaluate_output,
)
from .parts import ADAPTERS, PartAdapter, get_adapter
from .rx import (
    RxPlan,
    RxResult,
    Signal,
    StageOutput,
    compute_rx,
    default_rx_plan,
    rx_plan_warnings,
)
from .spectrum import (
    Span,
    ddc_stage,
    duc_stage,
    shift_spans,
    spans_mhz,
    wrap_frequency,
    wrap_spans,
)

__all__ = [
    "ADAPTERS",
    "Interference",
    "SignalCapture",
    "Verdict",
    "evaluate_dac",
    "evaluate_output",
    "PartAdapter",
    "RxPlan",
    "RxResult",
    "Signal",
    "StageOutput",
    "compute_rx",
    "default_rx_plan",
    "get_adapter",
    "rx_plan_warnings",
    "Span",
    "adc_spectrum",
    "ddc_stage",
    "duc_stage",
    "fold_to_first_nyquist",
    "nyquist_zone",
    "rf_to_nco",
    "shift_spans",
    "spans_mhz",
    "straddles_nyquist",
    "wrap_frequency",
    "wrap_spans",
]
