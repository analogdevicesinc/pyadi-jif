"""AD9081 high speed MxFE clocking model."""

from abc import ABCMeta, abstractmethod
from typing import Any, Dict, List, Union

import numpy as np

from ..solvers import GEKKO, CpoModel, CpoSolveResult  # type: ignore
from .ad9081_dp import ad9081_dp_rx, ad9081_dp_tx
from .ad9081_util import _load_rx_config_modes, _load_tx_config_modes
from .adc import adc
from .converter import converter
from .dac import dac

from ..solvers import integer_var  # type: ignore # isort: skip # noqa: I202


class ad9081_core(converter, metaclass=ABCMeta):
    """AD9081 high speed MxFE model.

    This model supports both direct clock configurations and on-board
    generation

    Clocking: AD9081 can internally generate or leverage external clocks. The
    high speed clock within the system is referred to as the DAC clock and
    the ADC clock will be a divided down version of the clock:
    adc_clock  == dac_clock / L, where L = 1,2,3,4


    For internal generation, the DAC clock is generated through an integer PLL
    through the following relation:
    dac_clock == ((m_vco * n_vco) / R * ref_clock) / D

    For external clocks, the clock must be provided at the DAC clock rate

    Once we have the DAC clock the data rates can be directly evaluated into
    each JESD framer:

    rx_baseband_sample_rate = (dac_clock / L) / datapath_decimation
    tx_baseband_sample_rate = dac_clock / datapath_interpolation

    """

    device_clock_available = None  # FIXME
    device_clock_ranges = None  # FIXME

    model: Union[GEKKO, CpoModel] = None

    name = "AD9081"

    # Integrated PLL constants
    l_available = [1, 2, 3, 4]
    l = 1  # pylint:  disable=E741
    m_vco_available = [5, 7, 8, 11]  # 8 is nominal
    m_vco = 8
    n_vco_available = [*range(2, 50 + 1)]
    n_vco = 2
    r_available = [1, 2, 3, 4]
    r = 1
    d_available = [1, 2, 3, 4]
    d = 1
    # Integrated PLL limits
    pfd_min = 25e6
    pfd_max = 750e6
    vco_min = 6e9
    vco_max = 12e9

    # JESD parameters
    available_jesd_modes = ["jesd204b", "jesd204c"]
    M_available = [1, 2, 3, 4, 6, 8, 12, 16]
    L_available = [1, 2, 3, 4, 6, 8]
    N_available = [12, 16]
    Np_available = [12, 16, 24]
    F_available = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32]
    S_available = [1, 2, 4, 8]
    # FIXME
    # K_available = [4, 8, 12, 16, 20, 24, 28, 32]
    K_available = [16, 32, 64, 128, 256]
    CS_available = [0, 1, 2, 3]
    CF_available = [0]
    # FIXME

    # Clocking constraints
    clocking_option_available = ["integrated_pll", "direct"]
    _clocking_option = "integrated_pll"
    bit_clock_min_available = {"jesd204b": 1.5e9, "jesd204c": 6e9}
    bit_clock_max_available = {"jesd204b": 15.5e9, "jesd204c": 24.75e9}

    config = {}  # type: ignore

    device_clock_max = 12e9
    _lmfc_divisor_sysref_available = [
        1,
        2,
        4,
        8,
        16,
        32,
        64,
        128,
        256,
        512,
        1024,
    ]

    def _check_valid_internal_configuration(self) -> None:
        # FIXME
        pass

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
        if self.clocking_option == "integrated_pll":
            pll_config: Dict = {
                "m_vco": self._get_val(self.config["ad9081_m_vco"]),
                "n_vco": self._get_val(self.config["ad9081_n_vco"]),
                "r": self._get_val(self.config["ad9081_r"]),
                "d": self._get_val(self.config["ad9081_d"]),
            }
            if "serdes_pll_div" in self.config:
                pll_config["serdes_pll_div"] = self._get_val(
                    self.config["serdes_pll_div"]
                )
            return {
                "clocking_option": self.clocking_option,
                "pll_config": pll_config,
            }
        else:
            if "serdes_pll_div" in self.config:
                return {
                    "serdes_pll_div": self._get_val(self.config["serdes_pll_div"]),
                    "clocking_option": self.clocking_option,
                }
            return {"clocking_option": self.clocking_option}

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by get_required_clocks

        Returns:
            List[str]: List of strings of clock names in order
        """
        # clk = (
        # "ad9081_dac_clock" if self.clocking_option == "direct" else "ad9081_pll_ref"
        # )
        clk = f"{self.name.lower()}_ref_clk"
        sysref = f"{self.name.lower()}_sysref"
        return [clk, sysref]

    @property
    @abstractmethod
    def _converter_clock_config(self) -> None:
        """Define source clocking relation based on ADC, DAC, or both.

        Raises:
            NotImplementedError: Method not implemented
        """
        raise NotImplementedError

    def _pll_config(self, rxtx: bool = False) -> Dict:
        self._converter_clock_config()  # type: ignore

        self.config["ad9081_m_vco"] = self._convert_input([5, 7, 8, 11], "ad9081_m_vco")
        self.config["ad9081_n_vco"] = self._convert_input(
            [*range(2, 51)], "ad9081_n_vco"
        )
        self.config["ad9081_r"] = self._convert_input([1, 2, 3, 4], "ad9081_r")
        self.config["ad9081_d"] = self._convert_input([1, 2, 3, 4], "ad9081_d")

        self.config["ad9081_ref_clk"] = self._add_intermediate(
            self.config["converter_clk"]
            * self.config["ad9081_d"]
            * self.config["ad9081_r"]
            / (self.config["ad9081_m_vco"] * self.config["ad9081_n_vco"])
        )
        # if self.solver == "gekko":
        #     self.config["ref_clk"] = self.model.Var(
        #         integer=True,
        #         lb=1e6,
        #         ub=self.device_clock_max,
        #         value=self.device_clock_max,
        #     )
        # elif self.solver == "CPLEX":
        #     # self.config["ref_clk"] = integer_var(
        #     #     int(1e6), int(self.device_clock_max), "ref_clk"
        #     # )
        #     self.config["ref_clk"] = (
        #         self.config["converter_clk"]
        #         * self.config["d"]
        #         * self.config["r"]
        #         / (self.config["m_vco"] * self.config["n_vco"])
        #     )
        # else:
        #     raise Exception("Unknown solver")

        self.config["ad9081_vco"] = self._add_intermediate(
            self.config["ad9081_ref_clk"]
            * self.config["ad9081_m_vco"]
            * self.config["ad9081_n_vco"]
            / self.config["ad9081_r"],
        )

        # if self.solver == "gekko":
        #     self.config["vco"] = self.model.Intermediate(
        #         self.config["ref_clk"]
        #         * self.config["m_vco"]
        #         * self.config["n_vco"]
        #         / self.config["r"],
        #     )
        # elif self.solver == "CPLEX":
        #     self.config["vco"] = (
        #         self.config["ref_clk"]
        #         * self.config["m_vco"]
        #         * self.config["n_vco"]
        #         / self.config["r"]
        #     )
        # else:
        #     raise Exception("Unknown solver: %s" % self.solver)

        self._add_equation(
            [
                self.config["ad9081_vco"] >= self.vco_min,
                self.config["ad9081_vco"] <= self.vco_max,
                self.config["ad9081_ref_clk"] / self.config["ad9081_r"] <= self.pfd_max,
                self.config["ad9081_ref_clk"] / self.config["ad9081_r"] >= self.pfd_min,
                self.config["ad9081_ref_clk"] >= int(100e6),
                self.config["ad9081_ref_clk"] <= int(2e9),
                # self.config["converter_clk"] <= self.device_clock_max,
                self.config["converter_clk"]
                >= (
                    self.converter_clock_min
                    if not rxtx
                    else self.dac.converter_clock_min  # type: ignore
                ),
                self.config["converter_clk"]
                <= (
                    self.converter_clock_max
                    if not rxtx
                    else self.dac.converter_clock_max  # type: ignore
                ),
            ]
        )

        # Make ref_clk an integer since API requires it
        if self.solver == "CPLEX":
            self.config["integer_ad9081_ref_clk"] = integer_var(
                min=int(100e6), max=int(2e9), name="integer_ad9081_ref_clk"
            )
            self._add_equation(
                [self.config["integer_ad9081_ref_clk"] == self.config["ad9081_ref_clk"]]
            )
        else:
            raise Exception("Only CPLEX solver supported")

        return self.config["ad9081_ref_clk"]

    def get_required_clocks(self) -> List:
        """Generate list required clocks.

        For AD9081 this will contain [converter clock, sysref requirement SOS]

        Returns:
            List: List of solver variables, equations, and constants
        """
        # SYSREF
        self.config = {}
        self.config["lmfc_divisor_sysref"] = self._convert_input(
            self._lmfc_divisor_sysref_available, "lmfc_divisor_sysref"
        )

        self.config["sysref"] = self._add_intermediate(
            self.multiframe_clock / self.config["lmfc_divisor_sysref"]
        )

        # Device Clocking
        if self.clocking_option == "direct":
            # raise Exception("Not implemented yet")
            clk = self.sample_clock * self.datapath_decimation
        else:
            clk = self._pll_config()  # type: ignore

        # Objectives
        # self.model.Obj(self.config["sysref"])  # This breaks many searches
        # self.model.Obj(-1*self.config["lmfc_divisor_sysref"])

        return [clk, self.config["sysref"]]


class ad9081_rx(adc, ad9081_core):
    """AD9081 Receive model."""

    name = "AD9081_RX"
    converter_type = "adc"

    converter_clock_min = 1.45e9
    converter_clock_max = 4e9

    sample_clock_min = 312.5e6 / 16
    sample_clock_max = 4e9

    quick_configuration_modes = _load_rx_config_modes()

    datapath = ad9081_dp_rx()
    decimation_available = [
        1,
        2,
        3,
        4,
        6,
        8,
        9,
        12,
        16,
        18,
        24,
        32,
        36,
        48,
        64,
        72,
        96,
        144,
        "auto",
    ]

    @property
    def decimation(self) -> int:
        """Decimation factor. This is the product of the coarse and fine decimation."""
        return self.datapath.decimation_overall

    @decimation.setter
    def decimation(self, value: int) -> None:
        raise Exception(
            "Decimation is not writable and should be set by the properties\n"
            + " datapath.cddc_decimations and datapath.fddc_decimations"
        )

    _adc_lmfc_divisor_sysref = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize AD9081 clocking model for RX.

        This is a common class used to handle RX constraints
        together.

        Args:
            *args (Any): Pass through arguments
            **kwargs (Any): Pass through keyword arguments
        """
        self.set_quick_configuration_mode("3.01", "jesd204b")
        self.datapath.cddc_decimations = [2] * 4
        self.datapath.fddc_decimations = [4] * 8
        self.datapath.fddc_enabled = [True] * 8
        assert self.decimation == 8
        super().__init__(*args, **kwargs)

    def _converter_clock_config(self) -> None:
        """RX specific configuration of internal PLL config.

        This method will update the config struct to include
        the RX clocking constraints
        """
        adc_clk = self.decimation * self.sample_clock
        self.config["l"] = self._convert_input([1, 2, 3, 4], "l")
        self.config["adc_clk"] = self._convert_input(adc_clk)
        self.config["converter_clk"] = self._add_intermediate(
            self.config["adc_clk"] * self.config["l"]
        )

    def _check_valid_internal_configuration(self) -> None:
        mode = self._check_valid_jesd_mode()
        cfg = self.quick_configuration_modes[self.jesd_class][mode]

        # Check decimation is valid
        if isinstance(self.decimation, int) or isinstance(self.decimation, float):
            found = False
            combos = []
            for dec in cfg["decimations"]:
                found = found or dec["coarse"] * dec["fine"] == self.decimation
                combos.append(f'{dec["coarse"]}/{dec["fine"]}')
            assert found, (
                f"Decimation {self.decimation} not valid for current JESD mode\n"
                + f"Valid CDDC/FDDC {combos}"
            )
        elif self.decimation == "auto":
            for dec in cfg["decimations"]:
                dec = dec["coarse"] * dec["fine"]
                # Check
                cc = dec * self.sample_clock
                # if dec == 64:
                #     print("dec", dec, cc, cfg["coarse"], cfg["fine"])
                if cc <= self.converter_clock_max and cc >= self.converter_clock_min:
                    self.decimation = dec
                    print("Decimation automatically determined:", dec)
                    return
            raise Exception("No valid decimation found")
        else:
            raise Exception("Decimation not valid")


