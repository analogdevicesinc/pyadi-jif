"""Part adapters describing converter datapaths for frequency planning."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Any

from adijif.converters.ad9081 import ad9081_rx, ad9081_tx, ad9082_rx, ad9082_tx
from adijif.converters.ad9081_dp import ad9081_dp_rx, ad9081_dp_tx
from adijif.converters.ad9084 import ad9084_rx, ad9084_tx, ad9088_rx, ad9088_tx
from adijif.converters.ad9084_dp import ad9084_dp_rx, ad9084_dp_tx
from adijif.converters.ad9088_dp import ad9088_dp_rx
from adijif.converters.ad9144 import ad9144
from adijif.converters.ad9152 import ad9152
from adijif.converters.ad9371 import ad9371_obs, ad9371_rx, ad9371_tx
from adijif.converters.ad9680 import ad9680
from adijif.converters.adrv9009 import adrv9009_rx, adrv9009_tx
from adijif.converters.adrv9371 import adrv9371_rx, adrv9371_tx

from .simple import SimpleDatapath


class _AD9081Tx(ad9081_dp_tx):
    """Normalize the older model's spelling and add its fixed FDUC mapping."""

    cduc_interpolation_available = ad9081_dp_tx.cduc_interpolations_available
    fduc_interpolation_available = ad9081_dp_tx.fduc_interpolations_available
    fduc_source = [1, 1, 2, 2, 3, 3, 4, 4]

    def __init__(self) -> None:
        super().__init__()
        self.fduc_source = list(type(self).fduc_source)


