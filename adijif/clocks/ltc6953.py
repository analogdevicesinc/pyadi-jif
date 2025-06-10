"""LTC6953 clock chip model."""

from typing import Dict, List, Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.clocks.clock import clock
from adijif.solvers import CpoExpr, GK_Intermediate


class ltc6953(clock):
    """LTC6953 clock chip model.

    This model currently supports all divider configurations
    """

    name = "LTC6953"

    input_ref = 1000000000

    # Ranges
    m_divider_min = 1
    m_divider_max = 1023
    m_available = [
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

    """ Output dividers """

    # Defaults
    _m: Union[int, List[int]] = [
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

    # Limits
    """ Internal limits """
    input_freq_max = 4.5e9

    # State management
    _clk_names: List[str] = []

    @property
    def m(self) -> Union[int, List[int]]:
        """Output dividers.

        Valid dividers are 1,2,3,4,5,6..32->(even)->4096

        Returns:
            int: Current allowable dividers
        """
        return self._d

    @m.setter
    def m(self, value: Union[int, List[int]]) -> None:
        """Output dividers.

        Valid dividers are 1,2,3,4,5,6..32->(even)->4096

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.m_available, "d")
        self._d = value

    def find_dividers(self) -> Dict:
        """Find the best dividers for the current configuration.

        NOT IMPLEMENTED YET

        Raises:
            NotImplementedError: Not implemented yet
        """
        raise NotImplementedError("find_dividers not implemented")

    def list_available_references(self) -> List[int]:
        """List the available reference frequencies.

        NOT IMPLEMENTED YET

        Raises:
            NotImplementedError: Not implemented yet
        """
        raise NotImplementedError("list_available_references not implemented")

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
            "out_dividers": out_dividers,
            "output_clocks": [],
        }

        config["input_ref"] = self._get_val(
            self.input_ref
        )  # pytype: disable=attribute-error

        output_cfg = {}
        for i, div in enumerate(out_dividers):
            rate = config["input_ref"] / div  # type: ignore # noqa: B950
            output_cfg[self._clk_names[i]] = {"rate": rate, "divider": div}

        config["output_clocks"] = output_cfg

        self._saved_solution = config

        return config

    def _setup_solver_constraints(self, input_ref: int) -> None:
        """Apply constraints to solver model.

        Args:
            input_ref (int): Input reference frequency in hertz
        """
        self.config = {}
        if not isinstance(input_ref, (int, float)):
            self.config["input_ref_set"] = input_ref(self.model)  # type: ignore
            input_ref = self.config["input_ref_set"]["range"]
        self.input_ref = input_ref

        self._add_equation(
            [
                input_ref <= self.input_freq_max,
            ]
        )

    def _setup(self, input_ref: int) -> None:
        if isinstance(input_ref, (float, int)):
            assert self.input_freq_max >= input_ref >= 0, "Input frequency out of range"

        # Setup clock chip internal constraints
        self._setup_solver_constraints(input_ref)

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
            __m = self._m if isinstance(self._m, list) else [self._m]
            if __m.sort() != self.m_available.sort():
                raise Exception("For solver gekko d is not configurable for LTC6952")
            mp = self.model.Var(integer=True, lb=1, ub=32)
            nx = self.model.Var(integer=True, lb=0, ub=7)
            od = self.model.Intermediate(mp * pow(2, nx))
        elif self.solver == "CPLEX":
            od = self._convert_input(self._m, f"m_{clk_name}")
        else:
            raise Exception("Unknown solver {}".format(self.solver))
        self.config["out_dividers"].append(od)
        return self.input_ref / od

    def set_requested_clocks(
        self, input_ref: int, out_freqs: List, clk_names: List[str]
    ) -> None:
        """Define necessary clocks to be generated in model.

        Args:
            input_ref (int): Input reference frequency in hertz
            out_freqs (List): list of required clocks to be output
            clk_names (List[str]):  list of strings of clock names

        Raises:
            Exception: If len(out_freqs) != len(clk_names)
        """
        if len(clk_names) != len(out_freqs):
            raise Exception("clk_names is not the same size as out_freqs")
        self._clk_names = clk_names

        # Setup clock chip internal constraints
        self._setup(input_ref)

        # Add requested clocks to output constraints
        for out_freq in out_freqs:
            if self.solver == "gekko":
                __m = self._d if isinstance(self.__m, list) else [self.__m]
                if __m.sort() != self.m_available.sort():
                    raise Exception(
                        "For solver gekko m is not configurable for LTC6953"
                    )

                mp = self.model.Var(integer=True, lb=1, ub=32)
                nx = self.model.Var(integer=True, lb=0, ub=7)
                od = self.model.Intermediate(mp * pow(2, nx))

            elif self.solver == "CPLEX":
                od = self._convert_input(self._m, "m_" + str(out_freq))

            self._add_equation([self.input_ref / od == out_freq])
            self.config["out_dividers"].append(od)
