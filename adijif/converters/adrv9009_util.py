"""ADRV9009 Utility Functions."""

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


quick_configuration_modes_tx = {
    # M = 1
    str(0): _convert_to_config(M=1, L=1, Np=16),
    str(1): _convert_to_config(M=1, L=2, Np=16),
    # M = 2
    str(2): _convert_to_config(M=2, L=1, Np=16),
    str(3): _convert_to_config(M=2, L=2, Np=16),
    str(4): _convert_to_config(M=2, L=4, Np=16),
    # M = 4
    str(5): _convert_to_config(M=4, L=1, Np=16),
    str(6): _convert_to_config(M=4, L=2, Np=16),
    str(7): _convert_to_config(M=4, L=4, Np=16),
    str(8): _convert_to_config(M=4, L=2, Np=12),
}


quick_configuration_modes_rx = {
    # M = 1
    str(0): _convert_to_config(M=1, L=1, S=1, Np=16),
    str(1): _convert_to_config(M=1, L=1, S=2, Np=16),
    str(2): _convert_to_config(M=1, L=1, S=4, Np=16),
    str(3): _convert_to_config(M=1, L=2, S=1, Np=16),
    str(4): _convert_to_config(M=1, L=2, S=2, Np=16),
    str(5): _convert_to_config(M=1, L=2, S=4, Np=16),
    str(6): _convert_to_config(M=1, L=4, S=2, Np=16),
    str(7): _convert_to_config(M=1, L=4, S=4, Np=16),
    # M = 2
    str(8): _convert_to_config(M=2, L=1, S=1, Np=16),
    str(9): _convert_to_config(M=2, L=1, S=2, Np=16),
    str(10): _convert_to_config(M=2, L=2, S=1, Np=16),
    str(11): _convert_to_config(M=2, L=2, S=2, Np=16),
    str(12): _convert_to_config(M=2, L=2, S=4, Np=16),
    str(13): _convert_to_config(M=2, L=4, S=1, Np=16),
    str(14): _convert_to_config(M=2, L=4, S=2, Np=16),
    str(15): _convert_to_config(M=2, L=4, S=4, Np=16),
    # M = 4
    str(16): _convert_to_config(M=4, L=1, S=1, Np=16),
    str(17): _convert_to_config(M=4, L=2, S=1, Np=16),
    str(18): _convert_to_config(M=4, L=2, S=2, Np=16),
    str(19): _convert_to_config(M=4, L=4, S=1, Np=16),
    str(20): _convert_to_config(M=4, L=4, S=2, Np=16),
    str(21): _convert_to_config(M=4, L=4, S=4, Np=16),
    # Np = 12,24
    str(22): _convert_to_config(M=2, L=1, S=2, Np=12),
    str(23): _convert_to_config(M=4, L=1, S=1, Np=12),
    str(24): _convert_to_config(M=4, L=2, S=1, Np=12),
    str(25): _convert_to_config(M=2, L=2, S=2, Np=24),
    str(26): _convert_to_config(M=4, L=2, S=1, Np=24),
}


def _extra_jesd_check(dev: converter) -> None:
    FK = dev.F * dev.K
    assert FK <= 256, "F x K must be <= 256"
    assert FK >= 20, "F x K must be >= 20"
    assert FK % 4 == 0, "F x K must be a multiple of 4"
