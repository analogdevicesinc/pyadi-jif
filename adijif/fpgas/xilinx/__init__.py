"""Xilinx FPGA clocking model."""

from typing import Dict, List, Optional, Union

from docplex.cp.modeler import if_then

from ...converters.converter import converter as conv
from ...solvers import (
    CpoIntVar,
    CpoSolveResult,
    GK_Intermediate,
    GK_Operators,
    GKVariable,
)
from .bf import xilinx_bf
from .sevenseries import SevenSeries as SSTransceiver
from .ultrascaleplus import UltraScalePlus as USPTransceiver
from .xilinx_draw import xilinx_draw


class xilinx(xilinx_bf, xilinx_draw):
    """Xilinx FPGA clocking model.

    This model captures different limitations of the Xilinx
    PLLs and interfaces used for JESD.

    Currently only Zynq 7000 devices have been fully tested.
    """

    name = "Xilinx-FPGA"

    favor_cpll_over_qpll = False
    minimize_fpga_ref_clock = False

    """Force generation of separate device clock from the clock chip. In many
    cases, the ref clock and device clock can be the same."""
    force_separate_device_clock: bool = False

    """Constrain reference clock to be specific values. Options:
    - CORE_CLOCK: Make reference clock the same as the core clock (LR/40 or LR/66)
    - CORE_CLOCK_DIV2: Make reference clock the same as the core clock divided by 2
    - Unconstrained: No constraints on reference clock. Simply meet PLL constraints
    """
    _ref_clock_constraint = "CORE_CLOCK"

    max_serdes_lanes = 24

    hdl_core_version = 2.1

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

    available_transceiver_types = ["GTXE2"]
    transceiver_type = "GTXE2"

    def trx_gen(self) -> int:
        """Get transceiver generation (2,3,4).

        Returns:
            int: generation of transceiver
        """
        return int(self.transceiver_type[-1])

    def trx_variant(self) -> str:
        """Get transceiver variant (GTX, GTH, GTY, ...).

        Returns:
            str: Transceiver variant
        """
        # return self.transceiver_type[:2]
        trxt = self.transceiver_type[:2]
        assert len(trxt) == 3
        return trxt

    def fpga_generation(self) -> str:
        """Get FPGA generation 7000, US, US+... based on transceiver type.

        Returns:
            str: FPGA generation

        Raises:
            Exception: Unknown transceiver generation
        """
        if self.trx_gen() == 2:
            return "7000"
        elif self.trx_gen() == 3:
            return "Ultrascale"
        elif self.trx_gen() == 4:
            return "Ultrascale+"
        elif self.trx_gen() == 5:
            return "Versal"
        raise Exception(f"Unknown transceiver generation {self.trx_gen()}")

    sys_clk_selections = [
        "XCVR_CPLL",
        "XCVR_QPLL0",
        "XCVR_QPLL1",
    ]
    sys_clk_select = "XCVR_QPLL1"

    _out_clk_selections = [
        # "XCVR_OUTCLK_PCS",
        # "XCVR_OUTCLK_PMA",
        "XCVR_REFCLK",
        "XCVR_REFCLK_DIV2",
        "XCVR_PROGDIV_CLK",
    ]
    _out_clk_select = [
        # "XCVR_OUTCLK_PCS",
        # "XCVR_OUTCLK_PMA",
        "XCVR_REFCLK",
        "XCVR_REFCLK_DIV2",
        "XCVR_PROGDIV_CLK",
    ]

    """ Force use of QPLL for transceiver source """
    force_qpll = False

    """ Force use of QPLL1 for transceiver source (GTHE3,GTHE4,GTYE4)"""
    force_qpll1 = False

    """ Force use of CPLL for transceiver source """
    force_cpll = False

    """ Force all transceiver sources to be from a single PLL quad.
        This will try to leverage the output dividers of the PLLs
    """
    force_single_quad_tile = False

    """ Request that clock chip generated device clock
        device clock == LMFC/40
        NOTE: THIS IS NOT FPGA REF CLOCK
    """
    request_device_clock = False

    _clock_names: List[str] = []

    """When PROGDIV, this will be set to the value of the divider"""
    _used_progdiv = {}

    """FPGA target Fmax rate use to determine link layer output rate"""
    target_Fmax = 500e6

    """Device and reference clock relation"""
    _device_clock_and_ref_clock_relation_options = [
        "NA",
        "ref_clock_2x_device_clock",
        "ref_clock_eq_device_clock",
    ]
    _device_clock_and_ref_clock_relation = "NA"

    @property
    def device_clock_and_ref_clock_relation(self) -> str:
        """Get device clock and reference clock relation.

        Device clock and reference clock relation can be set to:
        - NA: No relation
        - ref_clock_2x_device_clock: Reference clock is 2x device clock
        - ref_clock_eq_device_clock: Reference clock is equal to device clock

        Returns:
            str: Device clock and reference clock relation.
        """
        return self._device_clock_and_ref_clock_relation

    @device_clock_and_ref_clock_relation.setter
    def device_clock_and_ref_clock_relation(self, value: str) -> None:
        """Set device clock and reference clock relation.

        Device clock and reference clock relation can be set to:
        - NA: No relation
        - ref_clock_2x_device_clock: Reference clock is 2x device clock
        - ref_clock_eq_device_clock: Reference clock is equal to device clock

        Args:
            value (str): Device clock and reference clock relation.

        Raises:
            Exception: Invalid device clock and reference clock relation selection.
        """
        if value not in self._device_clock_and_ref_clock_relation_options:
            raise Exception(
                f"Invalid device_clock_and_ref_clock_relation {value}, "
                + f"options are {self._device_clock_and_ref_clock_relation_options}"
            )
        self._device_clock_and_ref_clock_relation = value

    # """Require generation of separate clock specifically for link layer"""
    # requires_separate_link_layer_out_clock = True

    """Require generation of separate core clock (LR/40 or LR/66)"""
    requires_core_clock_from_device_clock = False

    _device_clock_source_options = ["external", "link_clock", "ref_clock"]
    _device_clock_source = ["external"]

    configs = []  # type: ignore
    _transceiver_models = {}  # type: ignore

    @property
    def device_clock_source(self) -> str:
        """Get device clock source.

        Device clock source can be set to:
        - external: External clock from clock chip
        - link_clock: Link layer clock is reused for as device clock
        - ref_clock: Reference clock is reused for device clock

        Returns:
            str: Device clock source.
        """
        return self._device_clock_source

    @device_clock_source.setter
    def device_clock_source(self, value: Union[str, List[str]]) -> None:
        """Set device clock source.

        Device clock source can be set to:
        - external: External clock
        - link_clock: Link layer clock
        - ref_clock: Reference clock

        Args:
            value (str, List[str]): Device clock source.

        Raises:
            Exception: Invalid device clock source selection.
        """
        if not isinstance(value, list):
            value = [value]
        for item in value:
            if item not in self._device_clock_source_options:
                raise Exception(
                    f"Invalid device clock source {item}, "
                    + f"options are {self._device_clock_source_options}"
                )
        self._device_clock_source = value

    @property
    def ref_clock_constraint(self) -> str:
        """Get reference clock constraint.

        Reference clock constraint can be set to:
        - CORE_CLOCK: Make reference clock the same as the core clock (LR/40 or LR/66)
        - CORE_CLOCK_DIV2: Make reference clock the same as the core clock divided by 2
        - Unconstrained: No constraints on reference clock. Simply meet PLL constraints

        Returns:
            str: Reference clock constraint.
        """
        return self._ref_clock_constraint

    @ref_clock_constraint.setter
    def ref_clock_constraint(self, value: str) -> None:
        """Set reference clock constraint.

        Reference clock constraint can be set to:
        - CORE_CLOCK: Make reference clock the same as the core clock (LR/40 or LR/66)
        - CORE_CLOCK_DIV2: Make reference clock the same as the core clock divided by 2
        - Unconstrained: No constraints on reference clock. Simply meet PLL constraints

        Args:
            value (str): Reference clock constraint.

        Raises:
            Exception: Invalid ref_clock_constraint selection.
        """
        if value not in ["CORE_CLOCK", "CORE_CLOCK_DIV2", "Unconstrained"]:
            raise Exception(
                f"Invalid ref_clock_constraint {value}, "
                + "options are CORE_CLOCK, CORE_CLOCK_DIV2, Unconstrained"
            )
        self._ref_clock_constraint = value

    @property
    def out_clk_select(self) -> Union[int, float]:
        """Get current PLL clock output mux options for link layer clock.

        Valid options are: "XCVR_REFCLK", "XCVR_REFCLK_DIV2", "XCVR_PROGDIV_CLK"
        If a list of these is provided, the solver will determine one to use.

        Returns:
            str, list(str): Mux selection for link layer clock.
        """
        return self._out_clk_select

    @out_clk_select.setter
    def out_clk_select(self, value: Union[str, List[str]]) -> None:
        """Set current PLL clock output mux options for link layer clock.

        Valid options are: "XCVR_REFCLK", "XCVR_REFCLK_DIV2", "XCVR_PROGDIV_CLK"
        If a list of these is provided, the solver will determine one to use.

        Args:
            value (str, List[str]): Mux selection for link layer clock.

        Raises:
            Exception: Invalid out_clk_select selection.
        """
        if isinstance(value, list):
            for item in value:
                if item not in self._out_clk_selections:
                    raise Exception(
                        f"Invalid out_clk_select {item}, "
                        + f"options are {self._out_clk_selections}"
                    )
        elif isinstance(value, dict):
            for converter in value:
                if not isinstance(converter, conv):
                    raise Exception("Keys of out_clk_select but be of type converter")
                if value[converter] not in self._out_clk_selections:
                    raise Exception(
                        f"Invalid out_clk_select {value[converter]}, "
                        + f"options are {self._out_clk_selections}"
                    )
        elif value not in self._out_clk_selections:  # str
            raise Exception(
                f"Invalid out_clk_select {value}, "
                + f"options are {self._out_clk_selections}"
            )

        self._out_clk_select = value

    @property
    def _ref_clock_max(self) -> int:
        """Get maximum reference clock for config.

        Returns:
            int: Rate in samples per second.

        Raises:
            Exception: Unsupported transceiver type configured.
        """
        # https://www.xilinx.com/support/documentation/data_sheets/ds191-XC7Z030-XC7Z045-data-sheet.pdf # noqa: B950
        if self.transceiver_type == "GTXE2":
            if str(self.speed_grade) == "-3E":
                return 700000000
            else:
                return 670000000
        else:
            raise Exception(
                f"Unknown ref_clock_max for transceiver type {self.transceiver_type}"
            )
            # raise Exception(f"Unknown transceiver type {self.transceiver_type}")

    @property
    def _ref_clock_min(self) -> int:
        """Get minimum reference clock for config.

        Returns:
            int: Rate in samples per second.

        Raises:
            Exception: Unsupported transceiver type configured.
        """
        # https://www.xilinx.com/support/documentation/data_sheets/ds191-XC7Z030-XC7Z045-data-sheet.pdf # noqa: B950
        if self.transceiver_type == "GTXE2":
            return 60000000
        else:
            raise Exception(
                f"Unknown ref_clock_min for transceiver type {self.transceiver_type}"
            )
            # raise Exception(f"Unknown transceiver type {self.transceiver_type}")

    _available_dev_kit_names = [
        "zcu102",
        "zc706",
        "vcu118",
        "adsy1100",
    ]

    def setup_by_dev_kit_name(self, name: str) -> None:
        """Configure object based on board name. Ex: zc706, zcu102.

        Args:
            name (str): Name of dev kit. Ex: zc706, zcu102

        Raises:
            Exception: Unsupported board requested.

        """
        if name.lower() == "zc706":
            self.transceiver_type = "GTXE2"
            self.fpga_family = "Zynq"
            self.fpga_package = "FF"
            self.speed_grade = -2
            self.ref_clock_min = 60000000
            self.ref_clock_max = 670000000
            self.max_serdes_lanes = 8
            # default PROGDIV not available
            o = self._out_clk_selections.copy()
            del o[o.index("XCVR_PROGDIV_CLK")]
            self._out_clk_selections = o
            self._out_clk_select = o
        elif name.lower() == "zcu102":
            self.transceiver_type = "GTHE4"
            self.fpga_family = "Zynq"
            self.fpga_package = "FF"
            self.speed_grade = -2
            self.ref_clock_min = 60000000
            self.ref_clock_max = 820000000
            self.max_serdes_lanes = 8
        elif name.lower() == "vcu118":
            # XCVU9P-L2FLGA2104
            self.transceiver_type = "GTYE4"
            self.fpga_family = "Virtex"
            self.fpga_package = "FL"
            self.speed_grade = -2
            self.ref_clock_min = 60000000
            self.ref_clock_max = 820000000
            self.max_serdes_lanes = 24
        elif name.lower() == "adsy1100":
            # ADI VPX Module
            # VU11P: xcvu11p-flgb2104-2-i
            self.transceiver_type = "GTYE4"
            self.fpga_family = "Virtex"
            self.fpga_package = "FL"
            self.speed_grade = -2
            self.ref_clock_min = 60000000  # NEED TO VERIFY
            self.ref_clock_max = 820000000  # NEED TO VERIFY
            self.max_serdes_lanes = 24  # Connected to AD9084
        else:
            raise Exception(f"No boardname found in library for {name}")
        self.name = name

    def determine_pll(self, bit_clock: int, fpga_ref_clock: int) -> Dict:
        """Determine if configuration is possible with CPLL or QPLL.

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
        except:  # noqa: B001
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
            solution (CpoSolveResult): CPlex solution and only needed for CPlex
                solver

        Returns:
            Dict: Dictionary of clocking rates and dividers for configuration.

        Raises:
            Exception: Invalid PLL configuration.
        """
        out = []
        if solution:
            self.solution = solution

        self._saved_solution = solution  # needed for draw

        for config in self.configs:
            pll_config: Dict[str, Union[str, int, float]] = {}

            # Filter out other converters
            # FIXME: REIMPLEMENT BETTER
            if converter.name + "_use_cpll" not in config.keys():
                print("Continued")
                continue

            pll_config = self._transceiver_models[converter.name].get_config(
                config, converter, fpga_ref
            )
            # cpll = self._get_val(config[converter.name + "_use_cpll"])
            # qpll = self._get_val(config[converter.name + "_use_qpll"])
            # if converter.name + "_use_qpll1" in config.keys():
            #     qpll1 = self._get_val(config[converter.name + "_use_qpll1"])
            # else:
            #     qpll1 = False

            # SERDES output mux
            if pll_config["type"] == "cpll":
                pll_config["sys_clk_select"] = "XCVR_CPLL"
            elif pll_config["type"] == "qpll":
                pll_config["sys_clk_select"] = "XCVR_QPLL0"
            elif pll_config["type"] == "qpll1":
                pll_config["sys_clk_select"] = "XCVR_QPLL1"
            else:
                raise Exception("Invalid PLL type")

            pll_config["out_clk_select"] = self._get_val(
                config[converter.name + "_out_clk_select"]
            )
            pll_config["out_clk_select"] = self._out_clk_selections[
                pll_config["out_clk_select"]
            ]

            if pll_config["out_clk_select"] == "XCVR_PROGDIV_CLK":
                progdiv = self._get_val(config[converter.name + "_progdiv_times2"])
                if float(int(progdiv / 2) * 2) != float(progdiv):
                    raise Exception(
                        f"PROGDIV divider {progdiv} is not an integer, "
                        + "this is not supported by the solver"
                    )
                progdiv = progdiv / 2
                progdiv = int(progdiv)

                # Check if we need progdiv really
                if progdiv == 1 and "XCVR_REFCLK" in self._out_clk_select:
                    # Change to XCVR_REFCLK
                    pll_config["out_clk_select"] = "XCVR_REFCLK"
                elif progdiv == 2 and "XCVR_REFCLK_DIV2" in self._out_clk_select:
                    # Change to XCVR_REFCLK_DIV2
                    pll_config["out_clk_select"] = "XCVR_REFCLK_DIV2"
                else:
                    if progdiv not in self._get_progdiv():
                        raise Exception(
                            f"PROGDIV divider {progdiv} not available for "
                            + f"transceiver type {self.transceiver_type}"
                        )
                    pll_config["progdiv"] = progdiv

            source = self._get_val(config[converter.name + "_device_clock_source"])
            pll_config["device_clock_source"] = self._device_clock_source_options[
                source
            ]

            if converter.jesd_class == "jesd204b":
                sps = converter.L * 32 / (converter.M * converter.Np)
            elif converter.jesd_class == "jesd204c":
                sps = converter.L * 64 / (converter.M * converter.Np)
            else:
                raise Exception("Invalid JESD class")
            pll_config["transport_samples_per_clock"] = sps

            out.append(pll_config)

        if len(out) == 1:
            out = out[0]  # type: ignore
        return out

    def _get_conv_prop(
        self, conv: conv, prop: Union[str, dict]
    ) -> Union[int, float, str]:
        """Helper to extract nested properties if present.

        Args:
            conv (conv): Converter object
            prop (str,dict): Property to extract

        Raises:
            Exception: Converter does not have property

        Returns:
            Union[int,float,str]: Value of property
        """
        if isinstance(prop, dict):
            if conv not in prop:
                raise Exception(f"Converter {conv.name} not found in config")
            return prop[conv]
        return prop

    def _get_progdiv(self) -> Union[List[int], List[float]]:
        """Get programmable SERDES dividers for FPGA.

        Raises:
            Exception: PRODIV is not available for transceiver type.

        Returns:
            List[int,float]: Programmable dividers for FPGA
        """
        if self.transceiver_type in ["GTYE3", "GTHE3"]:
            return [1, 4, 5, 8, 10, 16, 16.5, 20, 32, 33, 40, 64, 66, 80, 100]
        elif self.transceiver_type in ["GTYE4", "GTHE4"]:
            return [
                1,
                4,
                5,
                8,
                10,
                16,
                16.5,
                20,
                32,
                33,
                40,
                64,
                66,
                80,
                100,
                128,
                132,
            ]
        else:
            raise Exception(
                "PROGDIV is not available for FPGA transciever type "
                + str(self.transceiver_type)
            )

    def _set_link_layer_requirements(
        self,
        converter: conv,
        fpga_ref: Union[int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar],
        config: Dict,
        link_out_ref: Union[
            int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar
        ] = None,
    ) -> Dict:
        """Set link layer constraints for downstream FPGA logic.

        The link layer is driven from the XCVR core which can route the
        following signals to the link layer input:
        - External Ref
        - External Ref / 2
        - {CPLL,QPLL0,QPLL1} / PROGDIV

        The link layer input has a hard requirement that is must be at:
        - JESD204B: lane rate (bit clock) / 40 or lane rate (bit clock) / 80
        - JESD204C: lane rate (bit clock) / 66

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
            config (Dict): Dictionary of clocking rates and dividers for link
                layer
            link_out_ref (int or GKVariable): Reference clock generated for FPGA
                link layer output

        Returns:
            Dict: Dictionary of clocking rates extended with dividers for link
                layer

        Raises:
            Exception: Link layer output clock select invalid
        """
        if converter.jesd_class == "jesd204b":
            link_layer_input_rate = converter.bit_clock / 40
        elif converter.jesd_class == "jesd204c":
            link_layer_input_rate = converter.bit_clock / 66

        if isinstance(self.out_clk_select, dict):
            if converter not in self.out_clk_select.keys():
                raise Exception(
                    "Link layer out_clk_select invalid for converter " + converter.name
                )
            if isinstance(self.out_clk_select[converter], dict):
                out_clk_select = self.out_clk_select[converter].copy()
            else:
                out_clk_select = self.out_clk_select[converter]
        else:
            out_clk_select = self.out_clk_select

        out_clk_select_options = []
        if "XCVR_REFCLK" in out_clk_select:
            out_clk_select_options.append(0)
        if "XCVR_REFCLK_DIV2" in out_clk_select:
            out_clk_select_options.append(1)
        if "XCVR_PROGDIV_CLK" in out_clk_select:
            out_clk_select_options.append(2)

        # Quick check for progdiv since it doesn't require the solver
        if "XCVR_PROGDIV_CLK" in out_clk_select and len(out_clk_select) == 1:
            progdiv = self._get_progdiv()
            div = converter.bit_clock / link_layer_input_rate
            if div not in progdiv:
                raise Exception(
                    f"Cannot use PROGDIV since required divider {div},"
                    + f" only available {progdiv}"
                )

        config[converter.name + "_out_clk_select"] = self._convert_input(
            out_clk_select_options, converter.name + "_out_clk_select"
        )

        if "XCVR_PROGDIV_CLK" in out_clk_select:
            progdiv = self._get_progdiv()
            progdiv_times2 = [i * 2 for i in progdiv]
            # Check that casting to int is valid
            for i in progdiv_times2:
                if i != int(i):
                    raise Exception(
                        f"PROGDIV times 2 divider {i} is not an integer, "
                        + "this is not supported by the solver"
                    )
            progdiv_times2 = [int(i) for i in progdiv_times2]
            config[converter.name + "_progdiv_times2"] = self._convert_input(
                progdiv_times2, converter.name + "_progdiv"
            )

        self._add_equation(
            [
                if_then(
                    config[converter.name + "_out_clk_select"] == 0,  # XCVR_REFCLK
                    fpga_ref == link_layer_input_rate,
                ),
                if_then(
                    config[converter.name + "_out_clk_select"] == 1,  # XCVR_REFCLK_DIV2
                    fpga_ref == link_layer_input_rate * 2,
                ),
            ]
        )

        if "XCVR_PROGDIV_CLK" in out_clk_select:
            self._add_equation(
                [
                    if_then(
                        config[converter.name + "_out_clk_select"]
                        == 2,  # XCVR_PROGDIV_CLK
                        converter.bit_clock * 2
                        == link_layer_input_rate
                        * config[converter.name + "_progdiv_times2"],
                    ),
                ]
            )

        return config, link_layer_input_rate

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
        # Add reference clock constraints
        self._add_equation(
            [fpga_ref >= self.ref_clock_min, fpga_ref <= self.ref_clock_max]
        )

        if converter.jesd_class == "jesd204b":
            core_clock = converter.bit_clock / 40
        else:
            core_clock = converter.bit_clock / 66

        if self.ref_clock_constraint == "CORE_CLOCK":
            self._add_equation([fpga_ref == core_clock])
        elif self.ref_clock_constraint == "CORE_CLOCK_DIV2":
            self._add_equation([fpga_ref == core_clock / 2])

        # Add transceiver
        config = {}
        if self.fpga_generation() == "7000":
            self._transceiver_models[converter.name] = SSTransceiver(
                parent=self,
                transceiver_type=self.transceiver_type,
                speed_grade=self.speed_grade,
            )
        elif self.fpga_generation() in ["Ultrascale", "Ultrascale+"]:
            self._transceiver_models[converter.name] = USPTransceiver(
                parent=self,
                transceiver_type=self.transceiver_type,
                speed_grade=self.speed_grade,
            )
        else:
            raise Exception(f"Unsupported FPGA generation {self.fpga_generation()}")

        # Handle force PLLs for nested devices and multiple converters
        force_cpll = False
        force_qpll = False
        force_qpll1 = False

        if isinstance(self.force_cpll, dict):
            if converter in self.force_cpll:
                force_cpll = self.force_cpll[converter]
        else:
            force_cpll = self.force_cpll

        if isinstance(self.force_qpll, dict):
            if converter in self.force_qpll:
                force_qpll = self.force_qpll[converter]
        else:
            force_qpll = self.force_qpll

        if isinstance(self.force_qpll1, dict):
            if converter in self.force_qpll1:
                force_qpll1 = self.force_qpll1[converter]
        else:
            force_qpll1 = self.force_qpll1

        self._transceiver_models[converter.name].force_cpll = force_cpll
        self._transceiver_models[converter.name].force_qpll = force_qpll
        if hasattr(self._transceiver_models[converter.name], "force_qpll1"):
            self._transceiver_models[converter.name].force_qpll1 = force_qpll1

        config = self._transceiver_models[converter.name].add_constraints(
            config, fpga_ref, converter
        )

        # Add constraints for link clock and transport clock
        # Link clock in must be lane rate / 40 or lane rate / 66
        # Link clock out and transport must be sample rate / SPS

        # Add constraints for link clock input
        config, link_layer_input_rate = self._set_link_layer_requirements(
            converter, fpga_ref, config, None
        )

        # Add device clock constraints
        # Device clock drives the output clock for the link layer and the
        # transport clock. It is sample_rates / SPS
        if converter.jesd_class == "jesd204b":
            sps = converter.L * 32 / (converter.M * converter.Np)
        elif converter.jesd_class == "jesd204c":
            sps = converter.L * 64 / (converter.M * converter.Np)

        device_clock_rate = converter.sample_clock / sps

        # Quick check for non-solver case(s)
        if (
            len(self._device_clock_source) == 1
            and self._device_clock_source[0] == "link_clock"
            and device_clock_rate != link_layer_input_rate
        ):
            raise Exception(
                "Configuration not possible if device_clock_source is link_clock\n"
                + f"Device clock rate {device_clock_rate} != Link layer input "
                + f"rate {link_layer_input_rate}"
            )
        # Options: "external", "link_clock", "ref_clock"
        dcs = []
        if "external" in self._device_clock_source:
            dcs.append(0)
        if "link_clock" in self._device_clock_source:
            dcs.append(1)
        if "ref_clock" in self._device_clock_source:
            dcs.append(2)

        config[converter.name + "_device_clock_source"] = self._convert_input(
            dcs, converter.name + "_device_clock_source"
        )
        self._add_equation(
            [
                if_then(
                    config[converter.name + "_device_clock_source"] == 0,  # external
                    link_out_ref == device_clock_rate,
                ),
                if_then(
                    config[converter.name + "_device_clock_source"]
                    == 1,  # link_clock_in
                    link_layer_input_rate == device_clock_rate,
                ),
                if_then(
                    config[converter.name + "_device_clock_source"] == 2,  # ref_clk
                    fpga_ref == link_out_ref,
                ),
            ]
        )

        # Add device clock and ref clock interaction
        if not self.device_clock_and_ref_clock_relation == "NA":
            if self.device_clock_and_ref_clock_relation == "ref_clock_2x_device_clock":
                self._add_equation([fpga_ref == 2 * link_out_ref])
            elif (
                self.device_clock_and_ref_clock_relation == "ref_clock_eq_device_clock"
            ):
                self._add_equation([fpga_ref == link_out_ref])
            else:
                raise Exception(
                    "Invalid device clock and reference clock \n"
                    + f"relation {self.device_clock_and_ref_clock_relation}"
                )

        return config

        # Add optimization to favor a single reference clock vs unique ref+device clocks
        config[converter.name + "single_clk"] = self._convert_input(
            [0, 1], converter.name + "single_clk"
        )
        if self.force_separate_device_clock:
            sdc = [1]
        else:
            sdc = [0, 1]
        config[converter.name + "two_clks"] = self._convert_input(
            sdc, converter.name + "two_clks"
        )
        self._add_equation(
            [
                config[converter.name + "single_clk"]
                + config[converter.name + "two_clks"]
                == 1,
            ]
        )
        # Favor single clock, this equation will be minimized
        v = (
            config[converter.name + "single_clk"]
            + 1000 * config[converter.name + "two_clks"]
        )
        self._add_objective(v)

        # Add constraints to meet sample clock
        if self.requires_core_clock_from_device_clock:
            if converter.jesd_class == "jesd204b":
                core_clock = converter.bit_clock / 40
            else:
                core_clock = converter.bit_clock / 66

            self._add_equation([core_clock == link_out_ref])

        else:
            possible_divs = []
            for samples_per_clock in [1, 2, 4, 8, 16]:
                if converter.sample_clock / samples_per_clock <= self.target_Fmax:
                    possible_divs.append(samples_per_clock)

            if len(possible_divs) == 0:
                raise Exception("Link layer output clock rate too high")

            config[converter.name + "_link_out_div"] = self._convert_input(
                possible_divs, converter.name + "_samples_per_clock"
            )

            self._add_equation(
                [
                    (
                        config[converter.name + "single_clk"] * fpga_ref
                        + config[converter.name + "two_clks"]
                        * link_out_ref
                        * config[converter.name + "_link_out_div"]
                    )
                    == converter.sample_clock
                ]
            )

        return config

    def get_required_clocks(
        self,
        converter: conv,
        fpga_ref: Union[int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar],
        link_out_ref: Union[
            int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar
        ] = None,
    ) -> List:
        """Get necessary clocks for QPLL/CPLL configuration.

        Args:
            converter (conv): Converter object of converter connected to
                FPGA
            fpga_ref (int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar):
                Abstract or concrete reference to FPGA reference clock
            link_out_ref (int or GKVariable): Reference clock generated for FPGA
                link layer output, also called device clock

        Returns:
            List: List of solver variables and constraints

        Raises:
            Exception: If solver is not valid
            Exception: Link layer out clock required
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
                # rsl = self._get_conv_prop(
                #     cnv, self.requires_separate_link_layer_out_clock
                # )
                # if link_out_ref is None and rsl:
                #     raise Exception("Link layer out clock required")

                clock_names.append(cnv.name + "fpga_ref")
                # self.config[cnv.name+"fpga_ref"] = interval_var(
                #     self.ref_clock_min, self.ref_clock_max, name=cnv.name+"fpga_ref"
                # )
                self.config[cnv.name + "fpga_ref"] = fpga_ref
                self.ref_clocks.append(self.config[cnv.name + "fpga_ref"])
                if (
                    link_out_ref is not None
                ):  # self.requires_separate_link_layer_out_clock:
                    self.config[cnv.name + "link_out_ref"] = link_out_ref
                    self.ref_clocks.append(self.config[cnv.name + "link_out_ref"])
                    config = self._setup_quad_tile(
                        cnv,
                        self.config[cnv.name + "fpga_ref"],
                        self.config[cnv.name + "link_out_ref"],
                    )
                else:
                    config = self._setup_quad_tile(
                        cnv, self.config[cnv.name + "fpga_ref"]
                    )
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