class _AD9088Tx(ad9084_dp_tx):
    """Octal TX DSP (AD9088 Rev A, Theory of Operation, p. 42).

    The core clock model currently instantiates the quad AD9084 datapath.
    Keep this correction local to the planner until that model is updated.
    """

    cduc_enabled = [True] * 8
    cduc_nco_frequencies = [0] * 8
    cduc_nco_phases = [0] * 8
    fduc_enabled = [False] * 16
    fduc_nco_frequencies = [0] * 16
    fduc_nco_phases = [0] * 16
    fduc_source = [i // 2 + 1 for i in range(16)]
    cduc_sources = [[i + 1] for i in range(8)]


@dataclass(frozen=True)
class PartAdapter:
    """Static description of a converter part.

    Attributes:
        name: Part name.
        rx_datapath: Rx datapath class.
        tx_datapath: Tx datapath class.
        num_adcs: Number of ADCs.
        num_dacs: Number of DACs.
        default_adc_to_cddc: Default ADC index feeding each CDDC.
        rx_converter: Rx converter model class (JESD204 mode tables).
        tx_converter: Tx converter model class (JESD204 mode tables).
    """

    name: str
    rx_datapath: Any  # datapath class, e.g. ad9084_dp_rx
    tx_datapath: Any  # datapath class, e.g. ad9084_dp_tx
    num_adcs: int
    num_dacs: int
    default_adc_to_cddc: tuple[int, ...]
    rx_converter: Any = None  # converter class, e.g. ad9084_rx
    tx_converter: Any = None  # converter class, e.g. ad9084_tx
    topology: str = "mxfe"
    rx_factors: tuple[int, ...] = ()
    tx_factors: tuple[int, ...] = ()
    rx_nco_bits: int | None = 48
    tx_nco_bits: int | None = 48
    lo_bounds_hz: tuple[float, float] | None = None
    rx_complex: bool = True
    tx_complex: bool = True
    notes: str = ""
    rx_coarse_nco_bits: int = 48
    tx_coarse_nco_bits: int = 48
    rx_fine_rate_max_hz: float | None = None
    tx_fine_rate_max_hz: float | None = None

    @property
    def directions(self) -> tuple[str, ...]:
        """Directions with an implemented planner datapath."""
        return tuple(d for d in ("rx", "tx") if getattr(self, f"{d}_datapath"))

    @property
    def rx_rate_bounds_hz(self) -> tuple[float, float]:
        """Physical ADC sampling-rate limits, distinct from JESD rates."""
        if self.rx_converter is None:
            return (0.0, 0.0)
        return (
            self.rx_converter.converter_clock_min,
            self.rx_converter.converter_clock_max,
        )

    @property
    def tx_rate_bounds_hz(self) -> tuple[float, float]:
        """Physical DAC sampling-rate limits, distinct from JESD rates."""
        if self.tx_converter is None:
            return (0.0, 0.0)
        return (
            self.tx_converter.converter_clock_min,
            self.tx_converter.converter_clock_max,
        )

    def profile_rate_factors(self, direction: str) -> dict[int, int]:
        """Supported AD9371 rate/factor pairs from the existing profile parser."""
        from adijif.converters.ad9371 import (
            _OBS_FACTORS,
            _RX_FACTORS,
            _TX_FACTORS,
        )

        if self.name == "AD9371_OBS":
            return dict(_OBS_FACTORS)
        if self.name == "AD9371":
            return dict(_RX_FACTORS if direction == "rx" else _TX_FACTORS)
        return {}


ADAPTERS: dict[str, PartAdapter] = {
    "AD9084": PartAdapter(
        name="AD9084",
        rx_datapath=ad9084_dp_rx,
        tx_datapath=ad9084_dp_tx,
        num_adcs=4,
        num_dacs=4,
        default_adc_to_cddc=(0, 1, 2, 3),
        rx_converter=ad9084_rx,
        tx_converter=ad9084_tx,
        rx_coarse_nco_bits=32,
        tx_coarse_nco_bits=32,
        rx_fine_rate_max_hz=5e9,
        tx_fine_rate_max_hz=5e9,
    )
}

ADAPTERS.update(
    {
        "AD9081": PartAdapter(
            "AD9081",
            ad9081_dp_rx,
            _AD9081Tx,
            4,
            4,
            (0, 1, 2, 3),
            ad9081_rx,
            ad9081_tx,
            rx_fine_rate_max_hz=1.5e9,
            tx_fine_rate_max_hz=1.5e9,
        ),
        "AD9082": PartAdapter(
            "AD9082",
            ad9081_dp_rx,
            _AD9081Tx,
            2,
            4,
            (0, 0, 1, 1),
            ad9082_rx,
            ad9082_tx,
            rx_fine_rate_max_hz=1.5e9,
            tx_fine_rate_max_hz=1.5e9,
        ),
        "AD9088": PartAdapter(
            "AD9088",
            ad9088_dp_rx,
            _AD9088Tx,
            8,
            8,
            tuple(range(8)),
            ad9088_rx,
            ad9088_tx,
            rx_coarse_nco_bits=32,
            tx_coarse_nco_bits=32,
            rx_fine_rate_max_hz=2.5e9,
            tx_fine_rate_max_hz=2.5e9,
        ),
    }
)


def _simple_adapter(
    name: str,
    rx: Any,
    tx: Any,
    topology: str,
    n_rx: int,
    n_tx: int,
    lo: tuple[float, float] | None = None,
    rx_nco_bits: int | None = None,
) -> PartAdapter:
    return PartAdapter(
        name,
        partial(SimpleDatapath.create, n_rx, rx_nco_bits is not None)
        if rx
        else None,
        partial(SimpleDatapath.create, n_tx, False) if tx else None,
        n_rx,
        n_tx,
        (),
        rx,
        tx,
        topology,
        tuple(rx.decimation_available) if rx else (),
        tuple(tx.interpolation_available) if tx else (),
        rx_nco_bits,
        None,
        lo,
        topology != "adc",
        topology != "dac",
        "One DDC per ADC; real bypass at decimation 1."
        if topology == "adc"
        else "Real interpolation path; digital modulation modes are not modeled."
        if topology == "dac"
        else "Ideal complex filter chain; hardware profile generation and external LO synthesis are not modeled.",
    )


# LO limits: AD9371 Rev E / ADRV9009 Rev B feature tables. ADRV9371 is
# the repository's AD9371 legacy model. AD9680 Rev D p.56 specifies a
# 12-bit frequency tuning word (not the 48-bit word used by the MxFEs).
ADAPTERS.update(
    {
        "AD9680": _simple_adapter(
            "AD9680", ad9680, None, "adc", 2, 0, rx_nco_bits=12
        ),
        "AD9144": _simple_adapter("AD9144", None, ad9144, "dac", 0, 4),
        "AD9152": _simple_adapter("AD9152", None, ad9152, "dac", 0, 2),
        "AD9371": _simple_adapter(
            "AD9371", ad9371_rx, ad9371_tx, "transceiver", 2, 2, (300e6, 6e9)
        ),
        "AD9371_OBS": _simple_adapter(
            "AD9371_OBS", ad9371_obs, None, "transceiver", 2, 0, (300e6, 6e9)
        ),
        "ADRV9371": _simple_adapter(
            "ADRV9371",
            adrv9371_rx,
            adrv9371_tx,
            "transceiver",
            2,
            2,
            (300e6, 6e9),
        ),
        "ADRV9009": _simple_adapter(
            "ADRV9009",
            adrv9009_rx,
            adrv9009_tx,
            "transceiver",
            2,
            2,
            (75e6, 6e9),
        ),
    }
)


def get_adapter(part: str) -> PartAdapter:
    """Look up a part adapter by name.

    Args:
        part: Part name, e.g. ``"AD9084"``.

    Returns:
        The matching adapter.

    Raises:
        ValueError: If the part is not supported.
    """
    try:
        return ADAPTERS[part]
    except KeyError:
        raise ValueError(
            f"Unsupported part {part!r}; supported: {sorted(ADAPTERS)}"
        ) from None
