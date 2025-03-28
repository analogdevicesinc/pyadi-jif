"""7 series transceiver model."""

from typing import List, Union

from docplex.cp.modeler import if_then

from ...converters.converter import converter as conv
from ...solvers import CpoIntVar, GK_Intermediate, GK_Operators, GKVariable
from .pll import PLLCommon, XilinxPLL


class SevenSeries(XilinxPLL):
    """7 series Transceiver model."""

    # References
    # GTXs
    # https://docs.amd.com/v/u/en-US/ug476_7Series_Transceivers
    # https://docs.amd.com/v/u/en-US/ds191-XC7Z030-XC7Z045-data-sheet

    transceiver_types_available = [
        "GTXE2",
        "GTHE2",
    ]  # We don't support GTHE2 yet!
    _transceiver_type = "GTXE2"

    force_cpll = False
    force_qpll = False

    def add_plls(self) -> None:
        """Add PLLs to the model."""
        self.plls = {"CPLL": CPLL(self), "QPLL": QPLL(self)}

    def add_constraints(
        self,
        config: dict,
        fpga_ref: Union[CpoIntVar, GK_Intermediate, GK_Operators, GKVariable, int],
        converter: conv,
    ) -> dict:
        """Add constraints for PLLs.

        Args:
            config (dict): Configuration dictionary.
            fpga_ref (int, CpoIntVar): FPGA reference clock.
            converter (conv): Converter object.

        Returns:
            dict: Updated configuration dictionary.
        """
        assert self.plls, "No PLLs configured. Run the add_plls method"
        assert not (self.force_cpll and self.force_qpll), "Both CPLL and QPLL enabled"
        for pll in self.plls:
            config = self.plls[pll].add_constraints(config, fpga_ref, converter)
        self._add_equation(
            config[converter.name + "_use_cpll"] + config[converter.name + "_use_qpll"]
            == 1
        )
        return config

    def get_config(
        self, config: dict, converter: conv, fpga_ref: Union[int, float]
    ) -> dict:
        """Get PLL configuration.

        Args:
            config (dict): Configuration dictionary.
            converter (conv): Converter object.
            fpga_ref (Union[int, float]): FPGA reference clock.

        Returns:
            dict: Updated configuration dictionary.
        """
        if self.force_cpll:
            ecpll = 1
            eqpll = self.solution.get_kpis()[converter.name + "_use_qpll"]
        elif self.force_qpll:
            ecpll = self.solution.get_kpis()[converter.name + "_use_cpll"]
            eqpll = 1
        else:
            ecpll = self.solution.get_kpis()[converter.name + "_use_cpll"]
            eqpll = self.solution.get_kpis()[converter.name + "_use_qpll"]

        assert ecpll != eqpll, "Both CPLL and QPLL enabled"
        pll = "CPLL" if ecpll else "QPLL"
        return self.plls[pll].get_config(config, converter, fpga_ref)


