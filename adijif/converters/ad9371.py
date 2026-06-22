"""AD9371 transceiver clocking model."""

from abc import ABCMeta
from typing import Any, Dict, List, Union

import numpy as np

from adijif.converters.ad9371_draw import ad9371_rx_draw, ad9371_tx_draw

from ..solvers import (
    GEKKO,
    CpoModel,  # type: ignore # noqa: I202,BLK100
    CpoSolveResult,
)
from .ad9371_profile import apply_settings, parse_profile
from .ad9371_util import (
    _extra_jesd_check,
    quick_configuration_modes_rx,  # type: ignore
    quick_configuration_modes_tx,
)
from .adc import adc
from .converter import converter
from .dac import dac


class ad9371_core(converter, metaclass=ABCMeta):
    """AD9371 transceiver clocking model.

    This model manages the JESD configuration and input clock constraints.
    External LO constraints are not modeled.

    Clocking: AD9371 uses onboard PLLs to generate the JESD clocks

        Lane Rate = I/Q Sample Rate * M * Np * (10 / 8) / L
        Lane Rate = sample_clock * M * Np * (10 / 8) / L
    """

    device_clock_available = None  # FIXME
    device_clock_ranges = None  # FIXME

    name = "AD9371"

    # JESD configurations
    quick_configuration_modes = None  # FIXME
    available_jesd_modes = ["jesd204b"]
    M_available = [1, 2, 4]
    L_available = [1, 2, 4]
    N_available = [12, 16]
    Np_available = [12, 16]
    F_available = [1, 2, 3, 4, 6, 8]
    S_available = [1]  # FIXME?
    K_available = [*np.arange(17, 32 + 1)]
    CS_available = [0]
    CF_available = [0]

    # Clock constraints
    converter_clock_min = 122.88e6
    converter_clock_max = 6.144e9

    sample_clock_min = 30.72e6
    sample_clock_max = 491.52e6

    device_clock_min = 10e6
    device_clock_max = 1e9

    clocking_option_available = ["integrated_pll"]
    _clocking_option = "integrated_pll"

    # Divider ranges
    input_clock_dividers_available = [1 / 2, 1, 2, 4, 8, 16]
    input_clock_dividers_times2_available = [1, 2, 4, 8, 16, 32]

    _lmfc_divisor_sysref_available = [*range(1, 20)]

    # Unused
    max_rx_sample_clock = 320e6
    max_tx_sample_clock = 491.52e6
    max_obs_sample_clock = 491.52e6

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
        return ["ad9371_ref_clk", "ad9371_sysref"]

    def get_config(self, solution: CpoSolveResult = None) -> Dict:
        """Extract configurations from solver results.

        Collect internal converter configuration and output clock definitions
        leading to connected devices (clock chips, FPGAs)

        Args:
            solution (CpoSolveResult): CPlex solution. Only needed for CPlex solver

        Returns:
            Dict: Dictionary of clocking rates and dividers for configuration
        """
        if solution:
            self.solution = solution
        return {}


