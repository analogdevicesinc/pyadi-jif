"""AD9523-1 clock chip model."""

from typing import Dict, List, Union

from adijif.clocks.ad9523_1_bf import ad9523_1_bf
from adijif.solvers import CpoExpr, CpoIntVar, CpoSolveResult, GK_Intermediate


class ad9523_1(ad9523_1_bf):
    """AD9523-1 clock chip model.

    This model currently supports VCXO+PLL2 configurations
    """

    name = "AD9523-1"

    # Ranges
    m1_available = [3, 4, 5]
    d_available = [*range(1, 1024)]
    n2_available = [12, 16, 17, 20, 21, 22, 24, 25, 26, *range(28, 255)]
    a_available = [*range(0, 4)]
    b_available = [*range(3, 64)]
    # N = (PxB) + A, P=4, A==[0,1,2,3], B=[3..63]
    # See table 46 of DS for limits
    r2_available = list(range(1, 31 + 1))

    # Defaults
    _m1: Union[List[int], int] = [3, 4, 5]
    _d: Union[List[int], int] = [*range(1, 1024)]
    _n2: Union[List[int], int] = [
        12,
        16,
        17,
        20,
        21,
        22,
        24,
        25,
        26,
        *range(28, 255),
    ]
    _r2: Union[List[int], int] = list(range(1, 31 + 1))

    # Limits
    vco_min = 2.94e9
    vco_max = 3.1e9
    pfd_max = 259e6

    # State management
    _clk_names: List[str] = []

    minimize_feedback_dividers = True

    """ Enable internal VCXO/PLL1 doubler """
    use_vcxo_double = False

    vcxo: Union[int, float, CpoIntVar] = 125e6

    @property
    def m1(self) -> Union[int, List[int]]:
        """VCO divider path 1.

        Valid dividers are 3,4,5

        Returns:
            int: Current allowable dividers
        """
        return self._m1

    @m1.setter
    def m1(self, value: Union[int, List[int]]) -> None:
        """VCO divider path 1.

        Valid dividers are 3,4,5

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.m1_available, "m1")
        self._m1 = value

    @property
    def d(self) -> Union[int, List[int]]:
        """Output dividers.

        Valid dividers are 1->1023

        Returns:
            int: Current allowable dividers
        """
        return self._d

    @d.setter
    def d(self, value: Union[int, List[int]]) -> None:
        """Output dividers.

        Valid dividers are 1->1023

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.d_available, "d")
        self._d = value

    @property
    def n2(self) -> Union[int, List[int]]:
        """n2: VCO feedback divider.

        Valid dividers are 12, 16, 17, 20, 21, 22, 24, 25, 26, 28->255

        Returns:
            int: Current allowable dividers
        """
        return self._n2

    @n2.setter
    def n2(self, value: Union[int, List[int]]) -> None:
        """VCO feedback divider.

        Valid dividers are 12, 16, 17, 20, 21, 22, 24, 25, 26, 28->255

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.n2_available, "n2")
        self._n2 = value

    @property
    def r2(self) -> Union[int, List[int]]:
        """VCXO input dividers.

        Valid dividers are 1->31

        Returns:
            int: Current allowable dividers
        """
        return self._r2

    @r2.setter
    def r2(self, value: Union[int, List[int]]) -> None:
        """VCXO input dividers.

        Valid dividers are 1->31

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.r2_available, "r2")
        self._r2 = value

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
        for k in ["out_dividers", "m1", "n2", "r2"]:
            if k not in self.config.keys():
                raise Exception("Missing key: " + str(k))

        if solution:  # type: ignore
            self.solution = solution
        config: Dict = {
            "m1": self._get_val(self.config["m1"]),
            "n2": self._get_val(self.config["n2"]),
            "r2": self._get_val(self.config["r2"]),
            "out_dividers": [self._get_val(x) for x in self.config["out_dividers"]],
            "output_clocks": [],
        }

        config["vcxo"] = self._get_val(self.vcxo)  # pytype: disable=attribute-error
        vcxo = config["vcxo"]

        clk = vcxo / config["r2"] * config["n2"] / config["m1"]
        output_cfg = {}
        for i, div in enumerate(self.config["out_dividers"]):
            div = self._get_val(div)
            rate = clk / div
            output_cfg[self._clk_names[i]] = {"rate": rate, "divider": div}
        config["output_clocks"] = output_cfg
        config["vco"] = clk
        config["part"] = "AD9523-1"

        self._saved_solution = config

        return config

    def _setup_solver_constraints(self, vcxo: Union[float, int, CpoIntVar]) -> None:
        """Apply constraints to solver model.

        Args:
            vcxo (int): VCXO frequency in hertz

        Raises:
            Exception: Unknown solver
        """
        self.config = {
            "r2": self._convert_input(self._r2, "r2"),
            "m1": self._convert_input(self._m1, "m1"),
            "n2": self._convert_input(self._n2, "n2"),
        }
        if not isinstance(vcxo, (int, float)):
            self.config["vcxo_set"] = vcxo(self.model)  # type: ignore
            vcxo = self.config["vcxo_set"]["range"]
        self.vcxo = vcxo

        # PLL2 equations
        self._add_equation(
            [
                vcxo / self.config["r2"] <= self.pfd_max,
                vcxo / self.config["r2"] * self.config["n2"] <= self.vco_max,
                vcxo / self.config["r2"] * self.config["n2"] >= self.vco_min,
            ]
        )
        # Objectives
        if self.minimize_feedback_dividers:
            if self.solver == "CPLEX":
                ...
                # self.model.minimize(self.config["n2"])
                # cost = self.model
                # self.model.minimize_static_lex([self.config["n2"],])
            elif self.solver == "gekko":
                self.model.Obj(self.config["n2"])
            else:
                raise Exception("Unknown solver {}".format(self.solver))

    def _add_objective(self, sys_refs: List[CpoIntVar]) -> None:
        # Minimize feedback divider and sysref frequencies
        if self.minimize_feedback_dividers:
            self._objectives = [self.config["n2"]] + sys_refs
            # self.model.add(
            #     self.model.minimize_static_lex([self.config["n2"]] + sys_refs)
            # )
        else:
            self._objectives = [sys_refs]
            # self.model.add(self.model.minimize_static_lex(sys_refs))

    def _setup(self, vcxo: int) -> None:
        # Setup clock chip internal constraints

        # FIXME: ADD SPLIT m1 configuration support

        if self.use_vcxo_double and not isinstance(vcxo, int):
            raise Exception("VCXO doubler not supported in this mode TBD")
        if self.use_vcxo_double:
            vcxo *= 2
        self._setup_solver_constraints(vcxo)
        self.config["out_dividers"] = []
        self._clk_names = []  # Reset clock names to be generated

    def _get_clock_constraint(
        self, clk_name: List[str]
    ) -> Union[int, float, CpoExpr, GK_Intermediate]:
        """Get abstract clock output.

        Args:
            clk_name (str):  String of clock name

        Returns:
            (int or float or CpoExpr or GK_Intermediate): Abstract
                or concrete clock reference
        """
        od = self._convert_input(self._d, "d_" + str(clk_name))
        self.config["out_dividers"].append(od)
        self._clk_names.append(clk_name)
        return (
            self.vcxo / self.config["r2"] * self.config["n2"] / self.config["m1"] / od
        )

    def set_requested_clocks(
        self, vcxo: int, out_freqs: List, clk_names: List[str]
    ) -> None:
        """Define necessary clocks to be generated in model.

        Args:
            vcxo (int): VCXO frequency in hertz
            out_freqs (List): list of required clocks to be output
            clk_names (List[str]):  list of strings of clock names

        Raises:
            Exception: If len(out_freqs) != len(clk_names)
        """
        if len(clk_names) != len(out_freqs):
            raise Exception("clk_names is not the same size as out_freqs")

        # Setup clock chip internal constraints
        self._setup(vcxo)
        self._clk_names = clk_names

        # Add requested clocks to output constraints
        for out_freq in out_freqs:
            # od = self.model.Var(integer=True, lb=1, ub=1023, value=1)
            od = self._convert_input(self._d, "d_" + str(out_freq))
            # od = self.model.sos1([n*n for n in range(1,9)])

            self._add_equation(
                [
                    self.vcxo
                    / self.config["r2"]
                    * self.config["n2"]
                    / self.config["m1"]
                    / od
                    == out_freq
                ]
            )
            self.config["out_dividers"].append(od)
