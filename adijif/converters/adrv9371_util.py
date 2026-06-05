"""ADRV9371 (AD9371/AD9375 Mykonos) Utility Functions."""

from typing import Dict, Union

from adijif.converters.converter import converter


def _convert_to_config(
    L: Union[int, float],
    M: Union[int, float],
    Np: Union[int, float],
    S: Union[int, float] = 1,
) -> Dict:
    return {
        "L": L,
        "M": M,
        "F": Np / 8 * M * S / L,
        "S": S,
        "HD": (
            1
            if (M == 1 and L == 2 and S == 1)
            or (M == 2 and L == 4 and S == 1)
            or (M == 1 and L == 4 and S == 2)
            else 0
        ),
        "Np": Np,
        "N": Np,
        "CS": 0,
        "CF": 0,
        "K": 32,  # THIS IS A SUGGESTED VALUE
    }


# AD9371 transmit (Tx) JESD204B framer modes. The AD9371 supports up to two
# transmit channels (M up to 2) at Np=16.
quick_configuration_modes_tx = {
    # M = 1
    str(0): _convert_to_config(M=1, L=1, Np=16),
    str(1): _convert_to_config(M=1, L=2, Np=16),
    # M = 2
    str(2): _convert_to_config(M=2, L=1, Np=16),
    str(3): _convert_to_config(M=2, L=2, Np=16),
    str(4): _convert_to_config(M=2, L=4, Np=16),
}


# AD9371 receive (Rx) JESD204B deframer modes. Covers the main Rx path (up to
# two channels) and the observation/sniffer paths.
quick_configuration_modes_rx = {
    # M = 1
    str(0): _convert_to_config(M=1, L=1, S=1, Np=16),
    str(1): _convert_to_config(M=1, L=2, S=1, Np=16),
    # M = 2
    str(2): _convert_to_config(M=2, L=1, S=1, Np=16),
    str(3): _convert_to_config(M=2, L=2, S=1, Np=16),
    str(4): _convert_to_config(M=2, L=4, S=1, Np=16),
    # Np = 12 variants (compressed)
    str(5): _convert_to_config(M=2, L=2, S=1, Np=12),
    str(6): _convert_to_config(M=2, L=4, S=1, Np=12),
}


def _extra_jesd_check(dev: converter) -> None:
    FK = dev.F * dev.K
    assert FK <= 256, "F x K must be <= 256"
    assert FK >= 20, "F x K must be >= 20"
    assert FK % 4 == 0, "F x K must be a multiple of 4"
