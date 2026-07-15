"""ADRV9009 Utility Functions."""

import os
import re
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


def parse_adrv9009_profile(profile_path: str) -> dict:
    """Parse ADRV9009 profile file and extract configuration settings.

    Args:
        profile_path (str): Path to the profile text file.

    Returns:
        dict: A dictionary containing parsed configuration data.

    Raises:
        FileNotFoundError: If the profile file does not exist.
    """
    if not os.path.exists(profile_path):
        raise FileNotFoundError(f"Profile file not found: {profile_path}")

    with open(profile_path, "r") as f:
        content = f.read()

    clocks_match = re.search(
        r"<clocks>(.*?)</clocks>", content, re.DOTALL | re.IGNORECASE
    )
    rx_match = re.search(
        r"<rx\b[^>]*>(.*?)</rx>", content, re.DOTALL | re.IGNORECASE
    )
    tx_match = re.search(
        r"<tx\b[^>]*>(.*?)</tx>", content, re.DOTALL | re.IGNORECASE
    )

    profile_data = {"clocks": {}, "rx": {}, "tx": {}}

    def parse_section(body: str) -> dict:
        data = {}
        for line in body.splitlines():
            line = line.strip()
            match = re.match(r"^<([a-zA-Z0-9_]+)\s*=\s*([^>]+)>", line)
            if match:
                k, v = match.groups()
                try:
                    if "." in v:
                        data[k] = float(v)
                    else:
                        data[k] = int(v)
                except ValueError:
                    data[k] = v
        return data

    if clocks_match:
        profile_data["clocks"] = parse_section(clocks_match.group(1))
    if rx_match:
        profile_data["rx"] = parse_section(rx_match.group(1))
    if tx_match:
        profile_data["tx"] = parse_section(tx_match.group(1))

    return profile_data
