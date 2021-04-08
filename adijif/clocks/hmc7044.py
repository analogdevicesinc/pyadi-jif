"""HMC7044 clock chip model."""
from typing import Dict, List, Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.clocks.hmc7044_bf import hmc7044_bf


class hmc7044(hmc7044_bf):
    """AD9528 clock chip model.

    This model currently supports VCXO+PLL2 configurations
    """

    # Ranges
    # r2_divider_min = 1
    # r2_divider_max = 4095
    r2_available = [*range(1, 4095 + 1)]
    # n2_divider_min = 8
    # n2_divider_max = 65535
    n2_available = [*range(1, 65535 + 1)]

    """ Output dividers """
    d_available = [1, 3, 5, *range(2, 4095, 2)]
    # When pulse generation is required (like for sysref) divder range
    # is limited
    d_syspulse_available = [*range(32, 4095, 2)]

    # Defaults
    _d: Union[int, List[int]] = [1, 3, 5, *range(2, 4095, 2)]
    _n2: Union[int, List[int]] = [*range(1, 65535 + 1)]
    _r2: Union[int, List[int]] = [*range(1, 4095 + 1)]

    # Limits
    """ Internal limits """
    vco_min = 2150e6
    vco_max = 3550e6
    pfd_max = 250e6
    vcxo_min = 10e6
    vcxo_max = 500e6

    use_vcxo_double = True

    # State management
    _clk_names: List[str] = []

    @property
    def d(self) -> Union[int, List[int]]:
        """Output dividers.

        Valid dividers are 1,2,3,4,5,6->(even)->4094

        Returns:
            int: Current allowable dividers
        """
        return self._d

    @d.setter
    def d(self, value: Union[int, List[int]]) -> None:
        """Output dividers.

        Valid dividers are 1,2,3,4,5,6->(even)->4094

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

        config: Dict = {
            "r2": self._get_val(self.config["r2"]),
            "n2": self._get_val(self.config["n2"]),
            "out_dividers": [self._get_val(x) for x in self.config["out_dividers"]],
            "output_clocks": [],
        }

        clk = self.vcxo / config["r2"] * config["n2"]

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
        # self.model.Obj(self.config["n2"])
        # self.model.Obj(-1 * vcxo / self.config["r2"])

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
        assert self.vcxo_min <= vcxo <= self.vcxo_max, "VCXO out of range"
        self._setup_solver_constraints(vcxo)

        # Add requested clocks to output constraints
        self.config["out_dividers"] = []
        for out_freq in out_freqs:

            if self.solver == "gekko":
                even = self.model.Var(integer=True, lb=1, ub=4094 / 2)

                # odd = self.model.sos1([1, 3, 5])
                odd_i = self.model.Var(integer=True, lb=0, ub=2)
                odd = self.model.Intermediate(1 + odd_i * 2)

                eo = self.model.Var(integer=True, lb=0, ub=1)
                od = self.model.Intermediate(eo * odd + (1 - eo) * even * 2)
            elif self.solver == "CPLEX":
                od = self._convert_input(self._d, "d_" + str(out_freq))

            self._add_equation(
                [vcxo / self.config["r2"] * self.config["n2"] / od == out_freq]
            )
            self.config["out_dividers"].append(od)

            # Objectives
            # self.model.Obj(-1*eo) # Favor even dividers
