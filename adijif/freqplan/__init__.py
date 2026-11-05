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
from .config import CONFIG_VERSION, dumps, loads, plan_from_dict, plan_to_dict
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
from .tx import TxPlan, TxResult, compute_tx, default_tx_plan

__all__ = [
    "ADAPTERS",
    "CONFIG_VERSION",
    "Interference",
    "PartAdapter",
    "RxPlan",
    "RxResult",
    "Signal",
    "SignalCapture",
    "Span",
    "StageOutput",
    "TxPlan",
    "TxResult",
    "Verdict",
    "adc_spectrum",
    "compute_rx",
    "compute_tx",
    "ddc_stage",
    "default_rx_plan",
    "default_tx_plan",
    "duc_stage",
    "dumps",
    "evaluate_dac",
    "evaluate_output",
    "fold_to_first_nyquist",
    "get_adapter",
    "loads",
    "nyquist_zone",
    "plan_from_dict",
    "plan_to_dict",
    "rf_to_nco",
    "rx_plan_warnings",
    "shift_spans",
    "spans_mhz",
    "straddles_nyquist",
    "wrap_frequency",
    "wrap_spans",
]
