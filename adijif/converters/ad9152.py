"""AD9152 high speed DAC clocking model."""

from typing import Any, Dict, List, Union

from adijif.converters.ad9144 import ad9144
from adijif.converters.ad9152_dp import ad9152_dp

from ..solvers import CpoSolveResult  # noqa: I202


class ad9152(ad9144):
    """AD9152 high speed DAC model.

    This model inherits from AD9144 but with AD9152 specific constraints.
    """

    name = "AD9152"
    
    converter_clock_max = 2.25e9
    sample_clock_max = 2.25e9

    datapath = ad9152_dp()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize AD9152 class.

        Args:
            *args (Any): Pass through arguments
            **kwargs (Any): Pass through keyword arguments
        """
        super().__init__(*args, **kwargs)
        self.datapath = ad9152_dp()

    @property
    def interpolation(self) -> int:
        """Interpolation factor.

        Returns:
            int: interpolation factor
        """
        return self.datapath.interpolation

    @interpolation.setter
    def interpolation(self, value: int) -> None:
        """Set interpolation factor.

        Args:
            value (int): interpolation factor
        """
        self.datapath.interpolation = value

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        Returns:
            List[str]: List of strings of clock names in order
        """
        clk = f"{self.name.lower()}_ref_clk"
        return [clk, f"{self.name.lower()}_sysref"]

    def _pll_config(self) -> Dict:
        """Configure the AD9152 internal PLL.

        VCO range: 6.75 GHz to 12.3 GHz.
        """
        dac_clk = self.interpolation * self.sample_clock
        self.config["dac_clk"] = self._convert_input(dac_clk, "dac_clk")

        self.config["BCount"] = self._convert_input([*range(6, 127 + 1)], name="BCount")

        if self.solver == "gekko":
            self.config["ref_div_factor"] = self.model.sos1(
                self.input_clock_divider_available
            )
            self.config["ref_clk"] = self.model.Var(
                integer=False, lb=35e6, ub=1e9, value=35e6
            )
        elif self.solver == "CPLEX":
            self.config["ref_div_factor"] = self._convert_input(
                self.input_clock_divider_available, "ref_div_factor"
            )

            self.config["ref_clk"] = (
                self.config["dac_clk"]
                * self.config["ref_div_factor"]
                / self.config["BCount"]
                / 2
            )

        # AD9152 VCO range: 6.75 GHz to 12.3 GHz
        # LO_DIV_MODE 1 (div 4): fDAC = 1.6875 GHz to 2.25 GHz
        # LO_DIV_MODE 2 (div 8): fDAC = 843.75 MHz to 1.5375 GHz
        # LO_DIV_MODE 3 (div 16): fDAC = 421.875 MHz to 768.75 MHz

        if dac_clk > 2250e6:
            raise Exception("DAC Clock too fast")
        elif dac_clk >= 1687.5e6:
            self.config["lo_div_mode_p2"] = self._convert_input(
                2 ** (1 + 1), name="lo_div_mode_p2"
            )
        elif 843.75e6 <= dac_clk <= 1537.5e6:
            self.config["lo_div_mode_p2"] = self._convert_input(
                2 ** (2 + 1), name="lo_div_mode_p2"
            )
        elif 421.875e6 <= dac_clk <= 768.75e6:
            self.config["lo_div_mode_p2"] = self._convert_input(
                2 ** (3 + 1), name="lo_div_mode_p2"
            )
        else:
            raise Exception(f"DAC Clock and VCO range mismatch for dac_clk={dac_clk}")

        self.config["vco"] = self._add_intermediate(
            self.config["dac_clk"] * self.config["lo_div_mode_p2"]
        )

        self._add_equation(
            [
                self.config["ref_div_factor"] * self.pfd_min < self.config["ref_clk"],
                self.config["ref_div_factor"] * self.pfd_max > self.config["ref_clk"],
                self.config["ref_clk"] >= self.input_clock_min,
                self.config["ref_clk"] <= self.input_clock_max,
            ]
        )

        if self.solver == "gekko":
            self._add_equation(
                [
                    self.config["ref_clk"] * 2 * self.config["BCount"]
                    == self.config["dac_clk"] * self.config["ref_div_factor"]
                ]
            )

        return self.config["ref_clk"]
