"""Xilinx FPGA clocking model."""
from typing import Dict, List, Optional, Union

from adijif.converters.converter import converter as conv
from adijif.fpgas.xilinx_bf import xilinx_bf
from adijif.solvers import CpoSolveResult  # type: ignore
from adijif.solvers import (CpoIntVar, GK_Intermediate, GK_Operators,
                            GKVariable, gekko, integer_var)


class xilinx(xilinx_bf):
    """Xilinx FPGA clocking model.

    This model captures different limitations of the Xilinx
    PLLs and interfaces used for JESD.

    Currently only Zynq 7000 devices have been fully tested.
    """

    hdl_core_version = 1.0

    available_speed_grades = [-1, -2, -3]
    speed_grade = -2

    transceiver_voltage = 800

    ref_clock_min = -1  # Not set
    ref_clock_max = -1  # Not set

    available_fpga_packages = [
        "Unknown",
        "RF",
        "FL",
        "FF",
        "FB",
        "HC",
        "FH",
        "CS",
        "CP",
        "FT",
        "FG",
        "SB",
        "RB",
        "RS",
        "CL",
        "SF",
        "BA",
        "FA",
    ]
    fpga_package = "FB"

    available_fpga_families = ["Unknown", "Artix", "Kintex", "Virtex", "Zynq"]
    fpga_family = "Zynq"

    available_transceiver_types = ["GTX2"]
    transciever_type = "GTX2"

    sys_clk_selections = [
        "GTH34_SYSCLK_CPLL",
        "GTH34_SYSCLK_QPLL1",
        "GTH34_SYSCLK_QPLL0",
    ]
    sys_clk_select = "GTH34_SYSCLK_QPLL1"

    """ Force use of QPLL for transceiver source """
    force_qpll = 0

    """ Force use of CPLL for transceiver source """
    force_cpll = 0

    """ Force all transceiver sources to be from a single PLL quad.
        This will try to leverage the output dividers of the PLLs
    """
    force_single_quad_tile = 0

    """ Request that clock chip generated device clock
        device clock == LMFC/40
        NOTE: THIS IS NOT FPGA REF CLOCK
    """
    request_device_clock = False

    _clock_names: Union[List[str]] = []

    @property
    def _ref_clock_max(self) -> int:
        """Get maximum reference clock for config.

        Returns:
            int: Rate in samples per second.

        Raises:
            Exception: Unsupported transceiver type configured.
        """
        # https://www.xilinx.com/support/documentation/data_sheets/ds191-XC7Z030-XC7Z045-data-sheet.pdf
        if self.transciever_type == "GTX2":
            if self.speed_grade == "-3E":
                return 700000000
            else:
                return 670000000
        else:
            raise Exception(
                f"Unknown ref_clock_max for transceiver type {self.transciever_type}"
            )
            # raise Exception(f"Unknown transceiver type {self.transciever_type}")

    @property
    def _ref_clock_min(self) -> int:
        """Get minimum reference clock for config.

        Returns:
            int: Rate in samples per second.

        Raises:
            Exception: Unsupported transceiver type configured.
        """
        # https://www.xilinx.com/support/documentation/data_sheets/ds191-XC7Z030-XC7Z045-data-sheet.pdf
        if self.transciever_type == "GTX2":
            return 60000000
        else:
            raise Exception(
                f"Unknown ref_clock_min for transceiver type {self.transciever_type}"
            )
            # raise Exception(f"Unknown transceiver type {self.transciever_type}")

    # CPLL
    @property
    def vco_min(self) -> int:
        """Get minimum CPLL VCO rate for config.

        Returns:
            int: Rate in samples per second.

        Raises:
            Exception: Unsupported transceiver type configured.
        """
        if self.transciever_type == "GTX2":
            return 1600000000
        elif self.transciever_type in ["GTH3", "GTH4", "GTY4"]:
            return 2000000000
        else:
            raise Exception(
                f"Unknown vco_min for transceiver type {self.transciever_type}"
            )

    @property
    def vco_max(self) -> int:
        """Get maximum CPLL VCO rate for config.

        Returns:
            int: Rate in samples per second.

        Raises:
            Exception: Unsupported transceiver type configured.
        """
        if self.transciever_type == "GTX2":
            return 3300000000
        elif self.transciever_type in ["GTH3", "GTH4", "GTY4"]:
            if self.hdl_core_version > 2:
                if self.transciever_type in ["GTH3", "GTH4"]:
                    if self.transceiver_voltage < 850 or self.speed_grade == -1:
                        return 4250000000
                elif self.transciever_type == "GTY4" and self.speed_grade == -1:
                    return 4250000000
            return 6250000000
        else:
            raise Exception(
                f"Unknown vco_max for transceiver type {self.transciever_type}"
            )

    # QPLL
    @property
    def vco0_min(self) -> int:
        """Get minimum QPLL VCO0 rate for config.

        This is applicable for QPLLs only.

        Returns:
            int: Rate in samples per second.

        Raises:
            Exception: Unsupported transceiver type configured.
        """
        if self.transciever_type == "GTX2":
            return 5930000000
        elif self.transciever_type in ["GTH3", "GTH4", "GTY4"]:
            if self.sys_clk_select == "GTH34_SYSCLK_QPLL1":
                return 8000000000
            else:
                return 9800000000
        else:
            raise Exception(
                f"Unknown vco0_min for transceiver type {self.transciever_type}"
            )

    @property
    def vco0_max(self) -> int:
        """Get maximum QPLL VCO0 rate for config.

        This is applicable for QPLLs only.

        Returns:
            int: Rate in samples per second.

        Raises:
            Exception: Unsupported transceiver type configured.
        """
        if self.transciever_type == "GTX2":
            if (
                self.hdl_core_version > 2
                and self.fpga_family == "Kintex"
                and self.fpga_package in ["FB", "RF", "FF"]
            ):
                return 6600000000
            return 8000000000
        elif self.transciever_type in ["GTH3", "GTH4", "GTY4"]:
            if self.sys_clk_select == "GTH34_SYSCLK_QPLL1":
                return 13000000000
            else:
                return 16375000000
        else:
            raise Exception(
                f"Unknown vco0_max for transceiver type {self.transciever_type}"
            )

    @property
    def vco1_min(self) -> int:
        """Get minimum QPLL VCO1 rate for config.

        This is applicable for QPLLs only.

        Returns:
            int: Rate in samples per second.

        Raises:
            Exception: Unsupported transceiver type configured.
        """
        if self.transciever_type == "GTX2":
            return 9800000000
        elif self.transciever_type in ["GTH3", "GTH4", "GTY4"]:
            return self.vco0_min
        else:
            raise Exception(
                f"Unknown vco1_min for transceiver type {self.transciever_type}"
            )

    @property
    def vco1_max(self) -> int:
        """Get maximum QPLL VCO1 rate for config.

        This is applicable for QPLLs only.

        Returns:
            int: Rate in samples per second.

        Raises:
            Exception: Unsupported transceiver type configured.
        """
        if self.transciever_type == "GTX2":
            if self.hdl_core_version > 2 and self.speed_grade == -2:
                return 10312500000
            return 12500000000
        elif self.transciever_type in ["GTH3", "GTH4", "GTY4"]:
            return self.vco0_max
        else:
            raise Exception(
                f"Unknown vco1_max for transceiver type {self.transciever_type}"
            )

    @property
    def N(self) -> List[int]:
        """Get available feedback divider settings.

        This is applicable for QPLLs only.

        Returns:
            list[int]: List of divider integers.

        Raises:
            Exception: Unsupported transceiver type configured.
        """
        if self.transciever_type == "GTX2":
            return [16, 20, 32, 40, 64, 66, 80, 100]
        else:
            raise Exception(f"Unknown N for transceiver type {self.transciever_type}")

    def setup_by_dev_kit_name(self, name: str) -> None:
        """Configure object based on board name. Ex: zc706, zcu102.

        Args:
            name (str): Name of dev kit. Ex: zc706, zcu102

        Raises:
            Exception: Unsupported board requested.

        """
        if name.lower() == "zc706":
            self.transciever_type = "GTX2"
            self.fpga_family = "Zynq"
            self.fpga_package = "FF"
            self.speed_grade = -2
            self.ref_clock_min = 60000000
            self.ref_clock_max = 670000000
        elif name.lower() == "zcu102":
            self.transciever_type = "GTH4"
            self.fpga_family = "Zynq"
            self.fpga_package = "FF"
            self.speed_grade = -2
            self.ref_clock_min = 60000000
            self.ref_clock_max = 820000000
        elif name.lower() == "vcu118":
            # XCVU9P-L2FLGA2104
            self.transciever_type = "GTY4"
            self.fpga_family = "Virtex"
            self.fpga_package = "FL"
            self.speed_grade = -2
            self.ref_clock_min = 60000000
            self.ref_clock_max = 820000000
        else:
            raise Exception(f"No boardname found in library for {name}")

    def determine_pll(self, bit_clock: int, fpga_ref_clock: int) -> Dict:
        """Determin if configuration is possible with CPLL or QPLL.

        CPLL is checked first and will check QPLL if that case is
        invalid.

        This is only used for brute-force implementations.

        Args:
            bit_clock (int): Equivalent to lane rate in bits/second
            fpga_ref_clock (int): System reference clock

        Returns:
            Dict: Dictionary of PLL configuration
        """
        try:
            info = self.determine_cpll(bit_clock, fpga_ref_clock)
        except BaseException:
            info = self.determine_qpll(bit_clock, fpga_ref_clock)
        return info

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by get_required_clocks

        Returns:
            List[str]: List of strings of clock names in order

        Raises:
            Exception: Clock have not been enumerated aka get_required_clocks not
                not called yet.
        """
        if not self._clock_names:
            raise Exception(
                "get_required_clocks must be run to generated"
                + " dependent clocks before names are available"
            )
        return self._clock_names

    def get_config(
        self, solution: Optional[CpoSolveResult] = None
    ) -> Union[List[Dict], Dict]:
        """Extract configurations from solver results.

        Collect internal FPGA configuration and output clock definitions.

        Args:
            solution (CpoSolveResult): CPlex solution. Only needed for CPlex solver

        Returns:
            Dict: Dictionary of clocking rates and dividers for configuration

        Raises:
            Exception: Unsupported solver
        """
        out = []
        for config in self.configs:
            pll_config: Dict[str, Union[str, int, float]] = {}
            if self.solver == "gekko":
                if isinstance(config["qpll_0_cpll_1"], GKVariable):
                    pll = config["qpll_0_cpll_1"].value[0]
                else:
                    pll = config["qpll_0_cpll_1"].value
            elif self.solver == "CPLEX":
                name = config["qpll_0_cpll_1"].get_name()
                pll = solution.get_value(name)  # type: ignore
            else:
                raise Exception(f"Unknown solver {self.solver}")

            if self.solver == "gekko":
                if pll > 0:
                    pll_config["type"] = "cpll"
                    for k in ["m", "d", "n1", "n2", "vco"]:
                        pll_config[k] = self._get_val(config[k + "_cpll"])

                else:
                    pll_config["type"] = "qpll"
                    for k in ["m", "d", "n", "vco", "band", "qty4_full_rate_enabled"]:
                        pll_config[k] = self._get_val(config[k])

            elif self.solver == "CPLEX":
                if pll > 0:
                    pll_config["type"] = "cpll"
                    pll_config["m"] = solution.get_value(config["m_cpll"].get_name())  # type: ignore
                    pll_config["d"] = solution.get_value(config["d_cpll"].get_name())  # type: ignore
                    pll_config["n1"] = solution.get_value(config["n1_cpll"].get_name())  # type: ignore
                    pll_config["n2"] = solution.get_value(config["n2_cpll"].get_name())  # type: ignore
                    # pll_config["vco"] = solution.get_value(
                    #     config["vco_cpll"].get_name()
                    # )
                    fpga_ref = solution.get_value(self.config["fpga_ref"].get_name())  # type: ignore
                    pll_config["vco"] = (
                        fpga_ref * pll_config["n1"] * pll_config["n2"] / pll_config["m"]
                    )

                else:
                    pll_config["type"] = "qpll"
                    pll_config["m"] = solution.get_value(config["m"].get_name())  # type: ignore
                    pll_config["d"] = solution.get_value(config["d"].get_name())  # type: ignore
                    pll_config["n"] = solution.get_value(config["n"].get_name())  # type: ignore
                    # pll_config["vco"] = solution.get_value(config["vco"].get_name())
                    fpga_ref = solution.get_value(self.config["fpga_ref"].get_name())  # type: ignore
                    pll_config["vco"] = fpga_ref * pll_config["n"] / pll_config["m"]
                    pll_config["band"] = solution.get_value(config["band"].get_name())  # type: ignore
                    # pll_config["qty4_full_rate_enabled"] = solution.get_value(
                    # config["qty4_full_rate_enabled"].get_name()
                    # )
                    qty4_full_rate_divisor = solution.get_value(  # type: ignore
                        config["band"].get_name()
                    )
                    pll_config["qty4_full_rate_enabled"] = 1 - qty4_full_rate_divisor
            else:
                raise Exception("SOMETHING")
            out.append(pll_config)
        if len(out) == 1:
            out = out[0]  # type: ignore
        return out

    def _setup_quad_tile(
        self,
        converter: conv,
        fpga_ref: Union[int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar],
    ) -> Dict:
        """Configure FPGA {Q/C}PLL tile.

        Args:
            converter (conv): Converter object(s) connected to FPGA
            fpga_ref (int,GKVariable, GK_Intermediate, GK_Operators, CpoIntVar):
                Converter object(s) connected to FPGA

        Returns:
            Dict: Dictionary of clocking rates and dividers for configuration

        Raises:
            Exception: Unsupported solver
        """
        config = {}
        # QPLL
        config["m"] = self._convert_input([1, 2, 3, 4], "m")
        config["d"] = self._convert_input([1, 2, 4, 8, 16], "d")
        config["n"] = self._convert_input(self.N, "n")

        if self.solver == "gekko":
            config["vco"] = self.model.Intermediate(
                fpga_ref * config["n"] / config["m"]
            )
        elif self.solver == "CPLEX":
            config["vco"] = fpga_ref * config["n"] / config["m"]
        else:
            raise Exception(f"Unknown solver {self.solver}")

        # Define QPLL band requirements
        config["band"] = self._convert_input([0, 1], "band")

        if self.solver == "gekko":
            config["vco_max"] = self.model.Intermediate(
                config["band"] * self.vco1_max + (1 - config["band"]) * self.vco0_max
            )
            config["vco_min"] = self.model.Intermediate(
                config["band"] * self.vco1_min + (1 - config["band"]) * self.vco0_min
            )

        elif self.solver == "CPLEX":
            config["vco_max"] = (
                config["band"] * self.vco1_max + (1 - config["band"]) * self.vco0_max
            )
            config["vco_min"] = (
                config["band"] * self.vco1_min + (1 - config["band"]) * self.vco0_min
            )

        else:
            raise Exception(f"Unknown solver {self.solver}")

        # Define if we can use GTY (is available) at full rate
        if self.transciever_type != "GTY4":
            config["qty4_full_rate_divisor"] = self._convert_input(1)
        else:
            config["qty4_full_rate_divisor"] = self._convert_input([1, 2])

        if self.solver == "gekko":
            config["qty4_full_rate_enabled"] = self.model.Intermediate(
                1 - config["qty4_full_rate_divisor"]
            )
        elif self.solver == "CPLEX":
            config["qty4_full_rate_enabled"] = 1 - config["qty4_full_rate_divisor"]
        else:
            raise Exception(f"Unknown solver {self.solver}")

        #######################
        # CPLL
        config["m_cpll"] = self._convert_input([1, 2], "m_cpll")
        config["d_cpll"] = self._convert_input([1, 2, 4, 8], "d_cpll")
        config["n1_cpll"] = self._convert_input([4, 5], "n1_cpll")
        config["n2_cpll"] = self._convert_input([1, 2, 3, 4, 5], "n2_cpll")

        if self.solver == "gekko":
            config["vco_cpll"] = self.model.Intermediate(
                fpga_ref * config["n1_cpll"] * config["n2_cpll"] / config["m_cpll"]
            )
        elif self.solver == "CPLEX":
            config["vco_cpll"] = (
                fpga_ref * config["n1_cpll"] * config["n2_cpll"] / config["m_cpll"]
            )
        else:
            raise Exception(f"Unknown solver {self.solver}")

        # Merge
        if self.force_qpll and self.force_cpll:
            raise Exception("Cannot force both CPLL and QPLL")
        if self.force_qpll:
            config["qpll_0_cpll_1"] = self._convert_input(0, "qpll_0_cpll_1")
        elif self.force_cpll:
            if converter.bit_clock > self.vco_max * 2:
                raise Exception(f"CPLL too slow for lane rate. Max: {2*self.vco_max}")
            config["qpll_0_cpll_1"] = self._convert_input(1, "qpll_0_cpll_1")
        else:
            config["qpll_0_cpll_1"] = self._convert_input([0, 1], "qpll_0_cpll_1")

        if self.solver == "gekko":
            config["vco_select"] = self.model.Intermediate(
                config["qpll_0_cpll_1"] * config["vco_cpll"]
                + config["vco"] * (1 - config["qpll_0_cpll_1"])
            )
            config["vco_min_select"] = self.model.Intermediate(
                config["qpll_0_cpll_1"] * self.vco_min
                + config["vco_min"] * (1 - config["qpll_0_cpll_1"])
            )
            config["vco_max_select"] = self.model.Intermediate(
                config["qpll_0_cpll_1"] * self.vco_max
                + config["vco_max"] * (1 - config["qpll_0_cpll_1"])
            )

            config["d_select"] = self.model.Intermediate(
                config["qpll_0_cpll_1"] * config["d_cpll"]
                + (1 - config["qpll_0_cpll_1"]) * config["d"]
            )

            config["rate_divisor_select"] = self.model.Intermediate(
                config["qpll_0_cpll_1"] * (2)
                + (1 - config["qpll_0_cpll_1"]) * config["qty4_full_rate_divisor"]
            )
        elif self.solver == "CPLEX":
            config["vco_select"] = config["qpll_0_cpll_1"] * config[
                "vco_cpll"
            ] + config["vco"] * (1 - config["qpll_0_cpll_1"])

            config["vco_min_select"] = config["qpll_0_cpll_1"] * self.vco_min + config[
                "vco_min"
            ] * (1 - config["qpll_0_cpll_1"])

            config["vco_max_select"] = config["qpll_0_cpll_1"] * self.vco_max + config[
                "vco_max"
            ] * (1 - config["qpll_0_cpll_1"])

            config["d_select"] = (
                config["qpll_0_cpll_1"] * config["d_cpll"]
                + (1 - config["qpll_0_cpll_1"]) * config["d"]
            )

            config["rate_divisor_select"] = (
                config["qpll_0_cpll_1"] * (2)
                + (1 - config["qpll_0_cpll_1"]) * config["qty4_full_rate_divisor"]
            )
        else:
            raise Exception(f"Unknown solver {self.solver}")

        #######################

        # Set all relations
        # QPLL+CPLL
        self._add_equation(
            [
                config["vco_select"] >= config["vco_min_select"],
                config["vco_select"] <= config["vco_max_select"],
                config["vco_select"] * config["rate_divisor_select"]
                == converter.bit_clock * config["d_select"],
            ]
        )
        return config

    def get_required_clocks(self, converter: conv) -> List:
        """Get necessary clocks for QPLL/CPLL configuration.

        Args:
            converter (conv): Converter object of converter connected to FPGA

        Returns:
            List: List of solver variables and constraints

        Raises:
            Exception: If solver is not valid
        """
        if self.ref_clock_min == -1 or self.ref_clock_max == -1:
            raise Exception("ref_clock_min or ref_clock_max not set")
        if "_get_converters" in dir(converter):
            converter = (
                converter._get_converters()  # type: ignore
            )  # Handle nested converters

        if not isinstance(converter, list):
            converter = [converter]  # type: ignore

        if self.solver == "gekko":
            self.config = {
                "fpga_ref": self.model.Var(
                    integer=True,
                    lb=self.ref_clock_min,
                    ub=self.ref_clock_max,
                    value=self.ref_clock_min,
                )
            }
        elif self.solver == "CPLEX":
            self.config = {
                "fpga_ref": integer_var(
                    self.ref_clock_min, self.ref_clock_max, "fpga_ref"
                )
            }
        else:
            raise Exception(f"Unknown solver {self.solver}")

        # https://www.xilinx.com/support/documentation/user_guides/ug476_7Series_Transceivers.pdf

        clock_names = ["fpga_ref"]

        if self.force_single_quad_tile:
            raise Exception("force_single_quad_tile==1 not implemented")
        else:
            #######################
            self.configs = []
            self.dev_clocks = []
            obs = []
            for cnv in converter:  # type: ignore
                config = self._setup_quad_tile(cnv, self.config["fpga_ref"])
                # Set optimizations
                # self.model.Obj(self.config["d"])
                # self.model.Obj(self.config["d_cpll"])
                # self.model.Obj(config["d_select"])
                if self.solver == "gekko":
                    self.model.Obj(-1 * config["qpll_0_cpll_1"])  # Favor CPLL over QPLL
                elif self.solver == "CPLEX":
                    # FIXME
                    # self.model.maximize(config["qpll_0_cpll_1"])
                    obs.append(-1 * config["qpll_0_cpll_1"])
                else:
                    raise Exception(f"Unknown solver {self.solver}")

                self.configs.append(config)
                # FPGA also requires clock at device clock rate
                if self.request_device_clock:
                    self.dev_clocks.append(cnv.device_clock)
                    clock_names.append(cnv.name + "_fpga_device_clock")

        if self.solver == "gekko":
            self.model.Obj(self.config["fpga_ref"])
        elif self.solver == "CPLEX":
            pass
            # self.model.minimize_static_lex(obs + [self.config["fpga_ref"]])
            # self.model.maximize(obs + self.config["fpga_ref"])
        else:
            raise Exception(f"Unknown solver {self.solver}")

        self._clock_names = clock_names

        return [self.config["fpga_ref"]] + self.dev_clocks
