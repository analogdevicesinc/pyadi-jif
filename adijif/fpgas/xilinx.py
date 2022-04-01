"""Xilinx FPGA clocking model."""
from typing import Dict, List, Optional, Union

from adijif.converters.converter import converter as conv
from adijif.fpgas.xilinx_bf import xilinx_bf
from adijif.solvers import CpoSolveResult  # type: ignore
from adijif.solvers import CpoIntVar, GK_Intermediate, GK_Operators, GKVariable


class xilinx(xilinx_bf):
    """Xilinx FPGA clocking model.

    This model captures different limitations of the Xilinx
    PLLs and interfaces used for JESD.

    Currently only Zynq 7000 devices have been fully tested.
    """

    favor_cpll_over_qpll = False
    minimize_fpga_ref_clock = False

    max_serdes_lanes = 24

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
        "XCVR_CPLL",
        "XCVR_QPLL0",
        "XCVR_QPLL1",
    ]
    sys_clk_select = "XCVR_QPLL1"

    out_clk_selections = [
        "XCVR_OUTCLK_PCS",
        "XCVR_OUTCLK_PMA",
        "XCVR_REFCLK",
        "XCVR_REFCLK_DIV2",
        "XCVR_PROGDIV_CLK",
    ]
    out_clk_select = "XCVR_PROGDIV_CLK"

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

    """ Request core clock input with value of
    fpga_ref == converter.bit_clock / 40
    """
    request_fpga_core_clock_ref = False

    _clock_names: Union[List[str]] = []

    """When PROGDIV, this will be set to the value of the divider"""
    _used_progdiv = -1

    """FPGA target Fmax rate use to determine link layer output rate"""
    target_Fmax = 250e6

    configs = []  # type: ignore

    @property
    def _ref_clock_max(self) -> int:
        """Get maximum reference clock for config.

        Returns:
            int: Rate in samples per second.

        Raises:
            Exception: Unsupported transceiver type configured.
        """
        # https://www.xilinx.com/support/documentation/data_sheets/ds191-XC7Z030-XC7Z045-data-sheet.pdf # noqa: B950
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
        # https://www.xilinx.com/support/documentation/data_sheets/ds191-XC7Z030-XC7Z045-data-sheet.pdf # noqa: B950
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
            if self.sys_clk_select == "XCVR_QPLL1" and self.transciever_type in [
                "GTH3",
                "GTH4",
            ]:
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
            if self.sys_clk_select == "XCVR_QPLL1" and self.transciever_type in [
                "GTH3",
                "GTH4",
            ]:
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
        elif self.transciever_type in ["GTH3", "GTH4", "GTY4"]:
            return [16, 20, 32, 40, 64, 66, 75, 80, 100, 112, 120, 125, 150, 160]
        else:
            raise Exception(
                "Unknown N (feedback dividers) for transceiver type"
                " {}".format(self.transciever_type)
            )

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
            self.max_serdes_lanes = 8
        elif name.lower() == "zcu102":
            self.transciever_type = "GTH4"
            self.fpga_family = "Zynq"
            self.fpga_package = "FF"
            self.speed_grade = -2
            self.ref_clock_min = 60000000
            self.ref_clock_max = 820000000
            self.max_serdes_lanes = 8
        elif name.lower() == "vcu118":
            # XCVU9P-L2FLGA2104
            self.transciever_type = "GTY4"
            self.fpga_family = "Virtex"
            self.fpga_package = "FL"
            self.speed_grade = -2
            self.ref_clock_min = 60000000
            self.ref_clock_max = 820000000
            self.max_serdes_lanes = 24
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
        self,
        converter: conv,
        fpga_ref: Union[float, int],
        solution: Optional[CpoSolveResult] = None,
    ) -> Union[List[Dict], Dict]:
        """Extract configurations from solver results.

        Collect internal FPGA configuration and output clock definitions.

        Args:
            converter (conv): Converter object connected to FPGA who config is
                collected
            fpga_ref (int or float): Reference clock generated for FPGA for specific
                converter
            solution (CpoSolveResult): CPlex solution. Only needed for CPlex solver

        Returns:
            Dict: Dictionary of clocking rates and dividers for configuration
        """
        out = []
        if solution:
            self.solution = solution

        for config in self.configs:
            pll_config: Dict[str, Union[str, int, float]] = {}
            # Filter out other converters
            if converter.name + "qpll_0_cpll_1" not in config.keys():
                continue
            pll = self._get_val(config[converter.name + "qpll_0_cpll_1"])

            if pll > 0:  # type: ignore
                pll_config["type"] = "cpll"
                for k in ["m", "d", "n1", "n2"]:
                    pll_config[k] = self._get_val(config[converter.name + k + "_cpll"])

                pll_config["vco"] = (
                    fpga_ref * pll_config["n1"] * pll_config["n2"] / pll_config["m"]  # type: ignore # noqa: B950
                )
                # Check
                assert (
                    pll_config["vco"] * 2 / pll_config["d"] == converter.bit_clock  # type: ignore # noqa: B950
                ), "Invalid CPLL lane rate"
            else:
                pll_config["type"] = "qpll"
                for k in ["m", "d", "n", "band"]:
                    pll_config[k] = self._get_val(config[converter.name + k])
                pll_config["vco"] = fpga_ref * pll_config["n"] / pll_config["m"]  # type: ignore # noqa: B950
                pll_config["qty4_full_rate_enabled"] = 1 - pll_config["band"]  # type: ignore # noqa: B950
                # Check
                if self.request_fpga_core_clock_ref:
                    assert (
                        pll_config["vco"] == converter.bit_clock * pll_config["d"]  # type: ignore # noqa: B950
                    ), "Invalid QPLL lane rate {} != {}".format(
                        pll_config["vco"] / pll_config["d"], converter.bit_clock  # type: ignore # noqa: B950
                    )

            # SERDES output mux
            pll_config["sys_clk_select"] = self.sys_clk_select
            pll_config["out_clk_select"] = self.out_clk_select
            if self.out_clk_select == "XCVR_PROGDIV_CLK":
                pll_config["progdiv"] = self._used_progdiv

            out.append(pll_config)

        if len(out) == 1:
            out = out[0]  # type: ignore
        return out

    def _get_progdiv(self) -> Union[List[int], List[float]]:
        """Get programmable SERDES dividers for FPGA.

        Raises:
            Exception: PRODIV is not available for transceiver type.

        Returns:
            List[int,float]: Programmable dividers for FPGA
        """
        if self.transciever_type in ["GTY3", "GTH3"]:
            return [1, 4, 5, 8, 10, 16, 16.5, 20, 32, 33, 40, 64, 66, 80, 100]
        elif self.transciever_type in ["GTY4", "GTH4"]:
            return [1, 4, 5, 8, 10, 16, 16.5, 20, 32, 33, 40, 64, 66, 80, 100, 128, 132]
        else:
            raise Exception(
                "PROGDIV is not available for FPGA transciever type "
                + str(self.transciever_type)
            )

    def _set_link_layer_requirements(
        self,
        converter: conv,
        fpga_ref: Union[int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar],
        link_out_ref: Union[
            int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar
        ] = None,
    ) -> None:
        """Set link layer constraints for downstream FPGA logic.

        The link layer is driven from the XCVR core which can route the
        following signals to the link layer input:
        - External Ref
        - External Ref / 2
        - {CPLL,QPLL0,QPLL1} / PROGDIV

        The link layer input has a hard requirement that is must be at:
        - JESD204B: lane rate (bit clock) / 40 or lane rate (bit clock) / 80
        - JESD204C: lane rate (bit clock) / 60

        The link layer output rate will be equivalent to sample clock / N, where
        N is an integer. Note the smaller N, the more channeling it can be to
        synthesize the design. This output clock can be separate or be the same
        as the XCVR reference.

        Based on this info, we set up the problem where we define N (sample per
        clock increase), and set the lane rate based on the current converter
        JESD config.

        Args:
            converter (conv): Converter object connected to FPGA
            fpga_ref (int or GKVariable): Reference clock generated for FPGA
            link_out_ref (int or GKVariable): Reference clock generated for FPGA
                link layer output

        Raises:
            Exception: Link layer output clock select invalid
        """
        if converter.jesd_class == "jesd204b":
            link_layer_input_rate = converter.bit_clock / 40
        elif converter.jesd_class == "jesd204c":
            link_layer_input_rate = converter.bit_clock / 60

        if self.out_clk_select == "XCVR_REFCLK":
            self._add_equation([fpga_ref == link_layer_input_rate])
        elif self.out_clk_select == "XCVR_REFCLK_DIV2":
            self._add_equation([fpga_ref == link_layer_input_rate * 2])
        elif self.out_clk_select == "XCVR_PROGDIV_CLK":
            progdiv = self._get_progdiv()
            div = converter.bit_clock / link_layer_input_rate
            if div not in progdiv:
                raise Exception(
                    f"Cannot use PROGDIV since required divider {div},"
                    + f" only available {progdiv}"
                )
            self._used_progdiv = div
        else:
            raise Exception(
                "Invalid (or unsupported) link layer output clock selection "
                + str(self.out_clk_select)
            )

        if link_out_ref:
            # Set link clock output rate to be below FPGA Fmax
            for samples_per_clock in [1, 2, 4, 8, 16]:
                if converter.sample_clock / samples_per_clock <= self.target_Fmax:
                    self._add_equation(
                        [link_out_ref == converter.sample_clock / samples_per_clock]
                    )

    def _setup_quad_tile(
        self,
        converter: conv,
        fpga_ref: Union[int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar],
        link_out_ref: Union[
            None, int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar
        ] = None,
    ) -> Dict:
        """Configure FPGA {Q/C}PLL tile.

        Args:
            converter (conv): Converter object(s) connected to FPGA
            fpga_ref (int,GKVariable, GK_Intermediate, GK_Operators, CpoIntVar):
                Reference clock for FPGA
            link_out_ref (None, int,GKVariable, GK_Intermediate, GK_Operators,
                CpoIntVar): Link layer output reference clock

        Returns:
            Dict: Dictionary of clocking rates and dividers for configuration

        Raises:
            Exception: Unsupported solver
        """
        # CPLL -> VCO = FPGA_REF * N1*N2/M
        #         PLLOUT = VCO
        #         LR  = PLLOUT * 2/D
        #         LR  = FPGA_REF * N1*N2*2/(M*D)
        #
        # QPLL -> VCO = FPGA_REF * N/(M*2)
        #         PLLOUT = VCO/2
        #         LR  = PLLOUT * 2/D
        #         LR  = FPGA_REF * N/(M*D)
        config = {}
        # QPLL
        config[converter.name + "m"] = self._convert_input(
            [1, 2, 3, 4], converter.name + "m"
        )
        config[converter.name + "d"] = self._convert_input(
            [1, 2, 4, 8, 16], converter.name + "d"
        )
        config[converter.name + "n"] = self._convert_input(self.N, converter.name + "n")

        config[converter.name + "vco"] = self._add_intermediate(
            fpga_ref * config[converter.name + "n"] / (config[converter.name + "m"])
        )

        # Define QPLL band requirements
        config[converter.name + "band"] = self._convert_input(
            [0, 1], converter.name + "band"
        )

        config[converter.name + "vco_max"] = self._add_intermediate(
            config[converter.name + "band"] * self.vco1_max
            + (1 - config[converter.name + "band"]) * self.vco0_max
        )
        config[converter.name + "vco_min"] = self._add_intermediate(
            config[converter.name + "band"] * self.vco1_min
            + (1 - config[converter.name + "band"]) * self.vco0_min
        )

        # Define if we can use GTY (is available) at full rate
        if self.transciever_type != "GTY4":
            config[converter.name + "qty4_full_rate_divisor"] = self._convert_input(
                1, name=converter.name + "qty4_full_rate_divisor"
            )
        else:
            config[converter.name + "qty4_full_rate_divisor"] = self._convert_input(
                [1, 2], name=converter.name + "qty4_full_rate_divisor"
            )

        config[converter.name + "qty4_full_rate_enabled"] = self._add_intermediate(
            1 - config[converter.name + "qty4_full_rate_divisor"]
        )

        #######################
        # CPLL
        # CPLL -> VCO = FPGA_REF * N1*N2/M
        #         LR  = VCO * 2/D
        #         LR  = FPGA_REF * N1*N2*2/(M*D)
        config[converter.name + "m_cpll"] = self._convert_input(
            [1, 2], converter.name + "m_cpll"
        )
        config[converter.name + "d_cpll"] = self._convert_input(
            [1, 2, 4, 8], converter.name + "d_cpll"
        )
        config[converter.name + "n1_cpll"] = self._convert_input(
            [4, 5], converter.name + "n1_cpll"
        )
        config[converter.name + "n2_cpll"] = self._convert_input(
            [1, 2, 3, 4, 5], converter.name + "n2_cpll"
        )

        config[converter.name + "vco_cpll"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + "n1_cpll"]
            * config[converter.name + "n2_cpll"]
            / config[converter.name + "m_cpll"]
        )

        # Merge
        if self.force_qpll and self.force_cpll:
            raise Exception("Cannot force both CPLL and QPLL")
        if self.force_qpll:
            config[converter.name + "qpll_0_cpll_1"] = self._convert_input(
                0, converter.name + "qpll_0_cpll_1"
            )
        elif self.force_cpll:
            if converter.bit_clock > self.vco_max * 2:
                raise Exception(f"CPLL too slow for lane rate. Max: {2*self.vco_max}")
            config[converter.name + "qpll_0_cpll_1"] = self._convert_input(
                1, converter.name + "qpll_0_cpll_1"
            )
        else:
            config[converter.name + "qpll_0_cpll_1"] = self._convert_input(
                [0, 1], converter.name + "qpll_0_cpll_1"
            )

        config[converter.name + "vco_select"] = self._add_intermediate(
            config[converter.name + "qpll_0_cpll_1"]
            * config[converter.name + "vco_cpll"]
            + config[converter.name + "vco"]
            * (1 - config[converter.name + "qpll_0_cpll_1"])
        )
        config[converter.name + "vco_min_select"] = self._add_intermediate(
            config[converter.name + "qpll_0_cpll_1"] * self.vco_min
            + config[converter.name + "vco_min"]
            * (1 - config[converter.name + "qpll_0_cpll_1"])
        )
        config[converter.name + "vco_max_select"] = self._add_intermediate(
            config[converter.name + "qpll_0_cpll_1"] * self.vco_max
            + config[converter.name + "vco_max"]
            * (1 - config[converter.name + "qpll_0_cpll_1"])
        )

        config[converter.name + "d_select"] = self._add_intermediate(
            config[converter.name + "qpll_0_cpll_1"] * config[converter.name + "d_cpll"]
            + (1 - config[converter.name + "qpll_0_cpll_1"])
            * config[converter.name + "d"]
        )
        # Note: QPLL has extra /2 after VCO so:
        #       QPLL: lanerate == vco/d
        #       CPLL: lanerate == vco*2/d
        config[converter.name + "rate_divisor_select"] = self._add_intermediate(
            config[converter.name + "qpll_0_cpll_1"] * (2)
            + (1 - config[converter.name + "qpll_0_cpll_1"])
            * config[converter.name + "qty4_full_rate_divisor"]
        )

        #######################

        # Set all relations
        # QPLL+CPLL
        #
        # CPLL -> VCO = FPGA_REF * N1*N2/M
        #         PLLOUT = VCO
        #         LR  = PLLOUT * 2/D
        #         LR  = FPGA_REF * N1*N2*2/(M*D)
        #
        # QPLL -> VCO = FPGA_REF * N/(M)
        #         PLLOUT = VCO/2
        #         LR  = PLLOUT * 2/D
        #         LR  = FPGA_REF * N/(M*D)
        #
        #  LR = FPGA_REF*(A*N1*N2*2/(M*D) + (A-1)*N/(M*D))
        #    A = 0,1
        #  LR*D*M = FPGA_REF*(A*N1*N2*2 + (A-1)*N)

        self._add_equation(
            [
                config[converter.name + "vco_select"]
                >= config[converter.name + "vco_min_select"],
                config[converter.name + "vco_select"]
                <= config[converter.name + "vco_max_select"],
                # CPLL
                # converter.bit_clock == vco * 2 / d
                # QPLL
                # converter.bit_clock == vco / d
                config[converter.name + "vco_select"]
                * config[converter.name + "rate_divisor_select"]
                == converter.bit_clock * config[converter.name + "d_select"],
            ]
        )

        self._set_link_layer_requirements(converter, fpga_ref, link_out_ref)

        return config

    def get_required_clocks(
        self,
        converter: conv,
        fpga_ref: Union[int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar],
    ) -> List:
        """Get necessary clocks for QPLL/CPLL configuration.

        Args:
            converter (conv): Converter object of converter connected to FPGA
            fpga_ref (int, GKVariable, GK_Intermediate, GK_Operators,
                CpoIntVar): Abstract or concrete reference to FPGA reference
                clock

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

        # if self.solver == "gekko":
        #     self.config = {
        #         "fpga_ref": self.model.Var(
        #             # integer=True,
        #             lb=self.ref_clock_min,
        #             ub=self.ref_clock_max,
        #             value=self.ref_clock_min,
        #         )
        #     }
        # elif self.solver == "CPLEX":
        #     # self.config = {
        #     #     "fpga_ref": integer_var(
        #     #         self.ref_clock_min, self.ref_clock_max, "fpga_ref"
        #     #     )
        #     # }
        #     pass
        # else:
        #     raise Exception(f"Unknown solver {self.solver}")

        # https://www.xilinx.com/support/documentation/user_guides/ug476_7Series_Transceivers.pdf # noqa: B950

        # clock_names = ["fpga_ref"]
        clock_names = []
        self.config = {}
        if self.force_single_quad_tile:
            raise Exception("force_single_quad_tile==1 not implemented")
        else:
            #######################
            # self.configs = []
            self.dev_clocks = []
            self.ref_clocks = []
            # obs = []
            for cnv in converter:  # type: ignore
                clock_names.append(cnv.name + "fpga_ref")
                # self.config[cnv.name+"fpga_ref"] = interval_var(
                #     self.ref_clock_min, self.ref_clock_max, name=cnv.name+"fpga_ref"
                # )
                self.config[cnv.name + "fpga_ref"] = fpga_ref
                self.ref_clocks.append(self.config[cnv.name + "fpga_ref"])
                config = self._setup_quad_tile(cnv, self.config[cnv.name + "fpga_ref"])
                # Set optimizations
                # self.model.Obj(self.config[converter.name+"d"])
                # self.model.Obj(self.config[converter.name+"d_cpll"])
                # self.model.Obj(config[converter.name+"d_select"])
                if self.favor_cpll_over_qpll:
                    if self.solver == "gekko":
                        self.model.Obj(
                            -1 * config[cnv.name + "qpll_0_cpll_1"]
                        )  # Favor CPLL over QPLL
                    elif self.solver == "CPLEX":
                        self.model.maximize(config[cnv.name + "qpll_0_cpll_1"])
                        # obs.append(-1 * config[cnv.name + "qpll_0_cpll_1"])
                    else:
                        raise Exception(f"Unknown solver {self.solver}")

                self.configs.append(config)
                # FPGA also requires clock at device clock rate
                if self.request_device_clock:
                    self.dev_clocks.append(cnv.device_clock)
                    clock_names.append(cnv.name + "_fpga_device_clock")

        if self.minimize_fpga_ref_clock:
            if self.solver == "gekko":
                self.model.Obj(self.config[cnv.name + "fpga_ref"])
            elif self.solver == "CPLEX":
                # self.model.minimize_static_lex(obs + [self.config[converter.name+"fpga_ref"]]) # noqa: B950
                self.model.minimize(self.config[cnv.name + "fpga_ref"])  # noqa: B950
                # self.model.maximize(obs + self.config[converter.name+"fpga_ref"])
            else:
                raise Exception(f"Unknown solver {self.solver}")

        self._clock_names = clock_names

        # return [self.config["fpga_ref"]] + self.dev_clocks
        return self.ref_clocks + self.dev_clocks
