"""ADRV9009 transceiver clocking model."""
from typing import Dict, List

import numpy as np

from adijif.converters.adrv9009_bf import adrv9009_bf

# References
# https://ez.analog.com/wide-band-rf-transceivers/design-support-adrv9008-1-adrv9008-2-adrv9009/f/q-a/103757/adrv9009-clock-configuration/308013#308013


class adrv9009(adrv9009_bf):
    """ADRV9009 transceiver clocking model.

    This model manage the JESD configuration and input clock constraints.
    External LO constraints are not modeled.

    Clocking: ADRV9009 uses onboard PLLs to generate the JESD clocks

        Lane Rate = I/Q Sample Rate * M * Np * (10 / 8) / L
        Lane Rate = sample_clock * M * Np * (10 / 8) / L
    """

    name = "ADRV9009"

    direct_clocking = False
    available_jesd_modes = ["jesd204b"]
    K_possible = [*np.arange(20, 256, 4)]
    L_possible = [1, 2, 4]
    M_possible = [1, 2, 4]
    N_possible = [12, 14, 16, 24]
    Np_possible = [12, 16, 24]
    F_possible = [1, 2, 4, 8, 16]
    CS_possible = [0]
    CF_possible = [0]
    S_possible = [1]  # Not found in DS
    link_min = 3.6864e9
    link_max = 12.288e9

    max_rx_sample_clock = 250e6
    max_tx_sample_clock = 500e6
    max_obs_sample_clock = 500e6

    # Input clock requirements
    available_input_clock_dividers = [1 / 2, 1, 2, 4, 8, 16]
    input_clock_divider = 1

    device_clock_min = 10e6
    device_clock_max = 1e9

    max_input_clock = 1e9

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by
        get_required_clocks

        Returns:
            List[str]: List of strings of clock names mapped by get_required_clocks
        """
        return ["adrv9009_device_clock", "adrv9009_sysref"]

    def get_required_clocks(self) -> List[Dict]:
        """Generate list of required clocks.

        For ADRV9009 this will contain:
        [device clock requirement SOS, sysref requirement SOS]

        Returns:
            list[dict]: List of dictionaries of solver variables, equations, and constants
        """
        possible_sysrefs = []
        for n in range(1, 20):
            r = self.multiframe_clock / (n * n)
            if r == int(r):
                possible_sysrefs.append(r)

        self.config = {"sysref": self.model.sos1(possible_sysrefs)}
        self.model.Obj(self.config["sysref"])

        possible_device_clocks = []
        for div in self.available_input_clock_dividers:
            dev_clock = self.sample_clock / div
            if self.device_clock_min <= dev_clock <= self.device_clock_max:
                possible_device_clocks.append(dev_clock)

        self.config["device_clock"] = self.model.sos1(possible_device_clocks)
        # self.model.Obj(-1 * self.config["device_clock"])

        return [self.config["device_clock"], self.config["sysref"]]
