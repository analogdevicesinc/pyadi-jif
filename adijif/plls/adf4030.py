"""ADF4030 10-Channel Precision Synchronizer."""

from typing import Dict, List, Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.plls.pll import pll
from adijif.solvers import CpoExpr, GK_Intermediate


class adf4030(pll):
    """ADF4030 PLL model.

    This model currently supports all divider configurations

    https://www.analog.com/media/en/technical-documentation/data-sheets/adf4030.pdf
    """

    name = "adf4030"

    input_freq_min = int(10e6)
    input_freq_max = int(250e6)

    pfd_freq_min = int(10e6)
    pfd_freq_max = int(20e6)

    vco_freq_min = int(2.5e9 * 0.95)
    vco_freq_max = int(2.5e9 * 1.05)

    _r = [*range(1, 31 + 1)]
    r_available = [*range(1, 31 + 1)]

    @property
    def r(self) -> Union[int, List[int]]:
        """Reference divider.

        Valid values are 1->31

        Returns:
            int: Current allowable setting
        """
        return self._r

    @r.setter
    def r(self, value: Union[int, List[int]]) -> None:
        """Reference divider.

        Valid values are 1->31

        Args:
            value (int, list[int]): Current allowable setting

        """
        self._check_in_range(value, self.r_available, "r")
        self._r = value

    _n = [*range(8, 255 + 1)]
    n_available = [*range(8, 255 + 1)]

    @property
    def n(self) -> Union[int, List[int]]:
        """Feedback divider.

        Valid values are 8->255

        Returns:
            int: Current allowable setting
        """
        return self._n

    @n.setter
    def n(self, value: Union[int, List[int]]) -> None:
        """Feedback divider.

        Valid values are 8->255

        Args:
            value (int, list[int]): Current allowable setting

        """
        self._check_in_range(value, self.n_available, "n")
        self._n = value

    _o = [*range(10, 4095 + 1)]
    o_available = [*range(10, 4095 + 1)]

    @property
    def o(self) -> Union[int, List[int]]:
        """Output divider.

        Valid values are 10->4095

        Returns:
            int: Current allowable setting
        """
        return self._o

    @o.setter
    def o(self, value: Union[int, List[int]]) -> None:
        """Output divider.

        Valid values are 10->4095

        Args:
            value (int, list[int]): Current allowable setting

        """
        self._check_in_range(value, self.o_available, "o")
        self._o = value

    def get_config(self, solution: CpoSolveResult = None) -> Dict:
        """Extract configurations from solver results.

        Collect internal clock chip configuration and output clock definitions
        leading to connected devices (converters, FPGAs)

        Args:
            solution (CpoSolveResult): CPlex solution. Only needed for CPlex solver

        Returns:
            Dict: Dictionary of clocking rates and dividers for configuration

        Raises:
            Exception: If solver is not called first
        """
        if not self._clk_names:
            raise Exception("set_requested_clocks must be called before get_config")

        if solution:
            self.solution = solution

        out_dividers = [self._get_val(x) for x in self.config["out_dividers"]]

        config: Dict = {
            "r": self._get_val(self.config["r"]),
            "n": self._get_val(self.config["n"]),
            "out_dividers": out_dividers,
        }

        vco = self.solution.get_kpis()["vco_adf4030"]
        config["vco"] = vco

        # Outputs
        output_config = {}
        for i, clk in enumerate(self._clk_names):
            o_val = out_dividers[i]
            output_config[clk] = {
                "rate": vco / o_val,
                "divider": o_val,
            }

        config["output_clocks"] = output_config

        return config

    def _setup_solver_constraints(
        self, input_ref: Union[int, float, CpoExpr, GK_Intermediate]
    ) -> None:
        """Apply constraints to solver model.

        Args:
            input_ref (int, float, CpoExpr, GK_Intermediate): Input reference
                frequency in hertz
        """
        self.config = {}

        # if not isinstance(input_ref, (int, float)):
        #     self.config["input_ref_set"] = input_ref(self.model)  # type: ignore
        #     input_ref = self.config["input_ref_set"]["range"]
        self.input_ref = input_ref

        # PFD
        self.config["r"] = self._convert_input(self.r, name="r_adf4030")
        self.config["n"] = self._convert_input(self.n, name="n_adf4030")
        self.config["o"] = self._convert_input(self.o, name="o_adf4030")

        self.config["vco"] = self._add_intermediate(
            input_ref * self.config["n"] / self.config["r"]
        )
        self.model.add_kpi(
            input_ref * self.config["n"] / self.config["r"],
            "vco_adf4030",
        )

        self._add_equation(
            [
                input_ref <= self.input_freq_max,
                input_ref >= self.input_freq_min,
                self.config["vco"] <= self.vco_freq_max,
                self.config["vco"] >= self.vco_freq_min,
                input_ref <= self.pfd_freq_max * self.config["r"],
                input_ref >= self.pfd_freq_min * self.config["r"],
            ]
        )

    def _setup(self, input_ref: int) -> None:
        if isinstance(input_ref, (float, int)):
            assert (
                self.input_freq_max >= input_ref >= self.input_freq_min
            ), "Input frequency out of range"

        # Setup clock chip internal constraints
        self._setup_solver_constraints(input_ref)

        self._clk_names = []  # List of clock names to be generated
        self.config["out_dividers"] = []

    def _get_clock_constraint(
        self, clk_name: str
    ) -> Union[int, float, CpoExpr, GK_Intermediate]:
        """Get abstract clock output.

        Args:
            clk_name (str):  Reference clock name

        Returns:
            (int or float or CpoExpr or GK_Intermediate): Abstract
                or concrete clock reference
        """
        od = self._convert_input(self._o, f"o_div_{clk_name}_adf4030")

        # Update diagram to include new divider
        # d_n = len(self.config["out_dividers"])
        # self._update_diagram({f"o{d_n}": od})

        self._clk_names.append(clk_name)

        self.config["out_dividers"].append(od)
        return self.config["vco"] / od

    def set_requested_clocks(
        self,
        ref_in: Union[int, float, CpoExpr, GK_Intermediate],
        out_freq: Union[int, List[int]],
        clk_names: List[str],
    ) -> None:
        """Define necessary clocks to be generated in model.

        Args:
            ref_in (int, float, CpoExpr, GK_Intermediate): Reference frequency in hertz
            out_freq (int): list of required clocks to be output
            clk_names (List[str]): list of clock names

        Raises:
            Exception: If out_freq and clk_names are not the same length
        """
        if len(out_freq) != len(clk_names):
            raise Exception("out_freq and clk_names must be the same length")
        self._setup(ref_in)
        self._clk_names = clk_names

        for i, clk in enumerate(clk_names):
            o_div_name = f"o_div_{clk}_adf4030"
            self.config[o_div_name] = self._convert_input(self.o, o_div_name)
            self.config["out_dividers"].append(self.config[o_div_name])

            self._add_equation(
                self.config[o_div_name] * out_freq[i] == self.config["vco"],
            )