class CPLL(PLLCommon):
    """Channel PLL (CPLL) for 7 series FPGAs."""

    @property
    def vco_min(self) -> int:
        """Get the minimum VCO frequency for the transceiver type.

        Returns:
            int: Minimum VCO frequency.

        Raises:
            Exception: Unsupported transceiver type.
        """
        if self.parent.transceiver_type == "GTXE2":
            return 1600000000
        elif self.parent.transceiver_type == "GTHE2":
            return 1600000000
        raise Exception(
            f"Unknown vco_min for transceiver type {self.parent.transceiver_type}"
        )

    @property
    def vco_max(self) -> int:
        """Get the maximum VCO frequency for the transceiver type.

        Returns:
            int: Maximum VCO frequency.

        Raises:
            Exception: Unsupported transceiver type.
        """
        if self.parent.transceiver_type == "GTXE2":
            return 3300000000
        elif self.parent.transceiver_type == "GTHE2":
            return 5160000000
        raise Exception(
            f"Unknown vco_max for transceiver type {self.parent.transceiver_type}"
        )

    M_available = [1, 2]
    _M = [1, 2]

    @property
    def M(self) -> Union[int, List[int]]:
        """Get the M value for the CPLL."""
        return self._M

    @M.setter
    def M(self, value: Union[int, List[int]]) -> None:
        """Set the M value for the CPLL."""
        self._check_in_range(value, self.M_available, "M")
        self._M = value

    N2_available = [1, 2, 3, 4, 5]
    _N2 = [1, 2, 3, 4, 5]

    @property
    def N2(self) -> Union[int, List[int]]:
        """Get the N2 value for the CPLL."""
        return self._N2

    @N2.setter
    def N2(self, value: Union[int, List[int]]) -> None:
        """Set the N2 value for the CPLL."""
        self._check_in_range(value, self.N2_available, "N2")
        self._N2 = value

    N1_available = [4, 5]
    _N1 = [4, 5]

    @property
    def N1(self) -> Union[int, List[int]]:
        """Get the N1 value for the CPLL."""
        return self._N1

    @N1.setter
    def N1(self, value: Union[int, List[int]]) -> None:
        """Set the N1 value for the CPLL."""
        self._check_in_range(value, self.N1_available, "N1")
        self._N1 = value

    D_available = [1, 2, 4, 8]
    _D = [1, 2, 4, 8]

    @property
    def D(self) -> Union[int, List[int]]:
        """Get the D value for the CPLL."""
        return self._D

    @D.setter
    def D(self, value: Union[int, List[int]]) -> None:
        """Set the D value for the CPLL."""
        self._check_in_range(value, self.D_available, "D")
        self._D = value

    def get_config(
        self, config: dict, converter: conv, fpga_ref: Union[int, CpoIntVar]
    ) -> dict:
        """Get CPLL configuration.

        Args:
            config (dict): Configuration dictionary.
            converter (conv): Converter object.
            fpga_ref (int, CpoIntVar): FPGA reference clock.

        Returns:
            dict: Updated configuration dictionary.
        """
        pll_config = {}
        pll_config["type"] = "cpll"
        for k in ["m", "d", "n1", "n2"]:
            pll_config[k] = self._get_val(config[converter.name + "_" + k + "_cpll"])

        pll_config["vco"] = (
            fpga_ref * pll_config["n1"] * pll_config["n2"] / pll_config["m"]  # type: ignore # noqa: B950
        )
        # Check
        assert (
            pll_config["vco"] * 2 / pll_config["d"] == converter.bit_clock  # type: ignore # noqa: B950
        ), "Invalid CPLL lane rate"

        return pll_config

    def add_constraints(
        self, config: dict, fpga_ref: Union[int, CpoIntVar], converter: conv
    ) -> dict:
        """Add Channel PLL (CPLL) constraints.

        Args:
            config (dict): Configuration dictionary.
            fpga_ref (int, CpoIntVar): FPGA reference clock.
            converter (conv): Converter object.

        Returns:
            dict: Updated configuration dictionary.
        """
        if self.parent.force_cpll:
            v = 1
        else:
            v = [0, 1]
        config[converter.name + "_use_cpll"] = self._convert_input(
            v, converter.name + "_use_cpll"
        )
        if v == [0, 1]:
            self.model.add_kpi(
                config[converter.name + "_use_cpll"],
                name=converter.name + "_use_cpll",
            )
        # Add variables
        config[converter.name + "_m_cpll"] = self._convert_input(
            self._M, converter.name + "_m_cpll"
        )
        # This is documented oddly
        # There are footnotes that include 16 with GTHs, and 16,32 with GTYs
        # but its says "not supported for CPLL"?!?!?
        config[converter.name + "_d_cpll"] = self._convert_input(
            self._D, converter.name + "_d_cpll"
        )
        config[converter.name + "_n1_cpll"] = self._convert_input(
            self._N1, converter.name + "_n1_cpll"
        )
        config[converter.name + "_n2_cpll"] = self._convert_input(
            self._N2, converter.name + "_n2_cpll"
        )

        # Add intermediate variables
        config[converter.name + "_pll_out_cpll"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + "_n1_cpll"]
            * config[converter.name + "_n2_cpll"]
            / (config[converter.name + "_m_cpll"])
        )

        # Add constraints
        self._add_equation(
            [
                if_then(
                    config[converter.name + "_use_cpll"] == 1,
                    config[converter.name + "_d_cpll"] * converter.bit_clock
                    == config[converter.name + "_pll_out_cpll"] * 2,
                ),
            ]
        )
        self._add_equation(
            [
                if_then(
                    config[converter.name + "_use_cpll"] == 1,
                    config[converter.name + "_pll_out_cpll"] >= self.vco_min,
                ),
                if_then(
                    config[converter.name + "_use_cpll"] == 1,
                    config[converter.name + "_pll_out_cpll"] <= self.vco_max,
                ),
            ]
        )

        return config


