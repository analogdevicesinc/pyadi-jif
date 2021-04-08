"""AD9523-1 clock chip model."""
from typing import Dict, List, Union

from adijif.clocks.ad9523_1_bf import ad9523_1_bf
from adijif.solvers import CpoIntVar, CpoSolveResult


class ad9523_1(ad9523_1_bf):
    """AD9523-1 clock chip model.

    This model currently supports VCXO+PLL2 configurations
    """

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
    _n2: Union[List[int], int] = [12, 16, 17, 20, 21, 22, 24, 25, 26, *range(28, 255)]
    _r2: Union[List[int], int] = list(range(1, 31 + 1))

    # Limits
    vco_min = 2.94e9
    vco_max = 3.1e9
    pfd_max = 259e6

    # State management
    _clk_names: List[str] = []

    """ Enable internal VCXO/PLL1 doubler """
    use_vcxo_double = False

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

        if self.solver == "CPLEX":
            if not solution:  # type: ignore
                solution = self.solution
            config = {
                "m1": solution.get_value(self.config["m1"].get_name()),
                "n2": solution.get_value(self.config["n2"].get_name()),
                "r2": solution.get_value(self.config["r2"].get_name()),
                "out_dividers": [
                    solution.get_value(x) for x in self.config["out_dividers"]
                ],
                "output_clocks": [],
            }

            if isinstance(self.vcxo, CpoIntVar):
                config["vcxo"] = solution.get_value(self.vcxo.get_name())
                vcxo = config["vcxo"]
            else:
                vcxo = self.vcxo

            clk = vcxo / config["r2"] * config["n2"] / config["m1"]
            output_cfg = {}
            for i, div in enumerate(self.config["out_dividers"]):
                div = solution.get_value(div)
                rate = clk / div
                output_cfg[self._clk_names[i]] = {"rate": rate, "divider": div}
            config["output_clocks"] = output_cfg
            return config
        else:
            config = {
                "m1": self._get_val(self.config["m1"]),
                "n2": self._get_val(self.config["n2"]),
                "r2": self._get_val(self.config["r2"]),
                "out_dividers": [x.value[0] for x in self.config["out_dividers"]],
                "output_clocks": [],
            }

            vcxo = self._get_val(self.vcxo)  # type: ignore
            config["vcxo"] = vcxo

            clk = (
                vcxo  # type: ignore
                / self._get_val(config["r2"])
                * self._get_val(config["n2"])  # type: ignore
                / self._get_val(config["m1"])  # type: ignore
            )
            # for div in self.config["out_dividers"]:
            #     config["output_clocks"].append(clk / div.value[0])

            output_cfg = {}
            for i, div in enumerate(self.config["out_dividers"]):
                rate = clk / div.value[0]
                output_cfg[self._clk_names[i]] = {"rate": rate, "divider": div.value[0]}

        config["output_clocks"] = output_cfg
        return config

    def _setup_solver_constraints(self, vcxo: int) -> None:
        """Apply constraints to solver model.

        Args:
            vcxo (int): VCXO frequency in hertz
        """
        self.config = {
            "r2": self._convert_input(self._r2, "r2"),
            "m1": self._convert_input(self._m1, "m1"),
            "n2": self._convert_input(self._n2, "n2"),
        }
        # self.config = {"r2": self.model.Var(integer=True, lb=1, ub=31, value=1)}
        # self.config["m1"] = self.model.Var(integer=True, lb=3, ub=5, value=3)
        # self.config["n2"] = self.model.sos1(self.n2_available)
        if not isinstance(vcxo, int):
            self.config["vcxo_set"] = vcxo(self.model)
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
        # self.model.Obj(self.config["n2"])

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
        self._clk_names = clk_names

        # Setup clock chip internal constraints
        if self.use_vcxo_double and not isinstance(vcxo, int):
            raise Exception("VCXO doubler not supported in this mode TBD")
        if self.use_vcxo_double:
            vcxo *= 2
        self._setup_solver_constraints(vcxo)

        # FIXME: ADD SPLIT m1 configuration support

        # Add requested clocks to output constraints
        self.config["out_dividers"] = []
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