class ad9371_clock_common(ad9371_core):
    """AD9371 class managing common singleton (Rx,Tx) methods."""

    def _check_valid_jesd_mode(self) -> None:
        """Verify current JESD configuration for part is valid."""
        _extra_jesd_check(self)
        return super()._check_valid_jesd_mode()

    def apply_profile_settings(self, profile: str) -> Dict:
        """Apply an AD9371 TES profile to this converter.

        Sets ``sample_clock`` and decimation/interpolation from the matching
        section of the profile (RX section for ``ad9371_rx``, TX section for
        ``ad9371_tx``). JESD link parameters are not part of the TES profile
        and must be configured separately.

        Args:
            profile (str): Path to a TES ``.txt`` profile or the profile text.

        Returns:
            Dict: The parsed profile dictionary (header metadata + sections).
        """
        parsed = parse_profile(profile)
        apply_settings(self, parsed)
        return parsed

    def get_config(self, solution: CpoSolveResult = None) -> Dict:
        """Extract configurations from solver results.

        Collect internal converter configuration and output clock definitions
        leading to connected devices (clock chips, FPGAs)

        Args:
            solution (CpoSolveResult): CPlex solution. Only needed for CPlex solver

        Returns:
            Dict: Dictionary of clocking rates and dividers for configuration
        """
        return {"clocking_option": self.clocking_option}

    def _gekko_get_required_clocks(self) -> List[Dict]:
        possible_sysrefs = []
        for n in range(1, 20):
            r = self.multiframe_clock / (n * n)
            if r == int(r):
                possible_sysrefs.append(r)

        self.config = {"sysref": self.model.sos1(possible_sysrefs)}
        self.model.Obj(self.config["sysref"])

        possible_device_clocks = []
        for div in self.input_clock_dividers_available:
            dev_clock = self.sample_clock / div
            if self.device_clock_min <= dev_clock <= self.device_clock_max:
                possible_device_clocks.append(dev_clock)

        self.config["ref_clk"] = self.model.sos1(possible_device_clocks)

        return [self.config["ref_clk"], self.config["sysref"]]

    def get_required_clocks(self) -> List[Dict]:
        """Generate list of required clocks.

        For AD9371 this will contain:
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
            self.input_clock_dividers_times2_available
        )
        self.config["ref_clk"] = self._add_intermediate(
            self.sample_clock / self.config["input_clock_divider_x2"]
        )
        self.config["sysref"] = self._add_intermediate(
            self.multiframe_clock
            / (
                self.config["lmfc_divisor_sysref"]
                * self.config["lmfc_divisor_sysref"]
            )
        )

        self._add_equation(
            [
                self.device_clock_min <= self.config["ref_clk"],
                self.config["ref_clk"] <= self.device_clock_max,
            ]
        )

        return [self.config["ref_clk"], self.config["sysref"]]


class ad9371_rx(ad9371_rx_draw, adc, ad9371_clock_common, ad9371_core):
    """AD9371 Receive model."""

    quick_configuration_modes = {"jesd204b": quick_configuration_modes_rx}
    name = "AD9371_RX"
    converter_type = "adc"

    # JESD configurations
    K_available = [*np.arange(17, 32 + 1)]
    L_available = [1, 2, 4]
    M_available = [1, 2, 4]
    N_available = [12, 16]
    Np_available = [12, 16]
    F_available = [
        1,
        2,
        3,
        4,
        6,
        8,
    ]
    CS_available = [0]
    CF_available = [0]
    S_available = [1, 2, 4]

    # Clock constraints
    bit_clock_min_available = {"jesd204b": 614.4e6}
    bit_clock_max_available = {"jesd204b": 6.144e9}

    sample_clock_max = 320e6

    _decimation = 8
    decimation_available = [2, 4, 5, 8, 10, 16, 20, 40]
    """
    AD9371 Rx decimation stages.

    .. code-block:: none

            +-----------+
            +-----------+ Dec 5 (5) +---------+
            |           +-----------+         |
            |                                 |
            |   +----------+   +----------+   |  +------------+   +--------------+
        >---+---+ RHB2 (2) +---+ RHB1 (2) +---+--+ RFIR (1,2) +---+ Programmable +
                +----------+   +----------+      +------------+   +--------------+
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize AD9371-RX class.

        Objects will default to mode and sample_clock.

        Args:
            *args (Any): Pass through arguments
            **kwargs (Any): Pass through keyword arguments
        """
        # Set default mode (M=4, L=2, S=1, Np=16)
        self.set_quick_configuration_mode(str(17))
        self.sample_clock = int(122.88e6)
        super().__init__(*args, **kwargs)

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by
        get_required_clocks

        Returns:
            List[str]: List of strings of clock names mapped by get_required_clocks
        """
        return ["ad9371_rx_ref_clk", "ad9371_rx_sysref"]


