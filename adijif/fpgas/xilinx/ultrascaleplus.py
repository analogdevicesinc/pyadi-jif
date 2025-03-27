"""Ultrascale+ PLLs transceiver models."""

from typing import List, Union

from docplex.cp.modeler import if_then

from ...common import core
from ...converters.converter import converter as conv
from ...gekko_trans import gekko_translation
from ...solvers import CpoIntVar, GK_Intermediate, GK_Operators, GKVariable
from .pll import XilinxPLL
from .sevenseries import CPLL as SevenSeriesCPLL
from .sevenseries import QPLL as SevenSeriesQPLL


class UltraScalePlus(XilinxPLL, core, gekko_translation):
    """Ultrascale+ PLLs transceiver models."""

    # References
    # GTYs
    # https://docs.amd.com/v/u/en-US/ug578-ultrascale-gty-transceivers
    # https://docs.amd.com/r/en-US/ds925-zynq-ultrascale-plus/GTY-Transceiver-Switching-Characteristics
    # GTHs
    # https://docs.amd.com/v/u/en-US/ug576-ultrascale-gth-transceivers

    transceiver_types_available = ["GTHE4", "GTYE3", "GTYE4"]
    _transceiver_type = "GTHE4"

    force_cpll = False
    force_qpll = False
    force_qpll1 = False

    def add_plls(self) -> None:
        """Add PLLs to the model."""
        self.plls = {
            "CPLL": CPLL(self),
            "QPLL": QPLL(self),
            "QPLL1": QPLL1(self),
        }

    def add_constraints(
        self, config: dict, fpga_ref: Union[int, float], converter: conv
    ) -> dict:
        """Add constraints for PLLs.

        Args:
            config (dict): Configuration dictionary.
            fpga_ref (int, float): FPGA reference clock.
            converter (conv): Converter object.

        Returns:
            dict: Updated configuration dictionary.
        """
        assert self.plls, "No PLLs configured. Run the add_plls method"
        assert (
            self.force_cpll + self.force_qpll + self.force_qpll1 <= 1
        ), "Only one PLL can be enabled"
        for pll in self.plls:
            config = self.plls[pll].add_constraints(config, fpga_ref, converter)
        self._add_equation(
            config[converter.name + "_use_cpll"]
            + config[converter.name + "_use_qpll"]
            + config[converter.name + "_use_qpll1"]
            == 1
        )
        return config

    def get_config(
        self, config: dict, converter: conv, fpga_ref: Union[int, float]
    ) -> dict:
        """Get the configuration of the PLLs.

        Args:
            config (dict): Configuration dictionary.
            converter (conv): Converter object.
            fpga_ref (int, float): FPGA reference clock.

        Returns:
            dict: Updated configuration dictionary.
        """
        if self.force_cpll or self.force_qpll or self.force_qpll1:
            if self.force_cpll:
                ecpll = 1
                eqpll = self.solution.get_kpis()[converter.name + "_use_qpll"]
                eqpll1 = self.solution.get_kpis()[converter.name + "_use_qpll1"]
            elif self.force_qpll:
                ecpll = self.solution.get_kpis()[converter.name + "_use_cpll"]
                eqpll = 1
                eqpll1 = self.solution.get_kpis()[converter.name + "_use_qpll1"]
            else:
                ecpll = self.solution.get_kpis()[converter.name + "_use_cpll"]
                eqpll = self.solution.get_kpis()[converter.name + "_use_qpll"]
                eqpll1 = 1
        else:
            ecpll = self.solution.get_kpis()[converter.name + "_use_cpll"]
            eqpll = self.solution.get_kpis()[converter.name + "_use_qpll"]
            eqpll1 = self.solution.get_kpis()[converter.name + "_use_qpll1"]
        assert ecpll + eqpll + eqpll1 == 1, "Only one PLL can be enabled"
        if ecpll:
            pll = "CPLL"
        elif eqpll:
            pll = "QPLL"
        else:
            pll = "QPLL1"
        return self.plls[pll].get_config(config, converter, fpga_ref)


