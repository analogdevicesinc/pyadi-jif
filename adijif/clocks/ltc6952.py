"""LTC6952 clock chip model."""

from typing import Dict, List, Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.clocks.ltc6952_bf import ltc6952_bf
from adijif.solvers import CpoExpr, GK_Intermediate


class ltc6952(ltc6952_bf):
    """LTC6952 clock chip model.

    This model currently supports VCXO+PLL2 configurations
    """

    name = "LTC6952"

    vcxo = 125000000

    # Ranges
    r2_divider_min = 1
    r2_divider_max = 1023
    r2_available = [*range(1, 1023 + 1)]
    n2_divider_min = 1
    n2_divider_max = 65535
    n2_available = [*range(1, 65535 + 1)]

    """ Output dividers """
    d_available = [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        34,
        36,
        38,
        40,
        42,
        44,
        46,
        48,
        50,
        52,
        54,
        56,
        58,
        60,
        62,
        64,
        68,
        72,
        76,
        80,
        84,
        88,
        92,
        96,
        100,
        104,
        108,
        112,
        116,
        120,
        124,
        128,
        136,
        144,
        152,
        160,
        168,
        176,
        184,
        192,
        200,
        208,
        216,
        224,
        232,
        240,
        248,
        256,
        272,
        288,
        304,
        320,
        336,
        352,
        368,
        384,
        400,
        416,
        432,
        448,
        464,
        480,
        496,
        512,
        544,
        576,
        608,
        640,
        672,
        704,
        736,
        768,
        800,
        832,
        864,
        896,
        928,
        960,
        992,
        1024,
        1088,
        1152,
        1216,
        1280,
        1344,
        1408,
        1472,
        1536,
        1600,
        1664,
        1728,
        1792,
        1856,
        1920,
        1984,
        2048,
        2176,
        2304,
        2432,
        2560,
        2688,
        2816,
        2944,
        3072,
        3200,
        3328,
        3456,
        3584,
        3712,
        3840,
        3968,
        4096,
    ]

    # Defaults
    _d: Union[int, List[int]] = [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        34,
        36,
        38,
        40,
        42,
        44,
        46,
        48,
        50,
        52,
        54,
        56,
        58,
        60,
        62,
        64,
        68,
        72,
        76,
        80,
        84,
        88,
        92,
        96,
        100,
        104,
        108,
        112,
        116,
        120,
        124,
        128,
        136,
        144,
        152,
        160,
        168,
        176,
        184,
        192,
        200,
        208,
        216,
        224,
        232,
        240,
        248,
        256,
        272,
        288,
        304,
        320,
        336,
        352,
        368,
        384,
        400,
        416,
        432,
        448,
        464,
        480,
        496,
        512,
        544,
        576,
        608,
        640,
        672,
        704,
        736,
        768,
        800,
        832,
        864,
        896,
        928,
        960,
        992,
        1024,
        1088,
        1152,
        1216,
        1280,
        1344,
        1408,
        1472,
        1536,
        1600,
        1664,
        1728,
        1792,
        1856,
        1920,
        1984,
        2048,
        2176,
        2304,
        2432,
        2560,
        2688,
        2816,
        2944,
        3072,
        3200,
        3328,
        3456,
        3584,
        3712,
        3840,
        3968,
        4096,
    ]
    _n2: Union[int, List[int]] = [*range(1, 65535 + 1)]
    _r2: Union[int, List[int]] = [*range(1, 1023 + 1)]

    # Limits
    """ Internal limits """
    _vco_min = 1e6  # uses external VCO limits need to be set by the user
    _vco_max = 4500e6
    pfd_max = 167e6
    vcxo_min = 1e6
    vcxo_max = 500e6

    minimize_feedback_dividers = False

    # State management
    _clk_names: List[str] = []

    @property
    def vco_min(self) -> float:
        """Actual lower VCO frequency.

        Valid range 1->4500 MHz

        Returns:
            float: Current vco minimum value
        """
        return self._vco_min

    @vco_min.setter
    def vco_min(self, value: float) -> None:
        """Actual lower VCO frequency.

                Valid range 1->4500 MHz

        Args:
            value (float): Allowable values for vco min

        """
        self._vco_min = value

    @property
    def vco_max(self) -> float:
        """Actual upper VCO frequency.

        Valid range 1->4500 MHz

        Returns:
            float: Current vco minimum value
        """
        return self._vco_max

    @vco_max.setter
    def vco_max(self, value: float) -> None:
        """Actual upper VCO frequency.

                Valid range 1->4500 MHz

        Args:
            value (float): Allowable values for vco min

        """
        self._vco_max = value

    @property
    def d(self) -> Union[int, List[int]]:
        """Output dividers.

        Valid dividers are 1,2,3,4,5,6..32->(even)->4096

        Returns:
            int: Current allowable dividers
        """
        return self._d

    @d.setter
    def d(self, value: Union[int, List[int]]) -> None:
        """Output dividers.

        Valid dividers are 1,2,3,4,5,6..32->(even)->4096

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.d_available, "d")
        self._d = value

    @property
    def n2(self) -> Union[int, List[int]]:
        """n2: VCO feedback divider.

        Valid dividers are 1->65536

        Returns:
            int: Current allowable dividers
        """
        return self._n2

    @n2.setter
    def n2(self, value: Union[int, List[int]]) -> None:
        """VCO feedback divider.

        Valid dividers are 1->65536

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.n2_available, "n2")
        self._n2 = value

    @property
    def r2(self) -> Union[int, List[int]]:
        """VCXO input dividers.

        Valid dividers are 1->4096

        Returns:
            int: Current allowable dividers
        """
        return self._r2

    @r2.setter
    def r2(self, value: Union[int, List[int]]) -> None:
        """VCXO input dividers.

        Valid dividers are 1->4096

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

        if solution:
            self.solution = solution

        out_dividers = [self._get_val(x) for x in self.config["out_dividers"]]

        clk: float = (
            self.vcxo  # type: ignore # noqa: B950
            * self._get_val(self.config["n2"])  # type: ignore # noqa: B950
            / self._get_val(self.config["r2"])  # type: ignore # noqa: B950
        )

        config: Dict = {
            "r2": self._get_val(self.config["r2"]),
            "n2": self._get_val(self.config["n2"]),
            "VCO": clk,
            "vcxo": self.vcxo,
            "out_dividers": out_dividers,
            "output_clocks": [],
        }

        output_cfg = {}
        for i, div in enumerate(out_dividers):
            rate = clk / div  # type: ignore # noqa: B950
            output_cfg[self._clk_names[i]] = {"rate": rate, "divider": div}

        config["output_clocks"] = output_cfg

        self._saved_solution = config

        return config

    def _setup_solver_constraints(self, vcxo: int) -> None:
        """Apply constraints to solver model.

        Args:
            vcxo (int): VCXO frequency in hertz
        """
        self.vcxo = vcxo
        self.config = {
            "r2": self._convert_input(self._r2, "r2"),
            "n2": self._convert_input(self._n2, "n2"),
        }
        # self.config = {"r2": self.model.Var(integer=True, lb=1, ub=4095, value=1)}
        # self.config["n2"] = self.model.Var(
        #     integer=True, lb=8, ub=4095
        # )  # FIXME: CHECK UB

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
            self.model.minimize(self.config["r2"])
            # self.model.Obj(self.config["r2"])

    def _setup(self, vcxo: int) -> None:
        # Setup clock chip internal constraints

        # FIXME: ADD SPLIT m1 configuration support

        # Setup clock chip internal constraints
        self._setup_solver_constraints(vcxo)

        # Add requested clocks to output constraints
        self.config["out_dividers"] = []
        self._clk_names = []  # Reset

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
            __d = self._d if isinstance(self._d, list) else [self._d]

            if __d.sort() != self.d_available.sort():
                raise Exception("For solver gekko d is not configurable for LTC6952")
            # Since d is so disjoint it is very annoying to solve.
            mp = self.model.Var(integer=True, lb=1, ub=32)
            nx = self.model.Var(integer=True, lb=0, ub=7)
            od = self.model.Intermediate(mp * pow(2, nx))
        elif self.solver == "CPLEX":
            od = self._convert_input(self._d, "d_" + str(clk_name))
        else:
            raise Exception("Unknown solver {}".format(self.solver))

        self.config["out_dividers"].append(od)
        self._clk_names.append(clk_name)
        return self.vcxo / self.config["r2"] * self.config["n2"] / od

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
            if self.solver == "gekko":
                __d = self._d if isinstance(self._d, list) else [self._d]
                if __d.sort() != self.d_available.sort():
                    raise Exception(
                        "For solver gekko d is not configurable for LTC6952"
                    )

                mp = self.model.Var(integer=True, lb=1, ub=32)
                nx = self.model.Var(integer=True, lb=0, ub=7)
                od = self.model.Intermediate(mp * pow(2, nx))

            elif self.solver == "CPLEX":
                od = self._convert_input(self._d, "d_" + str(out_freq))

            self._add_equation(
                [self.vcxo / self.config["r2"] * self.config["n2"] / od == out_freq]
            )
            self.config["out_dividers"].append(od)

            # Objectives
            # self.model.Obj(-1*eo) # Favor even dividers
