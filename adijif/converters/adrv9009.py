"""ADRV9009 transceiver clocking model."""
from abc import ABCMeta
from typing import Dict, List, Union

import numpy as np

from adijif.common import core
from adijif.converters.adrv9009_bf import adrv9009_bf
from adijif.gekko_trans import gekko_translation

from ..solvers import GEKKO, CpoModel  # type: ignore
from .adrv9009_util import (_extra_jesd_check, quick_configuration_modes_rx,
                            quick_configuration_modes_tx)
from .converter import converter

# References
# https://ez.analog.com/wide-band-rf-transceivers/design-support-adrv9008-1-adrv9008-2-adrv9009/f/q-a/103757/adrv9009-clock-configuration/308013#308013


class adrv9009_core(metaclass=ABCMeta):
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

    max_rx_sample_clock = 250e6
    max_tx_sample_clock = 500e6
    max_obs_sample_clock = 500e6

    converter_clock_min = 39.063e6 * 8
    converter_clock_max = 491520000

    sample_clock_min = 39.063e6
    sample_clock_max = 491520000

    # Input clock requirements
    available_input_clock_dividers = [1 / 2, 1, 2, 4, 8, 16]
    available_input_clock_dividers_times2 = [1, 2, 4, 8, 16, 32]
    input_clock_divider = 1

    device_clock_min = 10e6
    device_clock_max = 1e9

    max_input_clock = 1e9

    def _check_valid_jesd_mode(self) -> None:
        """Verify current JESD configuration for part is valid."""
        _extra_jesd_check(self)
        converter._check_valid_jesd_mode(self)

    def _check_valid_internal_configuration(self) -> None:
        # FIXME
        pass

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by
        get_required_clocks

        Returns:
            List[str]: List of strings of clock names mapped by get_required_clocks
        """
        return ["adrv9009_device_clock", "adrv9009_sysref"]

    def _gekko_get_required_clocks(self) -> List[Dict]:
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

    def get_required_clocks(self) -> List[Dict]:
        """Generate list of required clocks.

        For ADRV9009 this will contain:
        [device clock requirement SOS, sysref requirement SOS]

        Returns:
            list[dict]: List of dictionaries of solver variables, equations, and constants
        """
        if self.solver == "gekko":
            return self._gekko_get_required_clocks()
        self.config = {}
        self.config["lmfc_divisor_sysref"] = self._convert_input(
            [*range(1, 20)], name="lmfc_divisor_sysref"
        )

        self.config["input_clock_divider_x2"] = self._convert_input(
            self.available_input_clock_dividers_times2
        )
        self.config["device_clock"] = self._add_intermediate(
            self.sample_clock / self.config["input_clock_divider_x2"]
        )
        self.config["sysref"] = self._add_intermediate(
            self.multiframe_clock
            / (self.config["lmfc_divisor_sysref"] * self.config["lmfc_divisor_sysref"])
        )

        self._add_equation(
            [
                self.device_clock_min <= self.config["device_clock"],
                self.config["device_clock"] <= self.device_clock_max,
            ]
        )

        return [self.config["device_clock"], self.config["sysref"]]


class adrv9009_rx_internal:
    """Internal class for ADRV9009 RX path."""

    quick_configuration_modes = quick_configuration_modes_rx

    bit_clock_min_available = {"jesd204b": 3.6864e9}
    bit_clock_max_available = {"jesd204b": 12.288e9}

    K_possible = [*np.arange(1, 32 + 1)]
    L_possible = [1, 2, 4]
    M_possible = [1, 2, 4]
    N_possible = [12, 14, 16, 24]
    Np_possible = [12, 16, 24]
    F_possible = [
        1,
        2,
        3,
        4,
        6,
        8,
    ]
    CS_possible = [0]
    CF_possible = [0]
    S_possible = [1, 2, 4]


class adrv9009_rx(adrv9009_rx_internal, adrv9009_core, adrv9009_bf):
    """ADRV9009 Receive model."""

    pass


class adrv9009_tx_internal:
    """Internal class for ADRV9009 TX path."""

    quick_configuration_modes = quick_configuration_modes_tx

    bit_clock_min_available = {"jesd204b": 2457.6e6}
    bit_clock_max_available = {"jesd204b": 12.288e9}

    K_possible = [*np.arange(1, 32 + 1)]
    L_possible = [1, 2, 4]
    M_possible = [1, 2, 4]
    N_possible = [12, 16]
    Np_possible = [12, 16]
    F_possible = [1, 2, 3, 4, 8]
    CS_possible = [0]
    CF_possible = [0]
    S_possible = [1]


class adrv9009_tx(adrv9009_tx_internal, adrv9009_core, adrv9009_bf):
    """ADRV9009 Transmit model."""

    pass


class adrv9009(core, gekko_translation, adrv9009_core):
    """ADRV9009 combined transmit and receive model."""

    solver = "CPLEX"

    def __init__(
        self, model: Union[GEKKO, CpoModel] = None, solver: str = None
    ) -> None:
        """Initialize ADRV9009 clocking model for TX and RX.

        This is a common class used to handle TX and RX constraints
        together.

        Args:
            model (GEKKO,CpoModel): Solver model
            solver (str): Solver name (gekko or CPLEX)
        """
        if solver:
            self.solver = solver
        self.adc = adrv9009_rx(model, solver=self.solver)
        self.dac = adrv9009_tx(model, solver=self.solver)
        self.model = model

    def _get_converters(self) -> List[Union[converter, converter]]:
        return [self.adc, self.dac]

    def get_required_clocks(self) -> List[Dict]:
        """Generate list of required clocks.

        For ADRV9009 this will contain:
        [device clock requirement SOS, sysref requirement SOS]

        Returns:
            list[dict]: List of dictionaries of solver variables, equations, and constants

        Raises:
            Exception: Invalid relation of rates between RX and TX
            AssertionError: Gekko called
        """
        # Validate sample rates feasible
        if (
            self.dac.sample_clock / self.adc.sample_clock
            not in [
                1,
                2,
                4,
            ]
            or self.adc.sample_clock / self.dac.sample_clock not in [1, 2, 4]
        ):
            raise Exception(
                "ADRV9009 RX and TX sample rates must be related by power of 2"
            )

        if self.solver == "gekko":
            raise AssertionError
            # return self._gekko_get_required_clocks()
        self.config = {}
        self.config["lmfc_divisor_sysref"] = self._convert_input(
            [*range(1, 20)], name="lmfc_divisor_sysref"
        )

        self.config["input_clock_divider_x2"] = self._convert_input(
            self.available_input_clock_dividers_times2
        )

        faster_clk = max([self.adc.sample_clock, self.dac.sample_clock])
        self.config["device_clock"] = self._add_intermediate(
            faster_clk / self.config["input_clock_divider_x2"]
        )

        faster_clk = max([self.adc.multiframe_clock, self.dac.multiframe_clock])
        self.config["sysref"] = self._add_intermediate(
            faster_clk
            / (self.config["lmfc_divisor_sysref"] * self.config["lmfc_divisor_sysref"])
        )

        self._add_equation(
            [
                self.device_clock_min <= self.config["device_clock"],
                self.config["device_clock"] <= self.device_clock_max,
            ]
        )

        return [self.config["device_clock"], self.config["sysref"]]
