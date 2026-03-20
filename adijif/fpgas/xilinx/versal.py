"""Versal GTY/GTYP transceiver models.

Versal Premium FPGAs (Gen 5) use a fundamentally different PLL architecture
compared to previous generations. Instead of CPLL/QPLL variants, Versal has:
- RPLL (Ring PLL): 4.0-8.0 GHz VCO range
- LCPLL (LC-Tank PLL): 8.0-16.375 GHz VCO range

Both PLLs support fractional-N dividers for fine frequency control.

References:
- AM002 Versal GTY Transceivers Architecture Manual
- DS957 Versal AI Core Data Sheet
"""

from typing import List, Union

from docplex.cp.modeler import if_then

from ...common import core
from ...converters.converter import converter as conv
from ...gekko_trans import gekko_translation
from ...solvers import CpoIntVar, GK_Intermediate, GK_Operators, GKVariable
from .pll import PLLCommon, XilinxPLL


class Versal(XilinxPLL, core, gekko_translation):
    """Versal GTY/GTYP transceiver models with RPLL and LCPLL.

    Versal supports two transceiver types:
    - GTYE5: Standard GTY, max 32.75 Gb/s
    - GTYP: Power-optimized variant, max 58 Gb/s

    Both use the same PLL architecture with RPLL and LCPLL.
    """

    transceiver_types_available = ["GTYE5", "GTYP"]
    _transceiver_type = "GTYE5"

    force_rpll = False
    force_lcpll = False

    def add_plls(self) -> None:
        """Add PLLs to the model."""
        self.plls = {
            "RPLL": RPLL(self),
            "LCPLL": LCPLL(self),
        }

    def add_constraints(
        self,
        config: dict,
        fpga_ref: Union[
            CpoIntVar, GK_Intermediate, GK_Operators, GKVariable, int
        ],
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
        assert not (self.force_rpll and self.force_lcpll), (
            "Both RPLL and LCPLL enabled"
        )
        for pll in self.plls:
            config = self.plls[pll].add_constraints(config, fpga_ref, converter)
        # 2-way mutual exclusivity: rpll XOR lcpll
        self._add_equation(
            config[converter.name + "_use_rpll"]
            + config[converter.name + "_use_lcpll"]
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
        if self.force_rpll:
            erpll = 1
            elcpll = self.solution.get_kpis()[converter.name + "_use_lcpll"]
        elif self.force_lcpll:
            erpll = self.solution.get_kpis()[converter.name + "_use_rpll"]
            elcpll = 1
        else:
            erpll = self.solution.get_kpis()[converter.name + "_use_rpll"]
            elcpll = self.solution.get_kpis()[converter.name + "_use_lcpll"]

        assert erpll != elcpll, "Both RPLL and LCPLL enabled"
        pll = "RPLL" if erpll else "LCPLL"
        return self.plls[pll].get_config(config, converter, fpga_ref)


class RPLL(PLLCommon):
    """Ring PLL (RPLL) for Versal transceivers.

    VCO Range: 4.0 - 8.0 GHz
    Input Divider M: [1, 2, 3, 4]
    Feedback Divider N:
        - Integer mode: [5, 6, ..., 25, 80]
        - Fractional mode: [8.0 - 80.999]
    Output Divider D: [1, 2, 4, 8, 16]

    Formulas:
        f_VCO = f_REFCLK × (N / M)
        f_PLLCLKOUT = f_VCO (no CLKOUTRATE divider)
        f_Linerate = (f_PLLCLKOUT × 2) / D

    Key constraint:
        bit_clock × D = f_VCO × 2

    From AM002 Table 15, pages 30-35.
    """

    @property
    def vco_min(self) -> int:
        """Get the VCO min frequency in Hz for RPLL."""
        if self.parent.transceiver_type in ["GTYE5", "GTYP"]:
            return 4000000000  # 4.0 GHz
        raise Exception(
            f"Unknown vco_min for transceiver type {self.parent.transceiver_type}"
        )

    @property
    def vco_max(self) -> int:
        """Get the VCO max frequency in Hz for RPLL."""
        if self.parent.transceiver_type in ["GTYE5", "GTYP"]:
            return 8000000000  # 8.0 GHz
        raise Exception(
            f"Unknown vco_max for transceiver type {self.parent.transceiver_type}"
        )

    M_available = [1, 2, 3, 4]
    _M = [1, 2, 3, 4]

    @property
    def M(self) -> Union[int, List[int]]:
        """Get the M value for RPLL."""
        return self._M

    @M.setter
    def M(self, value: Union[int, List[int]]) -> None:
        """Set the M value for RPLL."""
        self._check_in_range(value, self.M_available, "M")
        self._M = value

    # N divider: Integer mode has specific values, fractional mode is continuous
    # For solver, we use integer N and add fractional part separately
    N_available = [*range(5, 26), 80]  # [5, 6, ..., 25, 80]
    _N = [*range(5, 26), 80]

    @property
    def N(self) -> Union[int, List[int]]:
        """Get the N value for RPLL."""
        return self._N

    @N.setter
    def N(self, value: Union[int, List[int]]) -> None:
        """Set the N value for RPLL."""
        # Fractional mode allows 8.0-80.999, so accept any integer in that range
        if isinstance(value, int):
            if value < 5 or value > 80:
                raise ValueError(f"N must be between 5 and 80, got {value}")
        self._N = value

    D_available = [1, 2, 4, 8, 16]
    _D = [1, 2, 4, 8, 16]

    @property
    def D(self) -> Union[int, List[int]]:
        """Get the D value for RPLL."""
        return self._D

    @D.setter
    def D(self, value: Union[int, List[int]]) -> None:
        """Set the D value for RPLL."""
        self._check_in_range(value, self.D_available, "D")
        self._D = value

    # Fractional-N support
    SDMDATA_min_max = [0, 2**24 - 1]
    _SDMDATA_min = 0
    _SDMDATA_max = 2**24 - 1

    @property
    def SDMDATA_min(self) -> int:
        """Get the SDMDATA_min value."""
        return self._SDMDATA_min

    @SDMDATA_min.setter
    def SDMDATA_min(self, val: int) -> None:
        """Set the SDMDATA_min."""
        if val < self.SDMDATA_min_max[0] or val > self.SDMDATA_min_max[1]:
            raise ValueError(
                f"SDMDATA_min must be between {self.SDMDATA_min_max[0]} and "
                f"{self.SDMDATA_min_max[1]}"
            )
        self._SDMDATA_min = val

    @property
    def SDMDATA_max(self) -> int:
        """Get the SDMDATA_max value."""
        return self._SDMDATA_max

    @SDMDATA_max.setter
    def SDMDATA_max(self, val: int) -> None:
        """Set the SDMDATA_max."""
        if val < self.SDMDATA_min_max[0] or val > self.SDMDATA_min_max[1]:
            raise ValueError(
                f"SDMDATA_max must be between {self.SDMDATA_min_max[0]} and "
                f"{self.SDMDATA_min_max[1]}"
            )
        self._SDMDATA_max = val

    SDMWIDTH_available = [16, 20, 24]
    _SDMWIDTH = [16, 20, 24]

    @property
    def SDMWIDTH(self) -> Union[int, List[int]]:
        """Get the SDMWIDTH value."""
        return self._SDMWIDTH

    @SDMWIDTH.setter
    def SDMWIDTH(self, val: Union[int, List[int]]) -> None:
        """Set the SDMWIDTH."""
        self._check_in_range(val, self.SDMWIDTH_available, "SDMWIDTH")
        self._SDMWIDTH = val

    force_integer_mode = False

    _pname = "rpll"

    def get_config(
        self, config: dict, converter: conv, fpga_ref: Union[int, float]
    ) -> dict:
        """Get the configuration of the RPLL.

        Args:
            config (dict): Configuration dictionary.
            converter (conv): Converter object.
            fpga_ref (int, float): FPGA reference clock.

        Returns:
            dict: Updated configuration dictionary.
        """
        pname = self._pname
        pll_config = {"type": pname}
        pll_config["n"] = self._get_val(config[converter.name + f"_n_{pname}"])
        pll_config["m"] = self._get_val(config[converter.name + f"_m_{pname}"])
        pll_config["d"] = self._get_val(config[converter.name + f"_d_{pname}"])

        # Check if fractional mode was used
        if not self.force_integer_mode:
            sdm_data = self._get_val(
                config[converter.name + f"_sdm_data_{pname}"]
            )
            if sdm_data > 0:
                pll_config["sdm_data"] = sdm_data
                pll_config["sdm_width"] = self._get_val(
                    config[converter.name + f"_sdm_width_{pname}"]
                )
                pll_config["frac"] = self.solution.get_kpis()[
                    converter.name + f"_frac_{pname}"
                ]
                pll_config["n_dot_frac"] = self.solution.get_kpis()[
                    converter.name + f"_n_dot_frac_{pname}"
                ]
            else:
                pll_config["n_dot_frac"] = pll_config["n"]
        else:
            pll_config["n_dot_frac"] = pll_config["n"]

        pll_config["n"] = pll_config["n_dot_frac"]
        pll_config["vco"] = self.solution.get_kpis()[
            converter.name + f"_vco_{pname}"
        ]

        # Verify the configuration
        # RPLL: f_VCO = f_REFCLK × (N / M)
        #       f_PLLCLKOUT = f_VCO (no CLKOUTRATE divider)
        #       f_Linerate = (f_PLLCLKOUT × 2) / D
        pll_out = fpga_ref * pll_config["n_dot_frac"] / pll_config["m"]
        lane_rate = pll_out * 2 / pll_config["d"]
        if type(lane_rate) in [int, float]:
            assert abs(lane_rate - converter.bit_clock) < 1, (
                f"{lane_rate} != {converter.bit_clock}"
            )

        return pll_config

    def add_constraints(
        self,
        config: dict,
        fpga_ref: Union[
            int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar
        ],
        converter: conv,
    ) -> dict:
        """Add constraints for RPLL.

        Args:
            config (dict): Configuration dictionary.
            fpga_ref (int, CpoIntVar): FPGA reference clock.
            converter (conv): Converter object.

        Returns:
            dict: Updated configuration dictionary.
        """
        pname = self._pname

        # Global flag to use RPLL
        if self.parent.force_rpll:
            v = 1
        else:
            v = [0, 1]

        config[converter.name + f"_use_{pname}"] = self._convert_input(
            v, converter.name + f"_use_{pname}"
        )
        if v == [0, 1]:
            self.model.add_kpi(
                config[converter.name + f"_use_{pname}"],
                name=converter.name + f"_use_{pname}",
            )

        # Add divider variables
        config[converter.name + f"_m_{pname}"] = self._convert_input(
            self.M, converter.name + f"_m_{pname}"
        )
        config[converter.name + f"_d_{pname}"] = self._convert_input(
            self.D, converter.name + f"_d_{pname}"
        )
        config[converter.name + f"_n_{pname}"] = self._convert_input(
            self.N, converter.name + f"_n_{pname}"
        )

        # Add fractional-N support
        if not self.force_integer_mode:
            config[converter.name + f"_sdm_data_{pname}"] = (
                self.model.integer_var(
                    min=self.SDMDATA_min,
                    max=self.SDMDATA_max,
                    name=converter.name + f"_sdm_data_{pname}",
                )
            )
            config[converter.name + f"_sdm_width_{pname}"] = (
                self._convert_input(
                    self.SDMWIDTH, converter.name + f"_sdm_width_{pname}"
                )
            )

            # Fractional part: frac = sdm_data / (2^sdm_width)
            config[converter.name + f"_frac_{pname}"] = self._add_intermediate(
                config[converter.name + f"_sdm_data_{pname}"]
                / (2 ** config[converter.name + f"_sdm_width_{pname}"])
            )
            self.model.add_kpi(
                config[converter.name + f"_frac_{pname}"],
                name=converter.name + f"_frac_{pname}",
            )
            self._add_equation([config[converter.name + f"_frac_{pname}"] < 1])

            # N with fractional part: n_dot_frac = n + frac
            config[converter.name + f"_n_dot_frac_{pname}"] = (
                self._add_intermediate(
                    config[converter.name + f"_n_{pname}"]
                    + config[converter.name + f"_frac_{pname}"]
                )
            )
            self.model.add_kpi(
                config[converter.name + f"_n_dot_frac_{pname}"],
                name=converter.name + f"_n_dot_frac_{pname}",
            )
        else:
            config[converter.name + f"_n_dot_frac_{pname}"] = (
                self._add_intermediate(config[converter.name + f"_n_{pname}"])
            )

        # PLL output and VCO calculation
        # RPLL: f_VCO = f_REFCLK × (N / M)
        #       f_PLLCLKOUT = f_VCO (no CLKOUTRATE divider)
        config[converter.name + f"_pll_out_{pname}"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + f"_n_dot_frac_{pname}"]
            / config[converter.name + f"_m_{pname}"]
        )
        config[converter.name + f"_vco_{pname}"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + f"_n_dot_frac_{pname}"]
            / config[converter.name + f"_m_{pname}"]
        )
        self.model.add_kpi(
            config[converter.name + f"_vco_{pname}"],
            name=converter.name + f"_vco_{pname}",
        )

        # Add constraints
        # Lane rate constraint: bit_clock × D = pll_out × 2
        self._add_equation(
            [
                if_then(
                    config[converter.name + f"_use_{pname}"] == 1,
                    converter.bit_clock * config[converter.name + f"_d_{pname}"]
                    == config[converter.name + f"_pll_out_{pname}"] * 2,
                ),
            ]
        )

        # VCO range constraints
        self._add_equation(
            [
                if_then(
                    config[converter.name + f"_use_{pname}"] == 1,
                    config[converter.name + f"_vco_{pname}"] >= self.vco_min,
                ),
                if_then(
                    config[converter.name + f"_use_{pname}"] == 1,
                    config[converter.name + f"_vco_{pname}"] <= self.vco_max,
                ),
            ]
        )

        return config


