"""ADF4371 Microwave Wideband Synthesizer with Integrated VCO model."""

from typing import Dict, List, Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.plls.pll import pll
from adijif.solvers import CpoExpr, GK_Intermediate, integer_var, tround


class adf4371(pll):
    """ADF4371 PLL model.

    This model currently supports all divider configurations

    https://www.analog.com/media/en/technical-documentation/data-sheets/adf4371.pdf
    """

    name = "adf4371"

    input_freq_max = int(600e6)
    input_freq_min = int(10e6)

    pfd_freq_max_frac = int(160e6)
    pfd_freq_max_int = int(250e6)

    vco_freq_max = int(8e9)
    vco_freq_min = int(4e9)

    _d = [0, 1]
    d_available = [0, 1]

    @property
    def d(self) -> Union[int, List[int]]:
        """REF-in doubler.

        Valid values are 1,2

        Returns:
            int: Current allowable setting
        """
        return self._d

    @d.setter
    def d(self, value: Union[int, List[int]]) -> None:
        """REF-in double.

        Valid values are 1,2

        Args:
            value (int, list[int]): Current allowable setting

        """
        self._check_in_range(value, self.d_available, "d")
        self._d = value

    _r = [*range(1, 32 + 1)]
    r_available = [*range(1, 32 + 1)]

    @property
    def r(self) -> Union[int, List[int]]:
        """Reference divider.

        Valid values are 0->(2^5-1)

        Returns:
            int: Current allowable setting
        """
        return self._r

    @r.setter
    def r(self, value: Union[int, List[int]]) -> None:
        """Reference divider.

        Valid values are 1->32

        Args:
            value (int, list[int]): Current allowable setting

        """
        self._check_in_range(value, self.r_available, "r")
        self._r = value

    _t = [0, 1]
    t_available = [0, 1]

    @property
    def t(self) -> Union[int, List[int]]:
        """Reference divide by 2.

        Valid values are 0,1

        Returns:
            int: Current allowable setting
        """
        return self._t

    @t.setter
    def t(self, value: Union[int, List[int]]) -> None:
        """Reference divide by 2.

        Valid values are 0,1

        Args:
            value (int, list[int]): Current allowable setting

        """
        self._check_in_range(value, self.t_available, "t")
        self._t = value

    _rf_div = [1, 2, 4, 8, 16, 32, 64]
    rf_div_available = [1, 2, 4, 8, 16, 32, 64]

    @property
    def rf_div(self) -> Union[int, List[int]]:
        """Output RF divider.

        Valid dividers are 1,2,3,4,5,6..32->(even)->4096

        Returns:
            int: Current allowable dividers
        """
        return self._rf_div

    @rf_div.setter
    def rf_div(self, value: Union[int, List[int]]) -> None:
        """Output RF divider.

        Valid dividers are 1,2,3,4,5,6..32->(even)->4096

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.rf_div_available, "rf_div")
        self._rf_div = value

    _mode = ["integer", "fractional"]
    mode_available = ["integer", "fractional"]

    @property
    def mode(self) -> Union[str, List[str]]:
        """Set operational mode.

        Options are: fractional, integer or [fractional, integer]

        Returns:
            str: Current allowable modes
        """
        return self._mode

    @mode.setter
    def mode(self, value: Union[str, List[str]]) -> None:
        """Set operational mode.

        Options are: fractional, integer or [fractional, integer]

        Args:
            value (str, list[str]): Allowable values for mode

        """
        self._check_in_range(value, self.mode_available, "mode")
        self._mode = value

    # These are too large for user to set
    _int_4d5_min_max = [20, 32767]
    _int_8d9_min_max = [64, 65535]
    _int_frac_4d5_min_max = [23, 32767]
    _int_frac_8d9_min_max = [75, 65535]

    _frac1_min_max = [0, 33554431]
    _frac2_min_max = [0, 16383]
    _MOD1 = 2**25
    _MOD2 = [*range(2, 16383 + 1)]

    _prescaler = ["4/5", "8/9"]

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

        config: Dict = {
            "d": self._get_val(self.config["d"]),
            "r": self._get_val(self.config["r"]),
            "t": self._get_val(self.config["t"]),
            "frac1": self._get_val(self.config["frac1"]),
            "frac2": self._get_val(self.config["frac2"]),
            "MOD2": self._get_val(self.config["MOD2"]),
            "int": self._get_val(self.config["int"]),
            "rf_div": self._get_val(self.config["rf_div"]),
        }

        if self._get_val(self.config["fact_0_int_1"]) == 1:
            config["mode"] = "fractional"
        else:
            config["mode"] = "integer"

        if self._get_val(self.config["prescaler_4/5_0_8/9_1"]) == 1:
            config["prescaler"] = "8/9"
        else:
            config["prescaler"] = "4/5"

        vco = self.solution.get_kpis()["vco"]
        config["rf_out_frequency"] = vco / config["rf_div"]
        config["rf_out_frequency"] = tround(config["rf_out_frequency"])

        return config

    def _setup_solver_constraints(
        self, input_ref: Union[int, float, CpoExpr, GK_Intermediate]
    ) -> None:
        """Apply constraints to solver model.

        Args:
            input_ref (int, float, CpoExpr, GK_Intermediate): Input reference
                frequency in hertz

        Raises:
            NotImplementedError: If solver is not CPLEX
        """
        self.config = {}

        # if not isinstance(input_ref, (int, float)):
        #     self.config["input_ref_set"] = input_ref(self.model)  # type: ignore
        #     input_ref = self.config["input_ref_set"]["range"]
        self.input_ref = input_ref

        # PFD
        self.config["d"] = self._convert_input(self.d, name="d")
        self.config["r"] = self._convert_input(self.r, name="r")
        self.config["t"] = self._convert_input(self.t, name="t")

        self.config["f_pfd"] = self._add_intermediate(
            input_ref
            * ((1 + self.config["d"]) / (self.config["r"] * (1 + self.config["t"])))
        )

        # Configure fractional mode or integer mode constraints
        if self._mode == "fractional":
            self.config["fact_0_int_1"] = self._convert_input(0, "fact_0_int_1")
        elif self._mode == "integer":
            self.config["fact_0_int_1"] = self._convert_input(1, "fact_0_int_1")
        else:
            self.config["fact_0_int_1"] = self._convert_input([0, 1], "fact_0_int_1")

        self.config["pfd_max_freq"] = self._add_intermediate(
            (1 - self.config["fact_0_int_1"]) * self.pfd_freq_max_frac
            + self.config["fact_0_int_1"] * self.pfd_freq_max_int,
        )

        # VCO + output
        self.config["MOD2"] = self._convert_input(self._MOD2, name="MOD2")

        # Configure INT setting based on prescalers
        if self.solver == "CPLEX":
            self.config["frac1"] = integer_var(
                min=self._frac1_min_max[0],
                max=self._frac1_min_max[1],
                name="frac1",
            )
            self.config["frac2"] = integer_var(
                min=self._frac2_min_max[0],
                max=self._frac2_min_max[1],
                name="frac2",
            )

            if self._prescaler == "4/5":
                self.config["prescaler_4/5_0_8/9_1"] = self._convert_input(
                    0, "prescaler"
                )
            elif self._prescaler == "8/9":
                self.config["prescaler_4/5_0_8/9_1"] = self._convert_input(
                    1, "prescaler"
                )
            else:
                self.config["prescaler_4/5_0_8/9_1"] = self._convert_input(
                    [0, 1], "prescaler"
                )

            self.config["int_min"] = self._add_intermediate(
                self.config["fact_0_int_1"]
                * (
                    self.config["prescaler_4/5_0_8/9_1"] * self._int_8d9_min_max[0]
                    + (1 - self.config["prescaler_4/5_0_8/9_1"])
                    * self._int_4d5_min_max[0]
                )
                + (1 - self.config["fact_0_int_1"])
                * (
                    self.config["prescaler_4/5_0_8/9_1"] * self._int_frac_8d9_min_max[0]
                    + (1 - self.config["prescaler_4/5_0_8/9_1"])
                    * self._int_frac_4d5_min_max[0]
                )
            )

            self.config["int_max"] = self._add_intermediate(
                self.config["fact_0_int_1"]
                * (
                    self.config["prescaler_4/5_0_8/9_1"] * self._int_8d9_min_max[1]
                    + (1 - self.config["prescaler_4/5_0_8/9_1"])
                    * self._int_4d5_min_max[1]
                )
                + (1 - self.config["fact_0_int_1"])
                * (
                    self.config["prescaler_4/5_0_8/9_1"] * self._int_frac_8d9_min_max[1]
                    + (1 - self.config["prescaler_4/5_0_8/9_1"])
                    * self._int_frac_4d5_min_max[1]
                )
            )

            min_o = min(
                [
                    self._int_8d9_min_max[0],
                    self._int_4d5_min_max[0],
                    self._int_frac_8d9_min_max[0],
                    self._int_frac_4d5_min_max[0],
                ]
            )
            max_o = max(
                [
                    self._int_8d9_min_max[1],
                    self._int_4d5_min_max[1],
                    self._int_frac_8d9_min_max[1],
                    self._int_frac_4d5_min_max[1],
                ]
            )
            self.config["int"] = integer_var(min=min_o, max=max_o, name="int")
        else:
            raise NotImplementedError("Only CPLEX solver is implemented")

        self.config["vco"] = self._add_intermediate(
            (
                self.config["int"]
                + (self.config["frac1"] + self.config["frac2"] / self.config["MOD2"])
                / self._MOD1
            )
            * self.config["f_pfd"]
        )
        self.model.add_kpi(
            (
                self.config["int"]
                + (self.config["frac1"] + self.config["frac2"] / self.config["MOD2"])
                / self._MOD1
            )
            * self.config["f_pfd"],
            "vco",
        )

        self._add_equation(
            [
                input_ref <= self.input_freq_max,
                input_ref >= self.input_freq_min,
                self.config["f_pfd"] <= self.config["pfd_max_freq"],
                self.config["vco"] <= self.vco_freq_max,
                self.config["vco"] >= self.vco_freq_min,
                self.config["int"] <= self.config["int_max"],
                self.config["int"] >= self.config["int_min"],
            ]
        )

    def _setup(self, input_ref: int) -> None:
        if isinstance(input_ref, (float, int)):
            assert (
                self.input_freq_max >= input_ref >= self.input_freq_min
            ), "Input frequency out of range"

        # Setup clock chip internal constraints
        self._setup_solver_constraints(input_ref)

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
        self._clk_names = ["clk_name"]

        self.config["rf_div"] = self._convert_input(self.rf_div, "rf_div")

        return self.config["vco"] / self.config["rf_div"]

    def set_requested_clocks(
        self, ref_in: Union[int, float, CpoExpr, GK_Intermediate], out_freq: int
    ) -> None:
        """Define necessary clocks to be generated in model.

        Args:
            ref_in (int, float, CpoExpr, GK_Intermediate): Reference frequency in hertz
            out_freq (int): list of required clocks to be output

        """
        self._setup(ref_in)
        self._clk_names = ["rf_out"]

        self.config["rf_div"] = self._convert_input(self.rf_div, "rf_div")

        self._add_equation([self.config["rf_div"] * out_freq == self.config["vco"]])
