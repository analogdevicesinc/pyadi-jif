"""HMC7044 clock chip model."""

from typing import Dict, List, Union

from adijif.clocks.hmc7044_bf import hmc7044_bf

from adijif.solvers import CpoExpr, CpoModel  # type: ignore # isort: skip  # noqa: I202
from adijif.solvers import CpoSolveResult  # type: ignore # isort: skip  # noqa: I202
from adijif.solvers import GEKKO  # type: ignore # isort: skip  # noqa: I202
from adijif.solvers import GK_Intermediate  # type: ignore # isort: skip  # noqa: I202

from adijif.draw import Layout, Node  # type: ignore # isort: skip  # noqa: I202


class hmc7044(hmc7044_bf):
    """HMC7044 clock chip model.

    This model currently supports VCXO+PLL2 configurations
    """

    name = "HMC7044"

    # Ranges
    # r2_divider_min = 1
    # r2_divider_max = 4095
    r2_available = [*range(1, 4095 + 1)]

    """ Output dividers """
    d_available = [1, 3, 5, *range(2, 4095, 2)]
    # When pulse generation is required (like for sysref) divder range
    # is limited
    d_syspulse_available = [*range(32, 4095, 2)]

    # Defaults
    _d: Union[int, List[int]] = [1, 3, 5, *range(2, 4095, 2)]
    _r2: Union[int, List[int]] = [*range(1, 4095 + 1)]

    # Limits
    """ Internal limits """
    vco_min = 2400e6
    vco_max = 3200e6
    pfd_max = 250e6
    vcxo_min = 10e6
    vcxo_max = 500e6

    use_vcxo_double = True
    vxco_doubler_available = [1, 2]
    _vcxo_doubler = [1, 2]

    minimize_feedback_dividers = True

    # State management
    _clk_names: List[str] = []

    def __init__(
        self, model: Union[GEKKO, CpoModel] = None, solver: str = "CPLEX"
    ) -> None:
        """Initialize HMC7044 clock chip model.

        Args:
            model (Model): Model to add constraints to
            solver (str): Solver to use. Should be one of "CPLEX" or "gekko"

        Raises:
            Exception: Invalid solver
        """
        super(hmc7044, self).__init__(model, solver)
        if solver == "gekko":
            self.n2_available = [*range(8, 65535 + 1)]
            self._n2 = [*range(8, 65535 + 1)]
        elif solver == "CPLEX":
            self.n2_available = [*range(8, 65535 + 1)]
            self._n2 = [*range(8, 65535 + 1)]
        else:
            raise Exception("Unknown solver {}".format(solver))

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

        Valid dividers are 8->65536

        Returns:
            int: Current allowable dividers
        """
        return self._n2

    @n2.setter
    def n2(self, value: Union[int, List[int]]) -> None:
        """VCO feedback divider.

        Valid dividers are 8->65536

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

    @property
    def vxco_doubler(self) -> Union[int, List[int]]:
        """VCXO doubler.

        Valid dividers are 1,2

        Returns:
            int: Current doubler value
        """
        return self._vcxo_doubler

    @vxco_doubler.setter
    def vxco_doubler(self, value: Union[int, List[int]]) -> None:
        """VCXO doubler.

        Valid dividers are 1,2

        Args:
            value (int, list[int]): Allowable values for divider

        """
        self._check_in_range(value, self.vxco_doubler_available, "vxco_doubler")
        self._vcxo_doubler = value

    def _init_diagram(self) -> None:
        """Initialize diagram for HMC7044 alone."""
        self.ic_diagram_node = None
        self._diagram_output_dividers = []

        # lo = Layout("HMC7044 Example")

        self.ic_diagram_node = Node("HMC7044")
        # lo.add_node(root)

        # External
        # ref_in = Node("REF_IN", ntype="input")
        # lo.add_node(ref_in)

        vcxo_doubler = Node("VCXO Doubler", ntype="shell")
        self.ic_diagram_node.add_child(vcxo_doubler)

        # Inside the IC
        r2_div = Node("R2", ntype="divider")
        # r2_div.value = "2"
        self.ic_diagram_node.add_child(r2_div)
        pfd = Node("PFD", ntype="phase-frequency-detector")
        self.ic_diagram_node.add_child(pfd)
        lf = Node("LF", ntype="loop-filter")
        self.ic_diagram_node.add_child(lf)
        vco = Node("VCO", ntype="voltage-controlled-oscillator")
        vco.shape = "circle"
        self.ic_diagram_node.add_child(vco)
        n2 = Node("N2", ntype="divider")
        self.ic_diagram_node.add_child(n2)

        out_dividers = Node("Output Dividers", ntype="shell")
        # ds = 4
        # out_divs = []
        # for i in range(ds):
        #     div = Node(f"D{i+1}", ntype="divider")
        #     out_dividers.add_child(div)
        #     out_divs.append(div)

        self.ic_diagram_node.add_child(out_dividers)

        # Connections inside the IC
        # lo.add_connection({"from": ref_in, "to": r2_div, 'rate': 125000000})
        self.ic_diagram_node.add_connection({"from": vcxo_doubler, "to": r2_div})
        self.ic_diagram_node.add_connection(
            {"from": r2_div, "to": pfd, "rate": 125000000 / 2}
        )
        self.ic_diagram_node.add_connection({"from": pfd, "to": lf})
        self.ic_diagram_node.add_connection({"from": lf, "to": vco})
        self.ic_diagram_node.add_connection({"from": vco, "to": n2})
        self.ic_diagram_node.add_connection({"from": n2, "to": pfd})

        self.ic_diagram_node.add_connection(
            {"from": vco, "to": out_dividers, "rate": 4000000000}
        )
        # for div in out_divs:
        #     self.ic_diagram_node.add_connection({"from": out_dividers, "to": div})
        #     # root.add_connection({"from": vco, "to": div})

    def _update_diagram(self, config: Dict) -> None:
        """Update diagram with configuration.

        Args:
            config (Dict): Configuration dictionary

        Raises:
            Exception: If key is not D followed by a number
        """
        # Add output dividers
        keys = config.keys()
        output_dividers = self.ic_diagram_node.get_child("Output Dividers")
        for key in keys:
            if key.startswith("D"):
                div = Node(key, ntype="divider")
                output_dividers.add_child(div)
                self.ic_diagram_node.add_connection(
                    {"from": output_dividers, "to": div}
                )
            else:
                raise Exception(
                    f"Unknown key {key}. Must be of for DX where X is a number"
                )

    def draw(self, lo: Layout = None) -> str:
        """Draw diagram in d2 language for IC alone with reference clock.

        Args:
            lo: Layout for drawing

        Returns:
            str: Diagram in d2 language

        Raises:
            Exception: If no solution is saved
        """
        if not self._saved_solution:
            raise Exception("No solution to draw. Must call solve first.")

        system_draw = lo is not None
        if not system_draw:
            lo = Layout("HMC7044 Example")
        else:
            # Verify lo is a Layout object
            assert isinstance(lo, Layout), "lo must be a Layout object"
        lo.add_node(self.ic_diagram_node)

        ref_in = Node("REF_IN", ntype="input")
        lo.add_node(ref_in)
        vcxo_double = self.ic_diagram_node.get_child("VCXO Doubler")
        lo.add_connection(
            {"from": ref_in, "to": vcxo_double, "rate": self._saved_solution["vcxo"]}
        )

        # Update Node values
        node = self.ic_diagram_node.get_child("VCXO Doubler")
        node.value = str(self._saved_solution["vcxo_doubler"])
        node = self.ic_diagram_node.get_child("R2")
        node.value = str(self._saved_solution["r2"])
        node = self.ic_diagram_node.get_child("N2")
        node.value = str(self._saved_solution["n2"])

        # Update VCXO Doubler to R2
        # con = self.ic_diagram_node.get_connection("VCXO Doubler", "R2")
        rate = self._saved_solution["vcxo_doubler"] * self._saved_solution["vcxo"]
        self.ic_diagram_node.update_connection("VCXO Doubler", "R2", rate)

        # Update R2 to PFD
        # con = self.ic_diagram_node.get_connection("R2", "PFD")
        rate = (
            self._saved_solution["vcxo"]
            * self._saved_solution["vcxo_doubler"]
            / self._saved_solution["r2"]
        )
        self.ic_diagram_node.update_connection("R2", "PFD", rate)

        # Update VCO
        # con = self.ic_diagram_node.get_connection("VCO", "Output Dividers")
        self.ic_diagram_node.update_connection(
            "VCO", "Output Dividers", self._saved_solution["vco"]
        )

        # Update diagram with dividers and rates
        d = 0
        output_dividers = self.ic_diagram_node.get_child("Output Dividers")

        for key, val in self._saved_solution["output_clocks"].items():
            clk_node = Node(key, ntype="divider")
            div_value = val["divider"]
            div = output_dividers.get_child(f"D{d}")
            div.value = str(div_value)
            d += 1
            lo.add_node(clk_node)
            lo.add_connection({"from": div, "to": clk_node, "rate": val["rate"]})

        if system_draw:
            return lo.draw()

        return lo.draw()

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
            "r2": self._get_val(self.config["r2"]),
            "n2": self._get_val(self.config["n2"]),
            "out_dividers": out_dividers,
            "output_clocks": [],
        }

        if self.vcxo_i:
            vcxo = self._get_val(self.vcxo_i["range"])
            self.vcxo = vcxo

        clk = self.vcxo / config["r2"] * config["n2"]

        output_cfg = {}
        vd = self._get_val(self.config["vcxo_doubler"])
        for i, div in enumerate(out_dividers):
            rate = vd * clk / div
            output_cfg[self._clk_names[i]] = {"rate": rate, "divider": div}

        config["output_clocks"] = output_cfg
        config["vco"] = clk * vd
        config["vcxo"] = self.vcxo
        config["vcxo_doubler"] = vd

        self._saved_solution = config

        return config

    def _setup_solver_constraints(self, vcxo: int) -> None:
        """Apply constraints to solver model.

        Args:
            vcxo (int): VCXO frequency in hertz

        Raises:
            Exception: Invalid solver
        """
        self.vcxo = vcxo

        if self.solver == "gekko":
            self.config = {"r2": self.model.Var(integer=True, lb=1, ub=4095, value=1)}
            self.config["n2"] = self.model.Var(integer=True, lb=8, ub=4095)
            if isinstance(vcxo, (int, float)):
                vcxo_var = self.model.Const(int(vcxo))
            else:
                vcxo_var = vcxo
            self.config["vcxo_doubler"] = self.model.sos1([1, 2])
            self.config["vcxod"] = self.model.Intermediate(
                self.config["vcxo_doubler"] * vcxo_var
            )
        elif self.solver == "CPLEX":
            self.config = {
                "r2": self._convert_input(self._r2, "r2"),
                "n2": self._convert_input(self._n2, "n2"),
            }
            self.config["vcxo_doubler"] = self._convert_input(
                self._vcxo_doubler, "vcxo_doubler"
            )
            self.config["vcxod"] = self._add_intermediate(
                self.config["vcxo_doubler"] * vcxo
            )
        else:
            raise Exception("Unknown solver {}".format(self.solver))

        # PLL2 equations
        self._add_equation(
            [
                self.config["vcxod"] <= self.pfd_max * self.config["r2"],
                self.config["vcxod"] * self.config["n2"]
                <= self.vco_max * self.config["r2"],
                self.config["vcxod"] * self.config["n2"]
                >= self.vco_min * self.config["r2"],
            ]
        )

        # Objectives
        if self.minimize_feedback_dividers:
            if self.solver == "CPLEX":
                self._add_objective(self.config["r2"])
                # self.model.minimize(self.config["r2"])
            elif self.solver == "gekko":
                self.model.Obj(self.config["r2"])
            else:
                raise Exception("Unknown solver {}".format(self.solver))

    def _setup(self, vcxo: int) -> None:
        # Setup clock chip internal constraints

        # FIXME: ADD SPLIT m1 configuration support

        # Convert VCXO into intermediate in case we have range type
        if type(vcxo) not in [int, float]:
            self.vcxo_i = vcxo(self.model)
            vcxo = self.vcxo_i["range"]
        else:
            self.vcxo_i = False

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
                raise Exception("For solver gekko d is not configurable for HMC7044")

            even = self.model.Var(integer=True, lb=3, ub=2047)
            odd = self.model.Intermediate(even * 2)
            od = self.model.sos1([1, 2, 3, 4, 5, odd])

        elif self.solver == "CPLEX":
            od = self._convert_input(self._d, "d_" + str(clk_name))
        else:
            raise Exception("Unknown solver {}".format(self.solver))

        # Update diagram to include new divider
        d_n = len(self.config["out_dividers"])
        self._update_diagram({f"D{d_n}": od})

        self._clk_names.append(clk_name)

        self.config["out_dividers"].append(od)
        return self.config["vcxod"] / self.config["r2"] * self.config["n2"] / od

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
        # if type(self.vcxo) not in [int,float]:
        #     vcxo = self.vcxo['range']

        self._saved_solution = None

        # Add requested clocks to output constraints
        for d_n, out_freq in enumerate(out_freqs):

            if self.solver == "gekko":
                __d = self._d if isinstance(self._d, list) else [self._d]
                if __d.sort() != self.d_available.sort():
                    raise Exception(
                        "For solver gekko d is not configurable for HMC7044"
                    )

                # even = self.model.Var(integer=True, lb=3, ub=2047)
                # odd = self.model.Intermediate(even * 2)
                # od = self.model.sos1([1, 2, 3, 4, 5, odd])

                # Since d is so disjoint it is very annoying to solve.
                even = self.model.Var(integer=True, lb=1, ub=4094 // 2)

                # odd = self.model.sos1([1, 3, 5])
                odd_i = self.model.Var(integer=True, lb=0, ub=2)
                odd = self.model.Intermediate(1 + odd_i * 2)

                eo = self.model.Var(integer=True, lb=0, ub=1)
                od = self.model.Intermediate(eo * odd + (1 - eo) * even * 2)

            elif self.solver == "CPLEX":
                od = self._convert_input(self._d, f"d_{out_freq}_{d_n}")

            self._add_equation(
                [
                    self.config["vcxod"] * self.config["n2"]
                    == out_freq * self.config["r2"] * od
                ]
            )
            self.config["out_dividers"].append(od)

            # Update diagram to include new divider
            self._update_diagram({f"D{d_n}": od})

            # Objectives
            # self.model.Obj(-1*eo) # Favor even dividers
