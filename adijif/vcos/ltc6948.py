# flake8: noqa
from typing import Dict, List, Union

import numpy as np
from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.clocks.clock import clock
from adijif.solvers import CpoExpr, GK_Intermediate


class ltc6948_bf(clock):
    """Brute force methods for calculating clocks

    These are currently meant for debug to compare against
    the solver solutions
    """

    def list_available_references(self, divider_set):
        """list_available_references: Based on config list possible
        references that can be generated based on VCO and output
        dividers
        """
        # Check input
        ref = {
            "n": 2,
            "vco": 3000000000,
            "r": 24,
            "required_output_divs": np.array([1.0]),
        }
        for key in ref:
            if key not in divider_set:
                raise Exception(
                    "Input must be of type dict with fields: " + str(ref.keys())
                )
        return [divider_set["vco"] / div for div in self.d_available]

    def find_dividers(self, vcxo, rates, find=3):

        raise Exception("Not implemented")

        # v = []
        # for mp in range(0, 32):
        #     for nx in range(0, 8):
        #         val = (mp + 1) * pow(2, nx)
        #         v.append(val)

        # odivs = np.unique(v)

        # mod = np.gcd.reduce(np.array(rates, dtype=int))
        # vcos = []
        # configs = []

        # for n in range(self.n2_divider_min, self.n2_divider_max):
        #     for r in range(self.r2_divider_min, self.r2_divider_max):
        #         # Check VCO in range and output clock a multiple of required reference
        #         f = vcxo * n / r
        #         if f >= self.vco_min and f <= self.vco_max:
        #             # Check if required dividers for output clocks are in set
        #             if f % mod == 0:
        #                 d = f / rates
        #                 if np.all(np.in1d(d, odivs)) and f not in vcos:
        #                     if f not in vcos:
        #                         vcos.append(f)
        #                         config = {
        #                             "n2": n,
        #                             "r2": r,
        #                             "vco": f,
        #                             "required_output_divs": d,
        #                         }
        #                         configs.append(config)
        #                         if len(configs) >= find:
        #                             return configs

        # return configs