class LCPLL(PLLCommon):
    """LC-Tank PLL (LCPLL) for Versal transceivers.

    VCO Range: 8.0 - 16.375 GHz
    Input Divider M: [1, 2, 3, 4]
    Feedback Divider N:
        - Integer mode: [13, 14, ..., 160]
        - Fractional mode (lane rate ≤ 25.78125 Gb/s): [16.0 - 160.999]
        - Fractional mode (lane rate ≤ 30.5 Gb/s): [16.0 - 80.999]
    Output Divider D: [1, 2, 4, 8, 16]
    LCPLL_CLKOUTRATE: [1, 2] (Full rate / Half rate)

    Formulas:
        f_VCO = f_REFCLK × (N / M)
        f_PLLCLKOUT = f_VCO / LCPLL_CLKOUTRATE
        f_Linerate = (f_PLLCLKOUT × 2) / D

    Key constraint:
        bit_clock × D × LCPLL_CLKOUTRATE = f_VCO × 2

    From AM002 Table 18, pages 36-41.
    """

    @property
    def vco_min(self) -> int:
        """Get the VCO min frequency in Hz for LCPLL."""
        if self.parent.transceiver_type in ["GTYE5", "GTYP"]:
            return 8000000000  # 8.0 GHz
        raise Exception(
            f"Unknown vco_min for transceiver type {self.parent.transceiver_type}"
        )

    @property
    def vco_max(self) -> int:
        """Get the VCO max frequency in Hz for LCPLL."""
        if self.parent.transceiver_type in ["GTYE5", "GTYP"]:
            return 16375000000  # 16.375 GHz
        raise Exception(
            f"Unknown vco_max for transceiver type {self.parent.transceiver_type}"
        )

    M_available = [1, 2, 3, 4]
    _M = [1, 2, 3, 4]

    @property
    def M(self) -> Union[int, List[int]]:
        """Get the M value for LCPLL."""
        return self._M

    @M.setter
    def M(self, value: Union[int, List[int]]) -> None:
        """Set the M value for LCPLL."""
        self._check_in_range(value, self.M_available, "M")
        self._M = value

    # N divider: Integer mode [13-160], fractional mode continuous
    N_available = [*range(13, 161)]  # [13, 14, ..., 160]
    _N = [*range(13, 161)]

    @property
    def N(self) -> Union[int, List[int]]:
        """Get the N value for LCPLL."""
        return self._N

    @N.setter
    def N(self, value: Union[int, List[int]]) -> None:
        """Set the N value for LCPLL."""
        # Fractional mode allows 16.0-160.999 (or 16.0-80.999 for high speed)
        if isinstance(value, int):
            if value < 13 or value > 160:
                raise ValueError(f"N must be between 13 and 160, got {value}")
        self._N = value

    D_available = [1, 2, 4, 8, 16]
    _D = [1, 2, 4, 8, 16]

    @property
    def D(self) -> Union[int, List[int]]:
        """Get the D value for LCPLL."""
        return self._D

    @D.setter
    def D(self, value: Union[int, List[int]]) -> None:
        """Set the D value for LCPLL."""
        self._check_in_range(value, self.D_available, "D")
        self._D = value

    # LCPLL_CLKOUTRATE: 1 = full rate, 2 = half rate
    LCPLL_CLKOUTRATE_available = [1, 2]
    _LCPLL_CLKOUTRATE = [1, 2]

    @property
    def LCPLL_CLKOUTRATE(self) -> Union[int, List[int]]:
        """Get the LCPLL_CLKOUTRATE value."""
        return self._LCPLL_CLKOUTRATE

    @LCPLL_CLKOUTRATE.setter
    def LCPLL_CLKOUTRATE(self, val: Union[int, List[int]]) -> None:
        """Set the LCPLL_CLKOUTRATE."""
        self._check_in_range(
            val, self.LCPLL_CLKOUTRATE_available, "LCPLL_CLKOUTRATE"
        )
        self._LCPLL_CLKOUTRATE = val

    # Fractional-N support
    SDMDATA_min_max = [0, 2**24 - 1]
    _SDMDATA_min = 0
    _SDMDATA_max = 2**24 - 1

    @property
    def SDMDATA_min(self) -> int:
        """Get the SDMDATA_min value."""
        return self._SDMDATA_min

    @SDMDATA_min.setter
    def SDMDATA_min(self, val: int) -> None:
        """Set the SDMDATA_min."""
        if val < self.SDMDATA_min_max[0] or val > self.SDMDATA_min_max[1]:
            raise ValueError(
                f"SDMDATA_min must be between {self.SDMDATA_min_max[0]} and "
                f"{self.SDMDATA_min_max[1]}"
            )
        self._SDMDATA_min = val

    @property
    def SDMDATA_max(self) -> int:
        """Get the SDMDATA_max value."""
        return self._SDMDATA_max

    @SDMDATA_max.setter
    def SDMDATA_max(self, val: int) -> None:
        """Set the SDMDATA_max."""
        if val < self.SDMDATA_min_max[0] or val > self.SDMDATA_min_max[1]:
            raise ValueError(
                f"SDMDATA_max must be between {self.SDMDATA_min_max[0]} and "
                f"{self.SDMDATA_min_max[1]}"
            )
        self._SDMDATA_max = val

    SDMWIDTH_available = [16, 20, 24]
    _SDMWIDTH = [16, 20, 24]

    @property
    def SDMWIDTH(self) -> Union[int, List[int]]:
        """Get the SDMWIDTH value."""
        return self._SDMWIDTH

    @SDMWIDTH.setter
    def SDMWIDTH(self, val: Union[int, List[int]]) -> None:
        """Set the SDMWIDTH."""
        self._check_in_range(val, self.SDMWIDTH_available, "SDMWIDTH")
        self._SDMWIDTH = val

    force_integer_mode = False

    _pname = "lcpll"

    def get_config(
        self, config: dict, converter: conv, fpga_ref: Union[int, float]
    ) -> dict:
        """Get the configuration of the LCPLL.

        Args:
            config (dict): Configuration dictionary.
            converter (conv): Converter object.
            fpga_ref (int, float): FPGA reference clock.

        Returns:
            dict: Updated configuration dictionary.
        """
        pname = self._pname
        pll_config = {"type": pname}
        pll_config["n"] = self._get_val(config[converter.name + f"_n_{pname}"])
        pll_config["m"] = self._get_val(config[converter.name + f"_m_{pname}"])
        pll_config["d"] = self._get_val(config[converter.name + f"_d_{pname}"])
        pll_config["clkout_rate"] = self._get_val(
            config[converter.name + f"_clkout_rate_{pname}"]
        )

        # Check if fractional mode was used
        if not self.force_integer_mode:
            sdm_data = self._get_val(
                config[converter.name + f"_sdm_data_{pname}"]
            )
            if sdm_data > 0:
                pll_config["sdm_data"] = sdm_data
                pll_config["sdm_width"] = self._get_val(
                    config[converter.name + f"_sdm_width_{pname}"]
                )
                pll_config["frac"] = self.solution.get_kpis()[
                    converter.name + f"_frac_{pname}"
                ]
                pll_config["n_dot_frac"] = self.solution.get_kpis()[
                    converter.name + f"_n_dot_frac_{pname}"
                ]
            else:
                pll_config["n_dot_frac"] = pll_config["n"]
        else:
            pll_config["n_dot_frac"] = pll_config["n"]

        pll_config["n"] = pll_config["n_dot_frac"]
        pll_config["vco"] = self.solution.get_kpis()[
            converter.name + f"_vco_{pname}"
        ]

        # Verify the configuration
        # LCPLL: f_VCO = f_REFCLK × (N / M)
        #        f_PLLCLKOUT = f_VCO / LCPLL_CLKOUTRATE
        #        f_Linerate = (f_PLLCLKOUT × 2) / D
        pll_out = (
            fpga_ref
            * pll_config["n_dot_frac"]
            / (pll_config["m"] * pll_config["clkout_rate"])
        )
        lane_rate = pll_out * 2 / pll_config["d"]
        if type(lane_rate) in [int, float]:
            assert abs(lane_rate - converter.bit_clock) < 1, (
                f"{lane_rate} != {converter.bit_clock}"
            )

        return pll_config

    def add_constraints(
        self,
        config: dict,
        fpga_ref: Union[
            int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar
        ],
        converter: conv,
    ) -> dict:
        """Add constraints for LCPLL.

        Args:
            config (dict): Configuration dictionary.
            fpga_ref (int, CpoIntVar): FPGA reference clock.
            converter (conv): Converter object.

        Returns:
            dict: Updated configuration dictionary.
        """
        pname = self._pname

        # Global flag to use LCPLL
        if self.parent.force_lcpll:
            v = 1
        else:
            v = [0, 1]

        config[converter.name + f"_use_{pname}"] = self._convert_input(
            v, converter.name + f"_use_{pname}"
        )
        if v == [0, 1]:
            self.model.add_kpi(
                config[converter.name + f"_use_{pname}"],
                name=converter.name + f"_use_{pname}",
            )

        # Add divider variables
        config[converter.name + f"_m_{pname}"] = self._convert_input(
            self.M, converter.name + f"_m_{pname}"
        )
        config[converter.name + f"_d_{pname}"] = self._convert_input(
            self.D, converter.name + f"_d_{pname}"
        )
        config[converter.name + f"_n_{pname}"] = self._convert_input(
            self.N, converter.name + f"_n_{pname}"
        )
        config[converter.name + f"_clkout_rate_{pname}"] = self._convert_input(
            self.LCPLL_CLKOUTRATE, converter.name + f"_clkout_rate_{pname}"
        )

        # Add fractional-N support
        if not self.force_integer_mode:
            config[converter.name + f"_sdm_data_{pname}"] = (
                self.model.integer_var(
                    min=self.SDMDATA_min,
                    max=self.SDMDATA_max,
                    name=converter.name + f"_sdm_data_{pname}",
                )
            )
            config[converter.name + f"_sdm_width_{pname}"] = (
                self._convert_input(
                    self.SDMWIDTH, converter.name + f"_sdm_width_{pname}"
                )
            )

            # Fractional part: frac = sdm_data / (2^sdm_width)
            config[converter.name + f"_frac_{pname}"] = self._add_intermediate(
                config[converter.name + f"_sdm_data_{pname}"]
                / (2 ** config[converter.name + f"_sdm_width_{pname}"])
            )
            self.model.add_kpi(
                config[converter.name + f"_frac_{pname}"],
                name=converter.name + f"_frac_{pname}",
            )
            self._add_equation([config[converter.name + f"_frac_{pname}"] < 1])

            # N with fractional part: n_dot_frac = n + frac
            config[converter.name + f"_n_dot_frac_{pname}"] = (
                self._add_intermediate(
                    config[converter.name + f"_n_{pname}"]
                    + config[converter.name + f"_frac_{pname}"]
                )
            )
            self.model.add_kpi(
                config[converter.name + f"_n_dot_frac_{pname}"],
                name=converter.name + f"_n_dot_frac_{pname}",
            )
        else:
            config[converter.name + f"_n_dot_frac_{pname}"] = (
                self._add_intermediate(config[converter.name + f"_n_{pname}"])
            )

        # PLL output and VCO calculation
        # LCPLL: f_VCO = f_REFCLK × (N / M)
        #        f_PLLCLKOUT = f_VCO / LCPLL_CLKOUTRATE
        config[converter.name + f"_pll_out_{pname}"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + f"_n_dot_frac_{pname}"]
            / (
                config[converter.name + f"_m_{pname}"]
                * config[converter.name + f"_clkout_rate_{pname}"]
            )
        )
        config[converter.name + f"_vco_{pname}"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + f"_n_dot_frac_{pname}"]
            / config[converter.name + f"_m_{pname}"]
        )
        self.model.add_kpi(
            config[converter.name + f"_vco_{pname}"],
            name=converter.name + f"_vco_{pname}",
        )

        # Add constraints
        # Lane rate constraint: bit_clock × D × LCPLL_CLKOUTRATE = vco × 2
        # Note: This differs from RPLL which has no CLKOUTRATE divider
        self._add_equation(
            [
                if_then(
                    config[converter.name + f"_use_{pname}"] == 1,
                    converter.bit_clock
                    * config[converter.name + f"_d_{pname}"]
                    * config[converter.name + f"_clkout_rate_{pname}"]
                    == config[converter.name + f"_vco_{pname}"] * 2,
                ),
            ]
        )

        # VCO range constraints
        self._add_equation(
            [
                if_then(
                    config[converter.name + f"_use_{pname}"] == 1,
                    config[converter.name + f"_vco_{pname}"] >= self.vco_min,
                ),
                if_then(
                    config[converter.name + f"_use_{pname}"] == 1,
                    config[converter.name + f"_vco_{pname}"] <= self.vco_max,
                ),
            ]
        )

        return config
