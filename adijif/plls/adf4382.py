"""ADF4382 Microwave Wideband Synthesizer with Integrated VCO model."""

from typing import Dict, List, Union

from docplex.cp.modeler import if_then
from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.plls.pll import pll
from adijif.solvers import CpoExpr, GK_Intermediate, integer_var


def to_int(value: Union[int, float, List[int], List[float]]) -> Union[int, List[int]]:
    """Convert value to int or list of ints."""
    if isinstance(value, (int, float)):
        return int(value)
    elif isinstance(value, list):
        return [int(v) for v in value]
    else:
        raise TypeError(f"Unsupported type: {type(value)}")


class adf4382(pll):
    """ADF4382 PLL model.

    This model does not support fractional mode

    https://www.analog.com/media/en/technical-documentation/data-sheets/adf4382.pdf
    """

    name = "adf4382"

    input_freq_min = int(10e6)
    input_freq_max = int(4.5e9)

    # pfd_freq_max_frac = int(160e6)
    """Input reference doubler range"""
    freq_doubler_input_min = int(10e6)
    freq_doubler_input_max = int(2000e6)

    """PFD frequency ranges"""
    # Integer
    pfd_freq_min_int_n_wide = int(5.4e6)
    pfd_freq_max_int_n_wide = int(625e6)
    # n full [*range(4, 4095+1)] minus 15, 28, 31
    _n_int_wide = (
        [*range(4, 15)] + [*range(16, 28)] + [*range(29, 31)] + [*range(32, 4095 + 1)]
    )
    pfd_freq_min_int_n_narrow = int(5.4e6)
    pfd_freq_max_int_n_narrow = int(540e6)
    _n_int_narrow = [15, 28, 31]
    # Fractional
    # n full [*range(19, 4095+1)]
    pfd_freq_min_frac_modes_0_4 = int(5.4e6)
    pfd_freq_max_frac_modes_0_4 = int(250e6)
    _n_frac_modes_0_4 = {
        "mode_0": to_int([*range(10, 4095 + 1)]),
        "mode_4": to_int([*range(23, 4095 + 1)]),
    }
    pfd_freq_min_frac_modes_5 = int(5.4e6)
    pfd_freq_max_frac_modes_5 = int(220e6)
    _n_frac_modes_5 = to_int([*range(27, 4095 + 1)])

    vco_freq_min = int(11e9)
    vco_freq_max = int(22e9)

    _d = to_int([1, 2])
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

    _mode = ["integer"]  # Dont use fractional mode by default
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
    _frac1_min_max = [0, 2**25 - 1]
    _frac2_min_max = [0, 2**24 - 1]
    _MOD1 = 33554432  # 2^25
    _MOD2_PHASE_SYNC_min_max = [1, 2**17 - 1]
    _MOD2_NO_PHASE_SYNC_min_max = [1, 2**24 - 1]

    _phase_sync = True

    @property
    def require_phase_sync(self) -> bool:
        """Determine if phase sync is required.

        Returns:
            bool: True if phase sync is required
        """
        return self._phase_sync

    @require_phase_sync.setter
    def require_phase_sync(self, value: bool) -> None:
        """Determine if phase sync is required.

        Args:
            value (bool): True if phase sync is required
        """
        self._check_in_range(value, [True, False], "require_phase_sync")
        self._phase_sync = value

    _EFM3_MODE = [0, 4, 5]
    EFM3_MODE_available = [0, 4, 5]

    @property
    def EFM3_MODE(self) -> Union[int, List[int]]:
        """Set EFM3 optimization mode.

        Options are: 0, 4, 5

        Returns:
            int: Current allowable modes
        """
        return self._EFM3_MODE

    @EFM3_MODE.setter
    def EFM3_MODE(self, value: Union[int, List[int]]) -> None:
        """Set EFM3 optimization mode.

        Options are: 0, 4, 5

        Args:
            value (int, list[int]): Allowable values for mode

        """
        self._check_in_range(value, self.EFM3_MODE_available, "EFM3_MODE")
        self._EFM3_MODE = value

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
            # "n": self.solution.get_kpis()["n"],
            "o": self._get_val(self.config["o"]),
            "r": self._get_val(self.config["r"]),
        }
        if isinstance(self._n, list):
            config["n"] = self.solution.get_kpis()["n"]
        else:
            config["n"] = self._n

        if self._mode == "integer" or self._mode == ["integer"]:
            mode = "integer"
        elif self._mode == "fractional" or self._mode == ["fractional"]:
            mode = "fractional"
        else:
            if self._get_val(self.config["frac_0_int_1"]) == 1:
                mode = "integer"
            else:
                mode = "fractional"

        if mode == "integer":
            config["mode"] = "integer"
        else:
            config["mode"] = "fractional"
            config["n_frac1w"] = self._get_val(self.config["n_frac1w"])
            config["n_frac2w"] = self._get_val(self.config["n_frac2w"])
            config["MOD1"] = self._MOD1
            config["MOD2"] = self._get_val(self.config["MOD2"])
            config["n_int"] = self._get_val(self.config["n_int"])
            config["EFM3_MODE"] = self._get_val(self.config["EFM3_MODE"])

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
        self.config["o"] = self._convert_input(self.o, name="o")

        if self._mode == "integer":
            self.config["frac_0_int_1"] = 1
        elif self._mode == "fractional":
            self.config["frac_0_int_1"] = 0
        else:
            self.config["frac_0_int_1"] = self._convert_input(
                [0, 1], name="frac_0_int_1"
            )

        self.config["EFM3_MODE"] = self._convert_input(self.EFM3_MODE, name="EFM3_MODE")
        if isinstance(self.EFM3_MODE, list):
            self.model.add_kpi(self.config["EFM3_MODE"], "EFM3_MODE")

        # N which supports fractional modes
        if "fractional" in self._mode:
            self.config["n_int"] = self._convert_input(self._n, name="n_int")
            self.config["n_frac1w"] = integer_var(
                min=self._frac1_min_max[0],
                max=self._frac1_min_max[1],
                name="n_frac1w",
            )
            self.config["n_frac2w"] = integer_var(
                min=self._frac2_min_max[0],
                max=self._frac2_min_max[1],
                name="n_frac2w",
            )
            _MOD2_min_max = (
                self._MOD2_PHASE_SYNC_min_max
                if self._phase_sync
                else self._MOD2_NO_PHASE_SYNC_min_max
            )
            self.config["MOD2"] = integer_var(
                min=_MOD2_min_max[0],
                max=_MOD2_min_max[1],
                name="MOD2",
            )
            self.config["n_frac"] = self._add_intermediate(
                (
                    self.config["n_frac1w"]
                    + self.config["n_frac2w"] / self.config["MOD2"]
                )
                / self._MOD1
            )
            # Constraints
            self._add_equation(
                if_then(
                    self.config["frac_0_int_1"] == 1,
                    self.config["n_frac"] == 0,
                )
            )
            self._add_equation(
                if_then(
                    self.config["frac_0_int_1"] == 0,
                    100000 * self.config["n_frac"] < 100000,
                )
            )
            self._add_equation(
                if_then(
                    self.config["frac_0_int_1"] == 0,
                    self.config["n_frac1w"] + self.config["n_frac2w"] > 0,
                )
            )
            self._add_equation(
                if_then(
                    self.config["frac_0_int_1"] == 0,
                    self.config["MOD2"] > self.config["n_frac2w"],
                )
            )

            self.config["n"] = self._add_intermediate(
                self.config["n_int"] + self.config["n_frac"]
            )
        else:
            self.config["n"] = self._convert_input(self._n, name="n_int")

        if isinstance(self._mode, list):
            # self.model.maximize(self.config["frac_0_int_1"])
            self._add_objective(self.config["frac_0_int_1"])

        # Add PFD frequency dependent on N
        if isinstance(self._n, list) and len(self._n) > 1:
            self.model.add_kpi(
                self.config["n"],
                "n",
            )

        # Add EFM3 mode constraints on N
        self._add_equation(
            [
                if_then(
                    self.config["EFM3_MODE"] == 0,
                    self.config["n"] >= min(self._n_frac_modes_0_4["mode_0"]),
                ),
                if_then(
                    self.config["EFM3_MODE"] == 4,
                    self.config["n"] >= min(self._n_frac_modes_0_4["mode_4"]),
                ),
                if_then(
                    self.config["EFM3_MODE"] == 5,
                    self.config["n"] >= min(self._n_frac_modes_5),
                ),
            ]
        )

        # Clocking rates
        self.config["f_pfd"] = self._add_intermediate(
            input_ref * self.config["d"] / self.config["r"]
        )

        self.config["vco"] = self._add_intermediate(
            self.config["f_pfd"] * self.config["n"] * self.config["o"]
        )
        self.model.add_kpi(
            self.config["f_pfd"] * self.config["n"] * self.config["o"],
            "vco",
        )

        # Add PFD frequency constraints for integer mode
        self._add_equation(
            [
                if_then(
                    self.config["frac_0_int_1"] == 1,
                    if_then(
                        self.config["n"] == 15,
                        self.config["f_pfd"] <= self.pfd_freq_max_int_n_narrow,
                    ),
                ),
                if_then(
                    self.config["frac_0_int_1"] == 1,
                    if_then(
                        self.config["n"] == 28,
                        self.config["f_pfd"] <= self.pfd_freq_max_int_n_narrow,
                    ),
                ),
                if_then(
                    self.config["frac_0_int_1"] == 1,
                    if_then(
                        self.config["n"] == 31,
                        self.config["f_pfd"] <= self.pfd_freq_max_int_n_narrow,
                    ),
                ),
                # Wide is a looser upper bound but applies to all cases
                if_then(
                    self.config["frac_0_int_1"] == 1,
                    self.config["f_pfd"] <= self.pfd_freq_max_int_n_wide,
                ),
            ]
        )

        # Add PFD frequency constraints for fractional mode
        self._add_equation(
            [
                if_then(
                    self.config["frac_0_int_1"] == 0,
                    if_then(
                        self.config["EFM3_MODE"] == 0,
                        self.config["f_pfd"] <= self.pfd_freq_max_frac_modes_0_4,
                    ),
                ),
                if_then(
                    self.config["frac_0_int_1"] == 0,
                    if_then(
                        self.config["EFM3_MODE"] == 4,
                        self.config["f_pfd"] <= self.pfd_freq_max_frac_modes_0_4,
                    ),
                ),
                if_then(
                    self.config["frac_0_int_1"] == 0,
                    if_then(
                        self.config["EFM3_MODE"] == 5,
                        self.config["f_pfd"] <= self.pfd_freq_max_frac_modes_5,
                    ),
                ),
            ]
        )

        # Global min for PFD
        self._add_equation(
            [
                self.config["f_pfd"] >= self.pfd_freq_min_int_n_wide,
            ]
        )

        # Add remaining constraints
        self._add_equation(
            [
                input_ref <= self.input_freq_max,
                input_ref >= self.input_freq_min,
                input_ref * self.config["d"] <= self.freq_doubler_input_max,
                input_ref * self.config["d"] >= self.freq_doubler_input_min,
                self.config["vco"] <= self.vco_freq_max,
                self.config["vco"] >= self.vco_freq_min,
            ]
        )

        # Minimize feedback divider to reduce jitter
        self._add_objective(1 / self.config["n"])
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
