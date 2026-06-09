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


# AD9371 transmit (Tx) JESD204B framer modes. The AD9371 has two transmitters;
# JESD204 counts the I and Q rails of each complex channel as separate
# converters, so the two Tx channels present as M=4 (the framing used by the
# Kuiper zynq-zc706-adv7511-adrv937x reference: M=4 L=4 Np=16 -> F=2). M=1/2
# modes cover single-channel / real-only configurations.
quick_configuration_modes_tx = {
    # M = 1
    str(0): _convert_to_config(M=1, L=1, Np=16),
    str(1): _convert_to_config(M=1, L=2, Np=16),
    # M = 2
    str(2): _convert_to_config(M=2, L=1, Np=16),
    str(3): _convert_to_config(M=2, L=2, Np=16),
    str(4): _convert_to_config(M=2, L=4, Np=16),
    # M = 4 (two complex Tx channels, I+Q)
    str(5): _convert_to_config(M=4, L=2, Np=16),  # F=4
    str(6): _convert_to_config(M=4, L=4, Np=16),  # F=2 (zc706 reference)
}


# AD9371 receive (Rx) JESD204B deframer modes. Like Tx, JESD204 counts the I/Q
# rails of each complex channel separately, so the two main Rx channels present
# as M=4 (the Kuiper zynq-zc706-adv7511-adrv937x reference main-Rx framing:
# M=4 L=2 Np=16 -> F=4). The observation/sniffer path runs as M=2 (mode "3").
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
    # M = 4 (two complex Rx channels, I+Q)
    str(7): _convert_to_config(M=4, L=2, S=1, Np=16),  # F=4 (zc706 reference)
    str(8): _convert_to_config(M=4, L=4, S=1, Np=16),  # F=2
}


def _extra_jesd_check(dev: converter) -> None:
    FK = dev.F * dev.K
    assert FK <= 256, "F x K must be <= 256"
    assert FK >= 20, "F x K must be >= 20"
    assert FK % 4 == 0, "F x K must be a multiple of 4"