class CPLL(SevenSeriesCPLL):
    """CPLL model for Ultrascale+ transceivers."""

    @property
    def vco_min(self) -> int:
        """Get the VCO min frequency in Hz for CPLL."""
        if self.parent.transceiver_type in ["GTHE4", "GTYE3", "GTYE4"]:
            return 2000000000
        raise Exception(
            f"Unknown vco_min for transceiver type {self.parent.transceiver_type}"
        )

    @property
    def vco_max(self) -> int:
        """Get the VCO max frequency in Hz for CPLL."""
        if self.parent.transceiver_type in ["GTHE4", "GTYE3", "GTYE4"]:
            return 6250000000
        raise Exception(
            f"Unknown vco_max for transceiver type {self.parent.transceiver_type}"
        )


class QPLL(SevenSeriesQPLL):
    """QPLL model for Ultrascale+ transceivers."""

    force_integer_mode = True

    @property
    def vco_min(self) -> int:
        """Get the VCO min frequency in Hz for QPLL."""
        if self.parent.transceiver_type in ["GTHE3", "GTHE4", "GTYE4"]:
            return 9800000000
        raise Exception(
            f"Unknown vco_min for transceiver type {self.parent.transceiver_type}"
        )

    @property
    def vco_max(self) -> int:
        """Get the VCO max frequency in Hz for QPLL."""
        if self.parent.transceiver_type in ["GTHE3", "GTHE4", "GTYE4"]:
            return 16375000000
        raise Exception(
            f"Unknown vco_max for transceiver type {self.parent.transceiver_type}"
        )

    N_available = [*range(16, 160 + 1)]
    _N = [*range(16, 160 + 1)]

    D_available = [1, 2, 4, 8, 16]
    _D = [1, 2, 4, 8, 16]
    # 32 not available in AC modes https://docs.amd.com/r/en-US/ds925-zynq-ultrascale-plus/GTY-Transceiver-Switching-Characteristics # type: ignore # noqa: B950

    @property
    def QPLL_CLKOUTRATE_available(self) -> List[int]:
        """Get the QPLL_CLKOUTRATE available values."""
        if self.parent.transceiver_type == "GTHE4":
            return [1, 2]
        return [1]

    _QPLL_CLKOUTRATE_GTY = [1, 2]
    _QPLL_CLKOUTRATE_GTH = [1, 2]

    @property
    def QPLL_CLKOUTRATE(self) -> int:
        """Get the QPLL_CLKOUTRATE value."""
        if "GTH" in self.parent.transceiver_type:
            return self._QPLL_CLKOUTRATE_GTH
        return self._QPLL_CLKOUTRATE_GTY

    @QPLL_CLKOUTRATE.setter
    def QPLL_CLKOUTRATE(self, val: int) -> None:
        """Set the QPLL_CLKOUTRATE.

        Args:
            val (int): QPLL_CLKOUTRATE value.

        Raises:
            ValueError: If QPLL_CLKOUTRATE is out of range.
        """
        self._check_in_range(val, self.QPLL_CLKOUTRATE_available, "QPLL_CLKOUTRATE")
        if "GTH" in self.parent.transceiver_type:
            self._QPLL_CLKOUTRATE_GTH = val
        raise ValueError(
            f"QPLL_CLKOUTRATE not available for {self.parent.transceiver_type}"
        )

    SDMDATA_min_max = [0, 2**24 - 1]
    _SDMDATA_min = 0

    @property
    def SDMDATA_min(self) -> int:
        """Get the SDMDATA_min value."""
        return self._SDMDATA_min

    @SDMDATA_min.setter
    def SDMDATA_min(self, val: int) -> None:
        """Set the SDMDATA_min.

        Args:
            val (int): SDMDATA_min value.

        Raises:
            ValueError: If SDMDATA_min is out of range.
        """
        if val < self.SDMDATA_min_max[0] or val > self.SDMDATA_min_max[1]:
            raise ValueError(
                f"SDMDATA_min must be between {self.SDMDATA_min_max[0]} and"
                + f" {self.SDMDATA_min_max[1]}"
            )
        self._SDMDATA_min = val

    _SDMDATA_max = 2**24 - 1

    @property
    def SDMDATA_max(self) -> int:
        """Get the SDMDATA_max value."""
        return self._SDMDATA_max

    @SDMDATA_max.setter
    def SDMDATA_max(self, val: int) -> None:
        """Set the SDMDATA_max.

        Args:
            val (int): SDMDATA_max value.

        Raises:
            ValueError: If SDMDATA_max is out of range.
        """
        if val < self.SDMDATA_min_max[0] or val > self.SDMDATA_min_max[1]:
            raise ValueError(
                f"SDMDATA must be between {self.SDMDATA_min_max[0]} and"
                + f" {self.SDMDATA_min_max[1]}"
            )
        self._SDMDATA_max = val

    SDMWIDTH_available = [16, 20, 24]
    _SDMWIDTH = [16, 20, 24]

    @property
    def SDMWIDTH(self) -> int:
        """Get the SDMWIDTH value."""
        return self._SDMWIDTH

    @SDMWIDTH.setter
    def SDMWIDTH(self, val: int) -> None:
        """Set the SDMWIDTH.

        Args:
            val (int): SDMWIDTH value.
        """
        self._check_in_range(val, self.SDMWIDTH_available, "SDMWIDTH")
        self._SDMWIDTH = val

    _pname = "qpll"

    def get_config(
        self, config: dict, converter: conv, fpga_ref: Union[int, float]
    ) -> dict:
        """Get the configuration of the QPLL.

        Args:
            config (dict): Configuration dictionary.
            converter (conv): Converter object.
            fpga_ref (int, float): FPGA reference clock.

        Returns:
            dict: Updated configuration dictionary.
        """
        pname = self._pname
        pll_config = {"type": self._pname}
        pll_config["n"] = self._get_val(config[converter.name + f"_n_{pname}"])
        pll_config["m"] = self._get_val(config[converter.name + f"_m_{pname}"])
        pll_config["d"] = self._get_val(config[converter.name + f"_d_{pname}"])
        pll_config["clkout_rate"] = self._get_val(
            config[converter.name + f"_clkout_rate_{pname}"]
        )
        if converter.bit_clock < 28.1e9 and not self.force_integer_mode:
            sdm_data = self._get_val(config[converter.name + f"_sdm_data_{pname}"])
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

        # config['vco'] = self._get_val(config[converter.name + f"_vco_{pname}"])
        pll_config["vco"] = self.solution.get_kpis()[converter.name + f"_vco_{pname}"]

        # Check
        pll_out = (
            fpga_ref
            * pll_config["n_dot_frac"]
            / (pll_config["m"] * pll_config["clkout_rate"])
        )
        lane_rate = pll_out * 2 / pll_config["d"]
        assert lane_rate == converter.bit_clock, f"{lane_rate} != {converter.bit_clock}"

        return pll_config

    def add_constraints(
        self,
        config: dict,
        fpga_ref: Union[int, GKVariable, GK_Intermediate, GK_Operators, CpoIntVar],
        converter: conv,
    ) -> dict:
        """Add constraints for the Transceiver.

        Args:
            config (dict): Configuration dictionary.
            fpga_ref (int, CpoIntVar): FPGA reference clock.
            converter (conv): Converter object.

        Returns:
            dict: Updated configuration dictionary.
        """
        pname = self._pname

        # Global flag to use QPLLn
        if self.parent.force_qpll and self._pname == "qpll":
            v = 1
        elif self.parent.force_qpll1 and self._pname == "qpll1":
            v = 1
        elif self.parent.force_cpll and self._pname == "cpll":
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

        # Add variables
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
            self.QPLL_CLKOUTRATE, converter.name + f"_clkout_rate_{pname}"
        )

        # Frac part
        if converter.bit_clock < 28.1e9 and not self.force_integer_mode:
            config[converter.name + f"_sdm_data_{pname}"] = self.model.integer_var(
                min=self.SDMDATA_min,
                max=self.SDMDATA_max,
                name=converter.name + f"_sdm_data_{pname}",
            )
            config[converter.name + f"_sdm_width_{pname}"] = self._convert_input(
                self.SDMWIDTH, converter.name + f"_sdm_width_{pname}"
            )
            config[converter.name + f"_HIGH_RATE_{pname}"] = self._convert_input(
                self.QPLL_CLKOUTRATE, converter.name + f"_HIGH_RATE_{pname}"
            )

        # Add intermediate variables
        if converter.bit_clock < 28.1e9 and not self.force_integer_mode:
            config[converter.name + f"_frac_{pname}"] = self._add_intermediate(
                config[converter.name + f"_sdm_data_{pname}"]
                / (2 ** config[converter.name + f"_sdm_width_{pname}"])
            )
            self.model.add_kpi(
                config[converter.name + f"_frac_{pname}"],
                name=converter.name + f"_frac_{pname}",
            )
            self._add_equation([config[converter.name + f"_frac_{pname}"] < 1])
            config[converter.name + f"_n_dot_frac_{pname}"] = self._add_intermediate(
                config[converter.name + f"_n_{pname}"]
                + config[converter.name + f"_frac_{pname}"]
            )
            self.model.add_kpi(
                config[converter.name + f"_n_dot_frac_{pname}"],
                name=converter.name + f"_n_dot_frac_{pname}",
            )
        else:
            config[converter.name + f"_n_dot_frac_{pname}"] = self._add_intermediate(
                config[converter.name + f"_n_{pname}"]
            )

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
            / (
                config[converter.name + f"_m_{pname}"]
                * config[converter.name + f"_clkout_rate_{pname}"]
            )
        )
        self.model.add_kpi(
            config[converter.name + f"_vco_{pname}"],
            name=converter.name + f"_vco_{pname}",
        )

        # Add constraints
        self._add_equation(
            [
                if_then(
                    config[converter.name + f"_use_{pname}"] == 1,
                    converter.bit_clock * config[converter.name + f"_d_{pname}"]
                    == config[converter.name + f"_pll_out_{pname}"] * 2,
                ),
                # if_then(
                #     config[converter.name + f"_use_{pname}"] == 1,
                #     config[converter.name + f"_HIGH_RATE_{pname}"]
                #     == (converter.bit_clock >= 28.1e9),
                # ),
            ]
        )

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
                # if_then(
                #     config[converter.name + f"_HIGH_RATE_{pname}"] == 1,
                #     config[converter.name + f"_frac_{pname}"] == 0,
                # ),
            ]
        )

        return config


class QPLL1(QPLL):
    """QPLL1 model for Ultrascale+ transceivers."""

    _pname = "qpll1"

    @property
    def vco_min(self) -> int:
        """VCO min frequency in Hz for QPLL1."""
        if self.parent.transceiver_type in ["GTHE3", "GTHE4", "GTYE3", "GTYE4"]:
            return 8000000000
        raise Exception(
            f"Unknown vco_min for transceiver type {self.parent.transceiver_type}"
        )

    @property
    def vco_max(self) -> int:
        """VCO max frequency in Hz for QPLL1."""
        if self.parent.transceiver_type in ["GTHE3", "GTHE4", "GTYE3", "GTYE4"]:
            return 13000000000
        raise Exception(
            f"Unknown vco_max for transceiver type {self.parent.transceiver_type}"
        )
