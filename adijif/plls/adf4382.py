"""ADF4382 Microwave Wideband Synthesizer with Integrated VCO model."""

from typing import Dict, List, Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.plls.pll import pll
from adijif.solvers import CpoExpr, GK_Intermediate


class adf4382(pll):
    """ADF4382 PLL model.

    This model does not support fractional mode

    https://www.analog.com/media/en/technical-documentation/data-sheets/adf4382.pdf
    """

    name = "adf4382"

    input_freq_min = int(10e6)
    input_freq_max = int(4.5e9)

    # pfd_freq_max_frac = int(160e6)

    # FIXME: This excludes N divider values of 15,28,29,30,31
    """PFD range when N is not 15,28,29,30,31"""
    pfd_freq_min_int_n_wide = int(5.4e6)
    pfd_freq_max_int_n_wide = int(625e6)
    _n_wide = [*range(4, 15)] + [*range(16, 28)] + [*range(32, 4096)]
    """PFD range when N is 15,28,29,30,31"""
    pfd_freq_min_int_n_narrow = int(5.4e6)
    pfd_freq_max_int_n_narrow = int(625e6)
    _n_narrow = [15, 28, 29, 30, 31]

    vco_freq_min = int(11.5e9)
    vco_freq_max = int(21e9)

    _d = [1, 2]
    d_available = [1, 2]

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

    _r = [*range(1, 63 + 1)]
    r_available = [*range(1, 63 + 1)]

    @property
    def r(self) -> Union[int, List[int]]:
        """Reference divider.

        Valid values are 1->(2^6-1)

        Returns:
            int: Current allowable setting
        """
        return self._r

    @r.setter
    def r(self, value: Union[int, List[int]]) -> None:
        """Reference divider.

        Valid values are 1->63

        Args:
            value (int, list[int]): Current allowable setting

        """
        self._check_in_range(value, self.r_available, "r")
        self._r = value

    _o = [1, 2, 4]
    o_available = [1, 2, 4]

    @property
    def o(self) -> Union[int, List[int]]:
        """Output RF divider.

        Valid dividers are 1,2,4

        Returns:
            int: Current allowable dividers
        """
        return self._o

    @o.setter
    def o(self, value: Union[int, List[int]]) -> None:
        """Output RF divider.

        Valid dividers are 1,2,4

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.o_available, "o")
        self._o = value

    _n = [*range(4, 2**12)]
    n_available = [*range(4, 2**12)]

    @property
    def n(self) -> Union[int, List[int]]:
        """Feedback divider.

        Valid dividers are 1->4096

        Returns:
            int: Current allowable dividers
        """
        return self._n

    @n.setter
    def n(self, value: Union[int, List[int]]) -> None:
        """Feedback divider.

        Valid dividers are 1->4096

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.n_available, "n")
        self._n = value

    # _mode = ["integer", "fractional"]
    # mode_available = ["integer", "fractional"]
    _mode = ["integer"]
    mode_available = ["integer"]

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
    # _int_4d5_min_max = [20, 32767]
    # _int_8d9_min_max = [64, 65535]
    # _int_frac_4d5_min_max = [23, 32767]
    # _int_frac_8d9_min_max = [75, 65535]

    # _frac1_min_max = [0, 33554431]
    # _frac2_min_max = [0, 16383]
    # _MOD1 = 2**25
    # _MOD2 = [*range(2, 16383 + 1)]

    # _prescaler = ["4/5", "8/9"]

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
            "n": self.solution.get_kpis()["n"],
            "o": self._get_val(self.config["o"]),
            "r": self._get_val(self.config["r"]),
        }

        # if self._get_val(self.config["fact_0_int_1"]) == 1:
        #     config["mode"] = "fractional"
        # else:
        #     config["mode"] = "integer"

        vco = self.solution.get_kpis()["vco"]
        config["rf_out_frequency"] = vco / config["o"]

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

        if self.solver != "CPLEX":
            raise NotImplementedError("Only CPLEX solver is supported")

        # if not isinstance(input_ref, (int, float)):
        #     self.config["input_ref_set"] = input_ref(self.model)  # type: ignore
        #     input_ref = self.config["input_ref_set"]["range"]
        self.input_ref = input_ref

        # PFD
        self.config["d"] = self._convert_input(self.d, name="d")
        self.config["r"] = self._convert_input(self.r, name="r")
        self.config["n_narrow"] = self._convert_input(self._n_narrow, name="n_narrow")
        self.config["n_wide"] = self._convert_input(self._n_wide, name="n_wide")
        self.config["o"] = self._convert_input(self.o, name="o")

        # Add PFD frequency dependent on N
        self.config["N_is_narrow"] = self._convert_input([0, 1], "N_is_narrow")
        self.config["n"] = self._add_intermediate(
            self.config["N_is_narrow"] * self.config["n_narrow"]
            + (1 - self.config["N_is_narrow"]) * self.config["n_wide"]
        )
        self.model.add_kpi(
            self.config["n"],
            "n",
        )

        # self.config["f_pfd"] = self._add_intermediate(

        self.config["f_pfd"] = self._add_intermediate(
            input_ref * self.config["d"] / self.config["r"]
        )

        # Configure fractional mode or integer mode constraints
        # if self._mode == "fractional":
        #     self.config["fact_0_int_1"] = self._convert_input(0, "fact_0_int_1")
        # elif self._mode == "integer":
        # self.config["fact_0_int_1"] = self._convert_input(1, "fact_0_int_1")
        # else:
        #     self.config["fact_0_int_1"] = self._convert_input([0, 1], "fact_0_int_1")

        self.config["vco"] = self._add_intermediate(
            self.config["f_pfd"] * self.config["n"] * self.config["o"]
        )
        self.model.add_kpi(
            self.config["f_pfd"] * self.config["n"] * self.config["o"],
            "vco",
        )
        min_n = min(self.n if isinstance(self.n, list) else [self.n])
        max_n = max(self.n if isinstance(self.n, list) else [self.n])
        self._add_equation(
            [
                input_ref <= self.input_freq_max,
                input_ref >= self.input_freq_min,
                self.config["f_pfd"]
                >= self.pfd_freq_min_int_n_wide,  # same min for both wide and narrow
                self.config["f_pfd"] * self.config["N_is_narrow"]
                <= self.pfd_freq_max_int_n_narrow,
                self.config["f_pfd"] * (1 - self.config["N_is_narrow"])
                <= self.pfd_freq_max_int_n_wide,
                self.config["vco"] <= self.vco_freq_max,
                self.config["vco"] >= self.vco_freq_min,
                self.config["n"] >= min_n,
                self.config["n"] <= max_n,
            ]
        )

        # Minimize feedback divider to reduce jitter
        # self.model.minimize(self.config['n'])

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

        assert "o" in self.config, "_setup must be called first to set PLL internals"

        return self.config["vco"] / self.config["o"]

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
        print(f"Output: {out_freq}")

        self._add_equation([self.config["o"] * out_freq == self.config["vco"]])
