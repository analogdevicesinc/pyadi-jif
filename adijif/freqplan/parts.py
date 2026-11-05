"""Part adapters describing converter datapaths for frequency planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adijif.converters.ad9084_dp import ad9084_dp_rx, ad9084_dp_tx


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
    """

    name: str
    rx_datapath: Any  # datapath class, e.g. ad9084_dp_rx
    tx_datapath: Any  # datapath class, e.g. ad9084_dp_tx
    num_adcs: int
    num_dacs: int
    default_adc_to_cddc: tuple[int, ...]


ADAPTERS: dict[str, PartAdapter] = {
    "AD9084": PartAdapter(
        name="AD9084",
        rx_datapath=ad9084_dp_rx,
        tx_datapath=ad9084_dp_tx,
        num_adcs=4,
        num_dacs=4,
        default_adc_to_cddc=(0, 1, 2, 3),
    )
}


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