class ltc6948(ltc6948_bf):
    """LTC6948 Ultralow Noise 0.37GHz to 6.39GHz Fractional-N Synthesizer with Integrated VCO

    Note this only supports integer mode

    """

    in_ref = 125000000

    # Ranges
    r_divider_min = 1
    r_divider_max = 31
    r_available = [*range(1, 31 + 1)]
    n_divider_min = 32
    n_divider_max = 1023
    n_available = [*range(32, 1023 + 1)]
    n_frac_divider_min = 35
    n_frac_divider_max = 1019
    n_frac_available = [*range(35, 1019 + 1)]
    """ Output dividers """
    o_divider_min = 1
    o_divider_max = 6
    o_available = [*range(1, 6 + 1)]

    _n: Union[int, List[int]] = [*range(1, 65535 + 1)]
    _r: Union[int, List[int]] = [*range(1, 1023 + 1)]

    _o: Union[int, List[int]] = [*range(1, 6 + 1)]

    f_num_divider_min = 1
    f_num_divider_max = 262143  # (2**18-1)

    # Limits
    """ Internal limits """
    _ref_in_min = int(10e6)
    _ref_in_max = int(425e6)
    # VCO limits capture LTC6948-1, LTC6948-2, LTC6948-3, LTC6948-4
    _vco_min = int(2.24e9)
    _vco_max = int(6.39e9)
    _pfd_max = int(100e6)
    _pfd_max_frac = int(76.1e6)
    rfout_min = int(0.373e9)
    rfout_max = int(6.39e9)

    minimize_feedback_dividers = True

    # State management
    _clk_names: List[str] = []

    @property
    def pfd_max(self) -> int:
        """Phase frequency detector maximum frequency.

        Valid range 10->100 MHz

        Returns:
            int: Current allowable pfd max
        """
        return self._pfd_max_frac if self.fractional_mode else self._pfd_max

    @property
    def vco_min(self) -> int:
        """Actual lower VCO frequency.

        Valid range 1->4500 MHz

        Returns:
            int: Current vco minimum value
        """
        return self._vco_min

    @vco_min.setter
    def vco_min(self, value: int) -> None:
        """Actual lower VCO frequency.

                Valid range 1->4500 MHz

        Args:
            value (int): Allowable values for vco min

        """
        self._vco_min = value

    @property
    def vco_max(self) -> int:
        """Actual upper VCO frequency.

        Valid range 1->4500 MHz

        Returns:
            int: Current vco minimum value
        """
        return self._vco_max

    @vco_max.setter
    def vco_max(self, value: int) -> None:
        """Actual upper VCO frequency.

                Valid range 1->4500 MHz

        Args:
            value (float): Allowable values for vco min

        """
        self._vco_max = value

    @property
    def o(self) -> Union[int, List[int]]:
        """Output divider.

        Valid dividers are 1,2,3,4,5,6

        Returns:
            int: Current allowable dividers
        """
        return self._o

    @o.setter
    def o(self, value: Union[int, List[int]]) -> None:
        """Output divider.

        Valid dividers are 1,2,3,4,5,6

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.o_available, "o")
        self._o = value

    @property
    def n(self) -> Union[int, List[int]]:
        """n: VCO feedback divider.

        Valid dividers are 32->1023

        Returns:
            int: Current allowable dividers
        """
        return self._n

    @n.setter
    def n(self, value: Union[int, List[int]]) -> None:
        """VCO feedback divider.

        Valid dividers are 1->65536

        Args:
            value (int, list[int]): Allowable values for divider

        """
        if self.fractional_mode:
            self._check_in_range(value, self.n_frac_available, "n")
        else:
            self._check_in_range(value, self.n_available, "n")
        self._n = value

    @property
    def r(self) -> Union[int, List[int]]:
        """Reference input dividers.

        Valid dividers are 1->31

        Returns:
            int: Current allowable dividers
        """
        return self._r

    @r.setter
    def r(self, value: Union[int, List[int]]) -> None:
        """Reference input dividers.

        Valid dividers are 1->31

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.r_available, "r")
        self._r = value

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

        if self.fractional_mode:
            f = self._get_val(self.config["f_num"]) / 262144
            f_num = self._get_val(self.config["f_num"])
        else:
            f = 0

        clk: float = (
            self.ref_in  # type: ignore # noqa: B950
            * (self._get_val(self.config["n"]) + f)  # type: ignore # noqa: B950
            / self._get_val(self.config["r"])  # type: ignore # noqa: B950
        )

        config: Dict = {
            "r": self._get_val(self.config["r"]),
            "n": self._get_val(self.config["n"]),
            "VCO": clk,
            "ref_in": self.ref_in,
            "out_dividers": out_dividers,
            "output_clocks": [],
            "fractional_mode": self.fractional_mode,
        }
        if self.fractional_mode:
            config["f"] = f
            config["f_numerator"] = f_num

        output_cfg = {}
        for i, div in enumerate(out_dividers):
            rate = clk / div  # type: ignore # noqa: B950
            output_cfg[self._clk_names[i]] = {"rate": rate, "divider": div}

        config["output_clocks"] = output_cfg
        return config

    def _setup_solver_constraints(self, ref_in: int) -> None:
        """Apply constraints to solver model.

        Args:
            ref_in (int): Reference frequency in hertz
        """
        self.ref_in = ref_in
        self.config = {
            "r": self._convert_input(self._r, "r"),
            "n": self._convert_input(self._n, "n"),
        }
        if self.fractional_mode:
            if self.solver == "gekko":
                raise Exception("Gekko does not support LTC6952")
            from adijif.solvers import interval_var

            # self.config['f'] = self._convert_input(self._f, "f")
            # self.config["f_num"] = interval_var(
            #     start=self.f_num_divider_min, end=self.f_num_divider_max
            # )
            # from docplex.cp.expression import interval_var as cp_interval_var
            # self.config["f_num"] = cp_interval_var(
            #     start=self.f_num_divider_min, end=self.f_num_divider_max
            # )
            f = [*range(self.f_num_divider_min, self.f_num_divider_max + 1)]
            self.config["f_num"] = self._convert_input(f, "f_num")

        # PLL equations
        if self.fractional_mode:
            self._add_equation(
                [
                    ref_in <= self.pfd_max * self.config["r"],
                    ref_in * (self.config["n"] + self.config["f_num"] / int(262144))
                    <= self.vco_max * self.config["r"],
                    ref_in * (self.config["n"] + self.config["f_num"] / int(262144))
                    >= self.vco_min * self.config["r"],
                ]
            )
        else:
            self._add_equation(
                [
                    ref_in / self.config["r"] <= self.pfd_max,
                    ref_in / self.config["r"] * self.config["n"] <= self.vco_max,
                    ref_in / self.config["r"] * self.config["n"] >= self.vco_min,
                ]
            )

        # Objectives
        # if self.minimize_feedback_dividers:
        #     self.model.minimize(self.config["r"])
        # self.model.Obj(self.config["r"])

    def _setup(self, ref_in: int) -> None:
        # Setup clock chip internal constraints

        # FIXME: ADD SPLIT m1 configuration support

        # Setup clock chip internal constraints
        self._setup_solver_constraints(ref_in)

        # Add requested clocks to output constraints
        self.config["out_dividers"] = []

    def _get_clock_constraint(
        self, clk_name: List[str]
    ) -> Union[int, float, CpoExpr, GK_Intermediate]:
        """Get abstract clock output.

        Args:
            clk_name (str):  String of clock name

        Returns:
            (int or float or CpoExpr or GK_Intermediate): Abstract
                or concrete clock reference

        Raises:
            Exception: Invalid solver
        """
        if self.solver == "gekko":
            raise Exception("Gekko does not support LTC6952")

        #     __d = self._d if isinstance(self._d, list) else [self._d]

        #     if __d.sort() != self.d_available.sort():
        #         raise Exception("For solver gekko d is not configurable for LTC6952")
        #     # Since d is so disjoint it is very annoying to solve.
        #     mp = self.model.Var(integer=True, lb=1, ub=32)
        #     nx = self.model.Var(integer=True, lb=0, ub=7)
        #     od = self.model.Intermediate(mp * pow(2, nx))
        elif self.solver == "CPLEX":
            od = self._convert_input(self._o, "o_" + str(clk_name))
        else:
            raise Exception("Unknown solver {}".format(self.solver))

        self.config["out_dividers"].append(od)
        return self.vcxo / self.config["r"] * self.config["n"] / od

    def set_requested_clocks(
        self, ref_in: int, out_freqs: List, clk_names: List[str], tolerance: float = 0
    ) -> None:
        """Define necessary clocks to be generated in model.

        Args:
            ref_in (int): Reference in frequency in hertz
            out_freqs (List): list of required clocks to be output
            clk_names (List[str]):  list of strings of clock names

        Raises:
            Exception: If len(out_freqs) != 1
            Exception: If len(clk_names) != 1
        """

        if isinstance(out_freqs, float):
            out_freqs = [out_freqs]
        if isinstance(out_freqs, int):
            out_freqs = [out_freqs]
        if isinstance(clk_names, str):
            clk_names = [clk_names]

        if len(clk_names) != 1:
            raise Exception("Only 1 clock output is supported")
        if len(out_freqs) != 1:
            raise Exception("Only 1 clock output is supported")

        self._clk_names = clk_names

        # Setup clock chip internal constraints
        self._setup(ref_in)

        # Add requested clocks to output constraints
        for out_freq in out_freqs:

            if self.solver == "gekko":
                raise Exception("Gekko does not support LTC6952")
                # __d = self._d if isinstance(self._d, list) else [self._d]
                # if __d.sort() != self.d_available.sort():
                #     raise Exception(
                #         "For solver gekko d is not configurable for LTC6952"
                #     )

                # mp = self.model.Var(integer=True, lb=1, ub=32)
                # nx = self.model.Var(integer=True, lb=0, ub=7)
                # od = self.model.Intermediate(mp * pow(2, nx))

            elif self.solver == "CPLEX":
                od = self._convert_input(self._o, "o_" + str(out_freq))

            if self.fractional_mode:
                if tolerance == 0:
                    self._add_equation(
                        # [
                        #     self.ref_in
                        #     * (self.config["n"] + 0)
                        #     == out_freq * od * self.config["r"]
                        # ]
                        [
                            self.ref_in
                            * (self.config["n"] + (self.config["f_num"] / int(262144)))
                            == out_freq * od * self.config["r"]
                        ]
                    )
                else:
                    self._add_equation(
                        [
                            self.ref_in
                            * (self.config["n"] + (self.config["f_num"] / int(262144)))
                            <= out_freq * od * self.config["r"] * (1 + tolerance),
                            self.ref_in
                            * (self.config["n"] + (self.config["f_num"] / int(262144)))
                            >= out_freq * od * self.config["r"] * (1 - tolerance),
                        ]
                    )
                    if self.solver == "CPLEX":
                        print("HERE")
                        from docplex.cp.modeler import abs

                        self.model.minimize(
                            abs(
                                self.ref_in
                                * (
                                    self.config["n"]
                                    + (self.config["f_num"] / int(262144))
                                )
                                / od
                                / self.config["r"]
                                - out_freq
                            )
                        )
            else:
                self._add_equation(
                    [self.ref_in / self.config["r"] * self.config["n"] / od == out_freq]
                )
            self.config["out_dividers"].append(od)

            # Objectives
            # self.model.Obj(-1*eo) # Favor even dividers
