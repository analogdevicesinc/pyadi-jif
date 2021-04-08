"""AD9528 clock chip model."""
from typing import Dict, List, Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.clocks.ad9528_bf import ad9528_bf


class ad9528(ad9528_bf):
    """AD9528 clock chip model.

    This model currently supports VCXO+PLL2 configurations
    """

    # Ranges
    """ VCO divider """
    m1_available = [3, 4, 5]
    """ Output dividers """
    d_available = [*range(1, 1024)]
    """ VCXO multiplier """
    n2_available = [*range(12, 256)]
    # N = (PxB) + A, P=4, A==[0,1,2,3], B=[3..63]
    # See table 46 of DS for limits
    """ VCXO dividers """
    r1_available = [*range(1, 32)]

    # State management
    _clk_names: List[str] = []

    # Defaults
    _m1: Union[List[int], int] = [3, 4, 5]
    _d: Union[List[int], int] = [*range(1, 1024)]
    _n2: Union[List[int], int] = [*range(12, 255)]
    _r1: Union[List[int], int] = [*range(1, 32)]

    # Limits
    vco_min = 3450e6
    vco_max = 4025e6
    pfd_max = 275e6

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

        Valid dividers are 12->255

        Returns:
            int: Current allowable dividers
        """
        return self._m2

    @n2.setter
    def n2(self, value: Union[int, List[int]]) -> None:
        """VCO feedback divider.

        Valid dividers are 12->255

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.n2_available, "n2")
        self._m2 = value

    @property
    def r1(self) -> Union[int, List[int]]:
        """VCXO input dividers.

        Valid dividers are 1->31

        Returns:
            int: Current allowable dividers
        """
        return self._r1

    @r1.setter
    def r1(self, value: Union[int, List[int]]) -> None:
        """VCXO input dividers.

        Valid dividers are 1->31

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.r1_available, "r1")
        self._r1 = value

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
            "r1": self._get_val(self.config["r1"]),
            "n2": self._get_val(self.config["n2"]),
            "m1": self._get_val(self.config["m1"]),
            "out_dividers": [self._get_val(x) for x in self.config["out_dividers"]],
            "output_clocks": [],
        }

        clk = self.vcxo / config["r1"] * config["n2"]

        output_cfg = {}
        for i, div in enumerate(self.config["out_dividers"]):
            rate = clk / self._get_val(div)
            output_cfg[self._clk_names[i]] = {
                "rate": rate,
                "divider": self._get_val(div),
            }

        config["output_clocks"] = output_cfg
        return config

    def _setup_solver_constraints(self, vcxo: int) -> None:
        """Apply constraints to solver model.

        Args:
            vcxo (int): VCXO frequency in hertz
        """
        self.vcxo = vcxo
        self.config = {
            "r1": self._convert_input(self._r1, "r1"),
            "m1": self._convert_input(self._m1, "m1"),
            "n2": self._convert_input(self._n2, "n2"),
        }
        # self.config = {"r1": self.model.Var(integer=True, lb=1, ub=31, value=1)}
        # self.config["m1"] = self.model.Var(integer=True, lb=3, ub=5, value=3)
        # self.config["n2"] = self.model.Var(integer=True, lb=12, ub=255, value=12)

        # PLL2 equations
        self._add_equation(
            [
                vcxo / self.config["r1"] <= self.pfd_max,
                vcxo / self.config["r1"] * self.config["m1"] * self.config["n2"]
                <= self.vco_max,
                vcxo / self.config["r1"] * self.config["m1"] * self.config["n2"]
                >= self.vco_min,
            ]
        )
        # Minimization objective
        # self.model.Obj(self.config["n2"] * self.config["m1"])

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
        if self.use_vcxo_double:
            vcxo *= 2
        self._setup_solver_constraints(vcxo)

        # Add requested clocks to output constraints
        self.config["out_dividers"] = []
        for out_freq in out_freqs:
            # od = self.model.Var(integer=True, lb=1, ub=256, value=1)
            od = self._convert_input(self._d, "d_" + str(out_freq))
            # od = self.model.sos1([n*n for n in range(1,9)])
            self._add_equation(
                [vcxo / self.config["r1"] * self.config["n2"] / od == out_freq]
            )
            self.config["out_dividers"].append(od)
