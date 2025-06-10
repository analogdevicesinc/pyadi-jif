"""AD9528 clock chip model."""

from typing import Dict, List, Union

from adijif.clocks.ad9528_bf import ad9528_bf
from adijif.solvers import CpoExpr, CpoSolveResult, GK_Intermediate


class ad9528(ad9528_bf):
    """AD9528 clock chip model.

    This model currently supports VCXO+PLL2 configurations
    """

    name = "AD9528"

    # Ranges
    """ VCO divider """
    m1_available = [3, 4, 5]
    """ Output dividers """
    d_available = [*range(1, 1024)]
    """ sysref dividers """
    k_available = [*range(0, 65536)]
    """ VCXO multiplier """
    n2_available = [*range(1, 256)]
    """ VCO calibration dividers """
    a_available = [0, 1, 2, 3]
    b_availble = [*range(3, 64)]
    # N = (PxB) + A, P=4, A==[0,1,2,3], B=[3..63]
    # See table 46 of DS for limits
    """ VCXO dividers """
    r1_available = [*range(1, 32)]

    # State management
    _clk_names: List[str] = []

    # Defaults
    _m1: Union[List[int], int] = [3, 4, 5]
    _d: Union[List[int], int] = [*range(1, 1024)]
    _k: Union[List[int], int] = k_available
    _n2: Union[List[int], int] = n2_available
    _r1: Union[List[int], int] = [*range(1, 32)]
    _a: Union[List[int], int] = [*range(0, 4)]
    _b: Union[List[int], int] = [*range(3, 64)]

    # Limits
    vco_min = 3450e6
    vco_max = 4025e6
    pfd_max = 275e6

    minimize_feedback_dividers = True

    use_vcxo_double = False
    vcxo = 125e6

    # sysref parameters
    sysref_external = False
    _sysref = None

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
    def k(self) -> Union[int, List[int]]:
        """Sysref dividers.

        Valid dividers are 0->65535

        Returns:
            int: Current allowable dividers
        """
        return self._k

    @k.setter
    def k(self, value: Union[int, List[int]]) -> None:
        """Sysref dividers.

        Valid dividers are 0->65535

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.d_available, "k")
        self._k = value

    @property
    def n2(self) -> Union[int, List[int]]:
        """n2: VCO feedback divider.

        Valid dividers are 1->255

        Returns:
            int: Current allowable dividers
        """
        return self._n2

    @n2.setter
    def n2(self, value: Union[int, List[int]]) -> None:
        """VCO feedback divider.

        Valid dividers are 1->255

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.n2_available, "n2")
        self._n2 = value

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

    @property
    def a(self) -> Union[int, List[int]]:
        """VCO calibration divider 1.

        Valid dividers are 0->3

        Returns:
            int: Current allowable dividers
        """
        return self._a

    @a.setter
    def a(self, value: Union[int, List[int]]) -> None:
        """VCO calibration divider 1.

        Valid dividers are 0->3

        Args:
            value (int, list[int]): Allowable values for counter

        """
        self._check_in_range(value, self.a_available, "a")
        self._a = value

    @property
    def b(self) -> Union[int, List[int]]:
        """VCO calibration divider 2.

        Valid dividers are 3->63

        Returns:
            int: Current allowable dividers
        """
        return self._b

    @b.setter
    def b(self, value: Union[int, List[int]]) -> None:
        """VCO calibration divider 2.

        Valid dividers are 3->63

        Args:
            value (int, list[int]): Allowable values for counter

        """
        self._check_in_range(value, self.b_available, "b")
        self._b = value

    @property
    def vco(self) -> float:
        """VCO Frequency in Hz.

        Returns:
            float: computed VCO frequency
        """
        r1 = self._get_val(self.config["r1"])
        m1 = self._get_val(self.config["m1"])
        n2 = self._get_val(self.config["n2"])

        return self.vcxo / r1 * m1 * n2

    @property
    def sysref(self) -> int:
        """SYSREF Frequency in Hz.

        Returns:
            int: computed sysref frequency
        """
        r1 = self._get_val(self.config["r1"])
        k = self._get_val(self.config["k"])

        if self.sysref_external:
            sysref_src = self.vcxo
        else:
            sysref_src = self.vcxo / r1

        return sysref_src / (2 * k)

    @sysref.setter
    def sysref(self, value: Union[int, float]) -> None:
        """Set sysref frequency.

        Args:
            value (int, float): Frequency
        """
        self._sysref = int(value)

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

        # out_dividers = [solution.get_value(x) for x in self.config["out_dividers"]]
        out_dividers = [self._get_val(x) for x in self.config["out_dividers"]]

        config: Dict = {
            "vcxo": self.vcxo / 2 if self.use_vcxo_double else self.vcxo,
            "vco": self.vco,
            "r1": self._get_val(self.config["r1"]),
            "n2": self._get_val(self.config["n2"]),
            "m1": self._get_val(self.config["m1"]),
            "a": self._get_val(self.config["a"]),
            "b": self._get_val(self.config["b"]),
            "out_dividers": out_dividers,
            "output_clocks": [],
        }

        if self._sysref:
            config["k"] = self._get_val(self.config["k"])
            config["sysref"] = self.sysref

        clk = self.vcxo * config["n2"] / config["r1"]

        output_cfg = {}
        for i, div in enumerate(out_dividers):
            rate = clk / div
            output_cfg[self._clk_names[i]] = {
                "rate": rate,
                "divider": div,
            }

        config["output_clocks"] = output_cfg

        self._saved_solution = config

        return config

    def _setup_solver_constraints(self, vcxo: int) -> None:
        """Apply constraints to solver model.

        Args:
            vcxo (int): VCXO frequency in hertz

        Raises:
            Exception: Unknown solver
        """
        if not isinstance(vcxo, (float, int)):
            vcxo = vcxo(self.model)
            self.vcxo = vcxo["range"]
        else:
            self.vcxo = vcxo

        self.config = {
            "r1": self._convert_input(self._r1, "r1"),
            "m1": self._convert_input(self._m1, "m1"),
            "k": self._convert_input(self._k, "k"),
            "n2": self._convert_input(self._n2, "n2"),
            "a": self._convert_input(self._a, "a"),
            "b": self._convert_input(self._b, "b"),
        }
        # self.config = {"r1": self.model.Var(integer=True, lb=1, ub=31, value=1)}
        # self.config["m1"] = self.model.Var(integer=True, lb=3, ub=5, value=3)
        # self.config["n2"] = self.model.Var(integer=True, lb=12, ub=255, value=12)

        # PLL2 equations
        self._add_equation(
            [
                self.vcxo / self.config["r1"] <= self.pfd_max,
                self.vcxo / self.config["r1"] * self.config["m1"] * self.config["n2"]
                <= self.vco_max,
                self.vcxo / self.config["r1"] * self.config["m1"] * self.config["n2"]
                >= self.vco_min,
                4 * self.config["b"] + self.config["a"] >= 16,
                4 * self.config["b"] + self.config["a"]
                == self.config["m1"] * self.config["n2"],
            ]
        )
        # Objectives
        if self.minimize_feedback_dividers:
            if self.solver == "CPLEX":
                self._add_objective(self.config["n2"])
                # self.model.minimize(self.config["n2"])
            elif self.solver == "gekko":
                self.model.Obj(self.config["n2"])
            else:
                raise Exception("Unknown solver {}".format(self.solver))
        # self.model.Obj(self.config["n2"] * self.config["m1"])

    def _setup(self, vcxo: int) -> None:
        # Setup clock chip internal constraints

        # FIXME: ADD SPLIT m1 configuration support

        # Setup clock chip internal constraints
        if self.use_vcxo_double:
            vcxo *= 2
        self._setup_solver_constraints(vcxo)

        # Add requested clocks to output constraints
        self.config["out_dividers"] = []
        self._clk_names = []  # Reset clock names

    def _get_clock_constraint(
        self, clk_name: str
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
        return self.vcxo / self.config["r1"] * self.config["n2"] / od

    def set_requested_clocks(
        self,
        vcxo: int,
        out_freqs: List,
        clk_names: List[str],
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

        if self._sysref:
            if self.sysref_external:
                sysref_src = self.vcxo
            else:
                sysref_src = self.vcxo / self.config["r1"]

            self._add_equation([sysref_src / (2 * self.config["k"]) == self._sysref])

        # Add requested clocks to output constraints
        for out_freq, name in zip(out_freqs, clk_names):  # noqa: B905
            # od = self.model.Var(integer=True, lb=1, ub=256, value=1)
            od = self._convert_input(self._d, f"d_{name}_{out_freq}")
            # od = self.model.sos1([n*n for n in range(1,9)])
            self._add_equation(
                [self.vcxo / self.config["r1"] * self.config["n2"] / od == out_freq]
            )
            self.config["out_dividers"].append(od)