class ad9371_tx(ad9371_tx_draw, dac, ad9371_clock_common, ad9371_core):
    """AD9371 Transmit model."""

    quick_configuration_modes = {"jesd204b": quick_configuration_modes_tx}
    name = "AD9371_TX"
    converter_type = "dac"

    # JESD configurations
    K_available = [*np.arange(17, 32 + 1)]
    L_available = [2, 4]
    M_available = [1, 2, 4]
    N_available = [16]
    Np_available = [16]
    F_available = [1, 2, 3, 4, 8]
    CS_available = [0]
    CF_available = [0]
    S_available = [1]

    # Clock constraints
    bit_clock_min_available = {"jesd204b": 614.4e6}
    bit_clock_max_available = {"jesd204b": 6.144e9}

    _interpolation = 8
    interpolation_available = [1, 2, 4, 5, 8, 10, 16, 20, 32, 40]
    """
    AD9371 Tx interpolation stages.

    .. code-block:: none

                                +------------+
            +--------------------+ Int 5  (5) +--------------------+
            |                    +------------+                    |
            |                                                      |
            |   +------------+   +------------+   +------------+   |   +--------------+
        <---+---+ THB3 (1,2) +---+ THB2 (1,2) +---+ THB1 (1,2) +---+---+ TFIR (1,2,4) +
                +------------+   +------------+   +------------+       +--------------+

    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize AD9371-TX class.

        Objects will default to mode and sample_clock.

        Args:
            *args (Any): Pass through arguments
            **kwargs (Any): Pass through keyword arguments
        """
        # Set default mode (M=4, L=2, Np=16)
        self.set_quick_configuration_mode(str(3))
        self.sample_clock = int(122.88e6)
        super().__init__(*args, **kwargs)

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by
        get_required_clocks

        Returns:
            List[str]: List of strings of clock names mapped by get_required_clocks
        """
        return ["ad9371_tx_ref_clk", "ad9371_tx_sysref"]


class ad9371(ad9371_core):
    """AD9371 combined transmit and receive model."""

    name = "AD9371"
    solver = "CPLEX"
    _nested = ["adc", "dac"]
    converter_type = "adc_dac"

    def __init__(
        self, model: Union[GEKKO, CpoModel] = None, solver: str = None
    ) -> None:
        """Initialize AD9371 clocking model for TX and RX.

        This is a common class used to handle TX and RX constraints
        together.

        Args:
            model (GEKKO,CpoModel): Solver model
            solver (str): Solver name (gekko or CPLEX)
        """
        if solver:
            self.solver = solver
        self.adc = ad9371_rx(model, solver=self.solver)
        self.dac = ad9371_tx(model, solver=self.solver)
        self.model = model

    def validate_config(self) -> None:
        """Validate device configurations including JESD and clocks of both ADC and DAC.

        This check only is for static configuration that does not include
        variables which are solved.
        """
        self.adc.validate_config()
        self.dac.validate_config()

    def _get_converters(self) -> List[Union[converter, converter]]:
        return [self.adc, self.dac]

    def apply_profile_settings(self, profile: str) -> Dict:
        """Apply an AD9371 TES profile to both RX and TX paths.

        Args:
            profile (str): Path to a TES ``.txt`` profile or the profile text.

        Returns:
            Dict: The parsed profile dictionary.
        """
        parsed = parse_profile(profile)
        apply_settings(self, parsed)
        return parsed

    def get_required_clocks(self) -> List[Dict]:
        """Generate list of required clocks.

        For AD9371 this will contain:
        [device clock requirement SOS, sysref requirement SOS]

        Returns:
            list[dict]: List of dictionaries of solver variables, equations, and constants

        Raises:
            Exception: Invalid relation of rates between RX and TX
            AssertionError: Gekko called
        """
        # Validate sample rates feasible
        if self.dac.sample_clock / self.adc.sample_clock not in [
            1,
            2,
            4,
        ] or self.adc.sample_clock / self.dac.sample_clock not in [1, 2, 4]:
            raise Exception(
                "AD9371 RX and TX sample rates must be related by power of 2"
            )

        if self.solver == "gekko":
            raise AssertionError

        self.config = {}
        self.config["adc_lmfc_divisor_sysref"] = self._convert_input(
            self._lmfc_divisor_sysref_available, name="adc_lmfc_divisor_sysref"
        )
        self.config["dac_lmfc_divisor_sysref"] = self._convert_input(
            self._lmfc_divisor_sysref_available, name="dac_lmfc_divisor_sysref"
        )

        self.config["input_clock_divider_x2"] = self._convert_input(
            self.input_clock_dividers_times2_available
        )

        faster_clk = max([self.adc.sample_clock, self.dac.sample_clock])
        self.config["ref_clk"] = self._add_intermediate(
            faster_clk / self.config["input_clock_divider_x2"]
        )

        self.config["sysref_adc"] = self._add_intermediate(
            self.adc.multiframe_clock / self.config["adc_lmfc_divisor_sysref"]
        )
        self.config["sysref_dac"] = self._add_intermediate(
            self.dac.multiframe_clock / self.config["dac_lmfc_divisor_sysref"]
        )

        self._add_equation(
            [
                self.device_clock_min <= self.config["ref_clk"],
                self.config["ref_clk"] <= self.device_clock_max,
            ]
        )

        return [
            self.config["ref_clk"],
            self.config["sysref_adc"],
            self.config["sysref_dac"],
        ]