class QPLL(PLLCommon):
    """QPLL for 7 series FPGAs."""

    M_available = [1, 2, 3, 4]
    _M = [1, 2, 3, 4]

    @property
    def M(self) -> Union[int, List[int]]:
        """Get the M value for the QPLL."""
        return self._M

    @M.setter
    def M(self, value: Union[int, List[int]]) -> None:
        """Set the M value for the QPLL."""
        self._check_in_range(value, self.M_available, "M")
        self._M = value

    N_available = [16, 20, 32, 40, 64, 66, 80, 100]
    _N = [16, 20, 32, 40, 64, 66, 80, 100]

    @property
    def N(self) -> Union[int, List[int]]:
        """Get the N value for the QPLL."""
        return self._N

    @N.setter
    def N(self, value: Union[int, List[int]]) -> None:
        """Set the N value for the QPLL."""
        self._check_in_range(value, self.N_available, "N")
        self._N = value

    D_available = [1, 2, 4, 8, 16]
    _D = [1, 2, 4, 8, 16]

    @property
    def D(self) -> Union[int, List[int]]:
        """Get the D value for the QPLL."""
        return self._D

    @D.setter
    def D(self, value: Union[int, List[int]]) -> None:
        """Set the D value for the QPLL."""
        self._check_in_range(value, self.D_available, "D")
        self._D = value

    @property
    def vco_min(self) -> int:
        """Get the minimum VCO frequency for the transceiver type.

        Returns:
            int: Minimum VCO frequency.

        Raises:
            Exception: Unsupported transceiver type.
        """
        if self.parent.transceiver_type[:3] == "GTH":
            return 8000000000
        elif (
            self.parent.transceiver_type[:3] == "GTX"
        ):  # FIXME: This is only the lower band
            return 5930000000
        raise Exception(
            f"Unknown vco_min for transceiver type {self.parent.transceiver_type}"
        )

    @property
    def vco_max(self) -> int:
        """Get the maximum VCO frequency for the transceiver type.

        Returns:
            int: Maximum VCO frequency.

        Raises:
            Exception: Unsupported transceiver type.
        """
        if self.parent.transceiver_type[:3] == "GTH":
            if float(str(self.parent.speed_grade)[:2]) >= -2:
                return 10312500000
            return 13100000000
        elif (
            self.parent.transceiver_type[:3] == "GTX"
        ):  # FIXME: This is only the lower band
            if float(str(self.parent.speed_grade)[:2]) >= -2:
                return 10312500000
            return 12500000000
        raise Exception(
            f"Unknown vco_max for transceiver type {self.parent.transceiver_type}"
        )

    def add_constraints(
        self, config: dict, fpga_ref: Union[int, CpoIntVar], converter: conv
    ) -> dict:
        """Add constraints for QPLL for 7 series FPGAs.

        Args:
            config (dict): Configuration dictionary.
            fpga_ref (int, CpoIntVar): FPGA reference clock.
            converter (conv): Converter object.

        Returns:
            dict: Updated configuration dictionary.

        Raises:
            Exception: Unsupported transceiver type.
        """
        if self.parent.force_qpll:
            v = 1
        else:
            v = [0, 1]
        # Global flag to use QPLLn
        config[converter.name + "_use_qpll"] = self._convert_input(
            v, converter.name + "_use_qpll"
        )
        if v == [0, 1]:
            self.model.add_kpi(
                config[converter.name + "_use_qpll"],
                name=converter.name + "_use_qpll",
            )

        # Add variables
        config[converter.name + "_m_qpll"] = self._convert_input(
            self._M, converter.name + "_m_qpll"
        )
        config[converter.name + "_d_qpll"] = self._convert_input(
            self._D, converter.name + "_d_qpll"
        )
        config[converter.name + "_n_qpll"] = self._convert_input(
            self._N, converter.name + "_n_qpll"
        )

        # Add intermediate variables
        config[converter.name + "_vco_qpll"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + "_n_qpll"]
            / config[converter.name + "_m_qpll"]
        )
        config[converter.name + "_pll_out_qpll"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + "_n_qpll"]
            / (config[converter.name + "_m_qpll"] * 2)
        )

        # Add constraints
        self._add_equation(
            [
                if_then(
                    config[converter.name + "_use_qpll"] == 1,
                    converter.bit_clock
                    == config[converter.name + "_pll_out_qpll"]
                    * 2
                    / config[converter.name + "_d_qpll"],
                ),
            ]
        )

        if self.parent.transceiver_type[:3] == "GTH":
            self._add_equation(
                [
                    if_then(
                        config[converter.name + "_use_qpll"] == 1,
                        config[converter.name + "_vco_qpll"] >= int(self.vco_min),
                    ),
                    if_then(
                        config[converter.name + "_use_qpll"] == 1,
                        config[converter.name + "_vco_qpll"] <= int(self.vco_max),
                    ),
                ]
            )
        elif self.parent.transceiver_type[:3] == "GTX":
            config[converter.name + "_lower_band_qpll"] = self._convert_input(
                [0, 1], converter.name + "_lower_band_qpll"
            )
            # Lower band
            c1 = if_then(
                config[converter.name + "_use_qpll"] == 1,
                if_then(
                    config[converter.name + "_lower_band_qpll"] == 1,
                    config[converter.name + "_vco_qpll"] >= int(self.vco_min),
                ),
            )
            c2 = if_then(
                config[converter.name + "_use_qpll"] == 1,
                if_then(
                    config[converter.name + "_lower_band_qpll"] == 1,
                    config[converter.name + "_vco_qpll"] <= int(8e9),
                ),
            )
            # See page 72 of https://docs.amd.com/v/u/en-US/ds191-XC7Z030-XC7Z045-data-sheet # noqa: B950
            c5 = if_then(
                config[converter.name + "_use_qpll"] == 1,
                if_then(
                    config[converter.name + "_lower_band_qpll"] == 1,
                    config[converter.name + "_d_qpll"] <= 8,  # no 16
                ),
            )

            # Upper band
            c3 = if_then(
                config[converter.name + "_use_qpll"] == 1,
                if_then(
                    config[converter.name + "_lower_band_qpll"] == 0,
                    config[converter.name + "_vco_qpll"] >= int(9.8e9),
                ),
            )
            c4 = if_then(
                config[converter.name + "_use_qpll"] == 1,
                if_then(
                    config[converter.name + "_lower_band_qpll"] == 0,
                    config[converter.name + "_vco_qpll"] <= int(self.vco_max),
                ),
            )
            self._add_equation([c1, c2, c3, c4, c5])

        else:
            raise Exception("Unsupported transceiver type")

        return config

    def get_config(
        self, config: dict, converter: conv, fpga_ref: Union[int, float]
    ) -> dict:
        """Get QPLL configuration for 7 series FPGAs.

        Args:
            config (dict): Configuration dictionary.
            converter (conv): Converter object.
            fpga_ref (Union[int, float]): FPGA reference clock.

        Returns:
            dict: Updated configuration dictionary.
        """
        pll_config = {"type": "qpll"}
        for k in ["m", "d", "n"]:
            pll_config[k] = self._get_val(config[converter.name + "_" + k + "_qpll"])

        pll_config["vco"] = fpga_ref * pll_config["n"] / pll_config["m"]
        pll_clk_out = fpga_ref * pll_config["n"] / (pll_config["m"] * 2)
        # Check
        assert (
            pll_clk_out * 2 / pll_config["d"] == converter.bit_clock  # type: ignore # noqa: B950
        ), (
            f"Invalid QPLL lane rate {pll_config['vco'] * 2 / pll_config['d']} "
            + f"!= {converter.bit_clock}"
        )

        return pll_config