class ad9081_tx(dac, ad9081_core):
    """AD9081 Transmit model."""

    name = "AD9081_TX"
    converter_type = "dac"

    converter_clock_min = 2.9e9
    converter_clock_max = 12e9

    sample_clock_min = 2.9e9 / (6 * 24)  # with max interpolation
    sample_clock_max = 12e9

    quick_configuration_modes = _load_tx_config_modes()

    datapath = ad9081_dp_tx()
    interpolation_available = [
        1,
        2,
        3,
        4,
        6,
        8,
        9,
        12,
        16,
        18,
        24,
        32,
        36,
        48,
        64,
        72,
        96,
        144,
    ]

    @property
    def interpolation(self) -> int:
        """Interpolation factor.

        This is the product of the coarse and fine interpolation.

        Returns:
            int: Interpolation factor
        """
        return self.datapath.interpolation_overall

    @interpolation.setter
    def interpolation(self, value: int) -> None:
        raise Exception(
            "Interpolation is not writable and should be set by the properties\n"
            + " datapath.cduc_interpolation and datapath.fduc_interpolation"
        )

    _dac_lmfc_divisor_sysref = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize AD9081 clocking model for TX.

        This is a common class used to handle TX constraints
        together.

        Args:
            *args (Any): Pass through arguments
            **kwargs (Any): Pass through keyword arguments
        """
        self.set_quick_configuration_mode("0", "jesd204c")
        self.datapath.cduc_interpolation = 6
        self.datapath.fduc_interpolation = 4
        self.datapath.fduc_enabled = [True] * 8
        super().__init__(*args, **kwargs)

    def _converter_clock_config(self) -> None:
        """TX specific configuration of internall PLL config.

        This method will update the config struct to include
        the TX clocking constraints
        """
        dac_clk = self.interpolation * self.sample_clock
        self.config["dac_clk"] = self._convert_input(dac_clk)
        self.config["converter_clk"] = self._add_intermediate(self.config["dac_clk"])


class ad9081(ad9081_core):
    """AD9081 combined transmit and receive model."""

    converter_clock_min = ad9081_rx.converter_clock_min
    converter_clock_max = ad9081_rx.converter_clock_max
    quick_configuration_modes: Dict[str, Any] = {}
    _nested = ["adc", "dac"]
    converter_type = "adc_dac"

    def __init__(
        self, model: Union[GEKKO, CpoModel] = None, solver: str = None
    ) -> None:
        """Initialize AD9081 clocking model for TX and RX.

        This is a common class used to handle TX and RX constraints
        together.

        Args:
            model (GEKKO,CpoModel): Solver model
            solver (str): Solver name (gekko or CPLEX)
        """
        if solver:
            self.solver = solver
        self.adc = ad9081_rx(model, solver=self.solver)
        self.dac = ad9081_tx(model, solver=self.solver)
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

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by get_required_clocks

        Returns:
            List[str]: List of strings of clock names in order
        """
        clk = (
            "ad9081_dac_clock"
            if self.adc.clocking_option == "direct"
            else "ad9081_pll_ref"
        )
        return [clk, "ad9081_adc_sysref", "ad9081_dac_sysref"]

    def _converter_clock_config(self) -> None:
        adc_clk = self.adc.decimation * self.adc.sample_clock
        dac_clk = self.dac.interpolation * self.dac.sample_clock
        l = dac_clk / adc_clk
        if np.abs(l - round(l)) > 1e-6:
            raise Exception(f"Sample clock ratio is not integer {adc_clk} {dac_clk}")
        else:
            l = int(round(l))
        if l not in self.adc.l_available:
            raise Exception(
                f"ADC clock must be DAC clock/L where L={self.adc.l_available}."
                + f" Got {l} ({dac_clk}/{adc_clk})"
            )

        self.config["dac_clk"] = self._convert_input(dac_clk)
        self.config["adc_clk"] = self._convert_input(adc_clk)
        self.config["converter_clk"] = self._add_intermediate(self.config["dac_clk"])

        # Add single PLL constraint
        # JESD204B/C transmitter is a power of 2 divisor of the lane rate of
        # the JESD204B/C receiver
        if self.solver == "gekko":
            raise Exception("Not implemented for GEKKO")
        elif self.solver == "CPLEX":
            divs = [int(2**d) for d in range(16)]
            self.config["serdes_pll_div"] = self._convert_input(
                divs, "serdes_pll_div", default=1
            )
        else:
            raise Exception(f"Unknown solver {self.solver}")

        self._add_equation(
            [self.config["serdes_pll_div"] * self.adc.bit_clock == self.dac.bit_clock]
        )

    def get_required_clocks(self) -> List:
        """Generate list required clocks.

        For AD9081 this will contain [converter clock, sysref requirement SOS]

        Returns:
            List: List of solver variables, equations, and constants
        """
        # SYSREF
        self.config = {}
        self.config["adc_lmfc_divisor_sysref"] = self._convert_input(
            self.adc._adc_lmfc_divisor_sysref, "adc_lmfc_divisor_sysref"
        )
        self.config["dac_lmfc_divisor_sysref"] = self._convert_input(
            self.dac._dac_lmfc_divisor_sysref, "dac_lmfc_divisor_sysref"
        )

        self.config["sysref_adc"] = self._add_intermediate(
            self.adc.multiframe_clock / self.config["adc_lmfc_divisor_sysref"]
        )
        self.config["sysref_dac"] = self._add_intermediate(
            self.dac.multiframe_clock / self.config["dac_lmfc_divisor_sysref"]
        )

        # Device Clocking
        if self.clocking_option == "direct":
            # raise Exception("Not implemented yet")
            # adc_clk = self.sample_clock * self.datapath_decimation
            # clk = dac_clk
            clk = self.dac.interpolation * self.dac.sample_clock
        else:
            clk = self._pll_config(rxtx=True)

        # Objectives
        # self.model.Obj(self.config["sysref"])  # This breaks many searches
        # self.model.Obj(-1*self.config["lmfc_divisor_sysref"])

        return [clk, self.config["sysref_adc"], self.config["sysref_dac"]]


class ad9082_rx(ad9081_rx):
    """AD9082 MxFE RX Clocking Model."""

    converter_clock_max = 6e9


class ad9082_tx(ad9081_tx):
    """AD9082 MxFE TX Clocking Model."""

    pass


class ad9082(ad9081):
    """AD9081 combined transmit and receive model."""

    converter_clock_min = ad9082_rx.converter_clock_min
    converter_clock_max = ad9082_rx.converter_clock_max
    quick_configuration_modes: Dict[str, Any] = {}
    _nested = ["adc", "dac"]

    def __init__(
        self, model: Union[GEKKO, CpoModel] = None, solver: str = None
    ) -> None:
        """Initialize AD9081 clocking model for TX and RX.

        This is a common class used to handle TX and RX constraints
        together.

        Args:
            model (GEKKO,CpoModel): Solver model
            solver (str): Solver name (gekko or CPLEX)
        """
        if solver:
            self.solver = solver
        self.adc = ad9082_rx(model, solver=self.solver)
        self.dac = ad9082_tx(model, solver=self.solver)
        self.model = model

    def _get_converters(self) -> List[Union[converter, converter]]:
        return [self.adc, self.dac]

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by get_required_clocks

        Returns:
            List[str]: List of strings of clock names in order
        """
        clk = (
            "ad9082_dac_clock"
            if self.adc.clocking_option == "direct"
            else "ad9082_pll_ref"
        )
        return [clk, "ad9082_adc_sysref", "ad9082_dac_sysref"]
