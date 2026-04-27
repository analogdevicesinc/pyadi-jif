"""ADF4030 10-Channel Precision Synchronizer."""

from typing import Dict, List, Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.clocks.clock import clock as clockc
from adijif.plls.pll import pll
from adijif.solvers import CpoExpr, GK_Intermediate

from adijif.draw import Layout, Node


class adf4030_drawer(object):
    """ADF4030 diagram drawer."""

    def _init_diagram(self) -> None:
        """Initialize diagram with PLL block."""

        self._diagram_output_dividers = []

        self.ic_diagram_node = Node("ADF4030")

        rdiv = Node("R", ntype="divider")
        self.ic_diagram_node.add_child(rdiv)

        pfd = Node("PFD", ntype="phase-frequency-detector")
        self.ic_diagram_node.add_child(pfd)

        charge_pump = Node("CP", ntype="charge-pump")
        self.ic_diagram_node.add_child(charge_pump)

        loop_filter = Node("LF", ntype="loop-filter")
        self.ic_diagram_node.add_child(loop_filter)

        vco = Node("VCO", ntype="vco")
        self.ic_diagram_node.add_child(vco)

        ndiv = Node("N", ntype="divider")
        self.ic_diagram_node.add_child(ndiv)

        output_dividers = Node("Output Dividers", ntype="shell")
        self.ic_diagram_node.add_child(output_dividers)

        # Connections
        self.ic_diagram_node.add_connection({
            "from": rdiv,
            "to": pfd,
        })
        self.ic_diagram_node.add_connection({
            "from": pfd,
            "to": charge_pump,
        })
        self.ic_diagram_node.add_connection({
            "from": charge_pump,
            "to": loop_filter,
        })
        self.ic_diagram_node.add_connection({
            "from": loop_filter,
            "to": vco,
        })
        self.ic_diagram_node.add_connection({
            "from": vco,
            "to": ndiv,
        })
        self.ic_diagram_node.add_connection({
            "from": ndiv,
            "to": pfd,
        })
        self.ic_diagram_node.add_connection({
            "from": vco,
            "to": output_dividers,
        })

    def _update_diagram(self, config: Dict) -> None:
        """Update diagram with new dividers."""

        keys = config.keys()
        output_dividers = self.ic_diagram_node.get_child("Output Dividers")
        for key in keys:
            if "o_div" in key and key not in self._diagram_output_dividers:
                od_node = Node(key, ntype="divider")
                output_dividers.add_child(od_node)
                self.ic_diagram_node.add_connection({
                    "from": output_dividers,
                    "to": od_node,
                })
            else:
                raise Exception("Unexpected config key: {}".format(key))
            
    def draw(self, lo: Layout = None) -> Union[str, Layout]:
        """Draw diagram with configuration.

        Args:
            lo (Layout): Diagram layout object

        Returns:
            Layout: Diagram layout object
        """
        if not self._saved_solution:
            raise Exception("No solution to draw. Must call solve first")
        
        system_draw = lo is not None
        if not system_draw:
            lo = Layout("ADF4030 Diagram")
        else:
            assert isinstance(lo, Layout), "Layout object must be provided for system drawing"
        lo.add_node(self.ic_diagram_node)

        ref_in = Node("REF_IN", ntype="input")
        rdiv = self.ic_diagram_node.get_child("R")
        lo.add_connection({
            "from": ref_in,
            "to": rdiv,
            "rate": 100e6,  # TODO: Get actual rate
        })

        # Update node values
        node = self.ic_diagram_node.get_child("R")
        node.value = str(self._saved_solution["r"])
        node = self.ic_diagram_node.get_child("N")
        node.value = str(self._saved_solution["n"])
        # for clk in self._clk_names:
        #     od_node = self.ic_diagram_node.get_child(f"o_div_{clk}_adf4030")
        #     od_node.value = str(self._saved_solution[f"o_div_{clk}_adf4030"])
        for key, val in self._saved_solution["output_clocks"].items():
            div = Node(key, ntype="divider")
            div.value = str(val["divider"])
            lo.add_node(div)
            lo.add_connection({
                "from": self.ic_diagram_node.get_child("Output Dividers"),
                "to": div,
                "rate": self._saved_solution["vco"] / val["divider"],
            })

        if system_draw:
            return lo.draw()
        
        return lo.draw()


class adf4030(pll, adf4030_drawer):

    """ADF4030 PLL model.

    This model currently supports all divider configurations

    https://www.analog.com/media/en/technical-documentation/data-sheets/adf4030.pdf
    """

    name = "adf4030"

    input_freq_min = int(10e6)
    input_freq_max = int(250e6)

    pfd_freq_min = int(10e6)
    pfd_freq_max = int(20e6)

    vco_freq_min = int(2.5e9 * 0.95)
    vco_freq_max = int(2.5e9 * 1.05)

    bsync_freq_min = int(1e6)
    bsync_freq_max = int(200e6)

    _r = [*range(1, 31 + 1)]
    r_available = [*range(1, 31 + 1)]

    @property
    def r(self) -> Union[int, List[int]]:
        """Reference divider.

        Valid values are 1->31

        Returns:
            int: Current allowable setting
        """
        return self._r

    @r.setter
    def r(self, value: Union[int, List[int]]) -> None:
        """Reference divider.

        Valid values are 1->31

        Args:
            value (int, list[int]): Current allowable setting

        """
        self._check_in_range(value, self.r_available, "r")
        self._r = value

    _n = [*range(8, 255 + 1)]
    n_available = [*range(8, 255 + 1)]

    @property
    def n(self) -> Union[int, List[int]]:
        """Feedback divider.

        Valid values are 8->255

        Returns:
            int: Current allowable setting
        """
        return self._n

    @n.setter
    def n(self, value: Union[int, List[int]]) -> None:
        """Feedback divider.

        Valid values are 8->255

        Args:
            value (int, list[int]): Current allowable setting

        """
        self._check_in_range(value, self.n_available, "n")
        self._n = value

    _o = [*range(10, 4095 + 1)]
    o_available = [*range(10, 4095 + 1)]

    @property
    def o(self) -> Union[int, List[int]]:
        """Output divider.

        Valid values are 10->4095

        Returns:
            int: Current allowable setting
        """
        return self._o

    @o.setter
    def o(self, value: Union[int, List[int]]) -> None:
        """Output divider.

        Valid values are 10->4095

        Args:
            value (int, list[int]): Current allowable setting

        """
        self._check_in_range(value, self.o_available, "o")
        self._o = value

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
            raise Exception(
                "set_requested_clocks must be called before get_config"
            )

        if solution:
            self.solution = solution

        out_dividers = [self._get_val(x) for x in self.config["out_dividers"]]

        config: Dict = {
            "r": self._get_val(self.config["r"]),
            "n": self._get_val(self.config["n"]),
            "out_dividers": out_dividers,
        }

        vco = self.solution.get_kpis()["vco_adf4030"]
        config["vco"] = vco

        # Outputs
        output_config = {}
        for i, clk in enumerate(self._clk_names):
            o_val = out_dividers[i]
            output_config[clk] = {
                "rate": vco / o_val,
                "divider": o_val,
            }

        config["output_clocks"] = output_config

        self._saved_solution = config

        return config

    def _setup_solver_constraints(
        self, input_ref: Union[int, float, CpoExpr, GK_Intermediate]
    ) -> None:
        """Apply constraints to solver model.

        Args:
            input_ref (int, float, CpoExpr, GK_Intermediate): Input reference
                frequency in hertz. Can also be range or arb_source type.
        """
        self.config = {}

        # Handle range type (returns dict with "range" key)
        # arb_source and direct expressions are already supported
        expr_types = tuple(filter(None, [int, float, CpoExpr, GK_Intermediate]))
        if not isinstance(input_ref, expr_types):
            input_ref_result = input_ref(self.model)  # type: ignore
            if isinstance(input_ref_result, dict):
                # range type
                self.config["input_ref_set"] = input_ref_result
                input_ref = self.config["input_ref_set"]["range"]
            else:
                # arb_source type (returns expression directly)
                input_ref = input_ref_result
        self.input_ref = input_ref

        # PFD
        self.config["r"] = self._convert_input(self.r, name="r_adf4030")
        self.config["n"] = self._convert_input(self.n, name="n_adf4030")
        self.config["o"] = self._convert_input(self.o, name="o_adf4030")

        self.config["vco"] = self._add_intermediate(
            input_ref * self.config["n"] / self.config["r"]
        )
        self.model.add_kpi(
            input_ref * self.config["n"] / self.config["r"],
            "vco_adf4030",
        )

        self._add_equation(
            [
                input_ref <= self.input_freq_max,
                input_ref >= self.input_freq_min,
                self.config["vco"] <= self.vco_freq_max,
                self.config["vco"] >= self.vco_freq_min,
                input_ref <= self.pfd_freq_max * self.config["r"],
                input_ref >= self.pfd_freq_min * self.config["r"],
            ]
        )

    def _setup(self, input_ref: Union[int, clockc]) -> None:
        # For integer/float values, validate frequency range
        if isinstance(input_ref, (float, int)):
            assert self.input_freq_max >= input_ref >= self.input_freq_min, (
                "Input frequency out of range"
            )

        # Setup clock chip internal constraints (this converts input_ref to solver var
        # and adds constraints for range/arb_source types)
        self._setup_solver_constraints(input_ref)

        self._clk_names = []  # List of clock names to be generated
        self.config["out_dividers"] = []

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
        od = self._convert_input(self._o, f"o_div_{clk_name}_adf4030")

        # Update diagram to include new divider
        # d_n = len(self.config["out_dividers"])
        # self._update_diagram({f"o{d_n}": od})

        self._clk_names.append(clk_name)

        self.config["out_dividers"].append(od)
        return self.config["vco"] / od

    def _prepare_bsync_reference(self, clk: Union[clockc, int, float]) -> None:
        """Prepare BSYNC reference clock.

        This is used for synchronizing ADF4030 BSYNCs to a common reference,
        which acts as an input while the outputs are synchronized to it. This
        method is only used within a system when the ADF4030 is used as a SYSREF
        PLL.

        Args:
            clk (Union[clockc, int, float]): Clock object or frequency in hertz to be added as BSYNC reference
        """
        self._bsync_reference = clk

    def _setup_bsync_reference(
        self, bsync_ref: Union[int, float, CpoExpr, GK_Intermediate]
    ) -> None:
        """Setup BSYNC reference clock constraints.

        This is used for synchronizing ADF4030 BSYNCs to a common reference,
        which acts as an input while the outputs are synchronized to it. This
        method is only used within a system when the ADF4030 is used as a SYSREF
        PLL.

        Args:
            clk (Union[clockc, int, float]): Clock object or frequency in hertz to be added as BSYNC reference
        """
        od = self._convert_input(self._o, "o_div_bsync_ref_adf4030")
        self.config["out_dividers"].append(od)
        self._add_equation(self.config["vco"] / od == bsync_ref)
        if isinstance(bsync_ref, (float, int)):
            assert self.bsync_freq_min <= bsync_ref <= self.bsync_freq_max, (
                "BSYNC reference frequency out of range\n",
                f"Got {bsync_ref}, expected between {self.bsync_freq_min} and {self.bsync_freq_max}\n",
                "Adjust BSYNC ranges or BSYNC reference input frequency",
            )
        self._add_equation(
            [
                bsync_ref >= self.bsync_freq_min,
                bsync_ref <= self.bsync_freq_max,
            ]
        )
        # THIS IS REALLY UNCOMMON SO LEAVE OUT OF MAIN CONSTRAINTS FOR NOW
        # Add constraint to make BSYNC an integer
        # ref = self.model.integer_var(name="bsync_val", domain=(1,int(self.bsync_freq_max)))
        # self._add_equation(
        #     ref == bsync_ref
        # )

    def set_requested_clocks(
        self,
        ref_in: Union[int, float, CpoExpr, GK_Intermediate],
        out_freq: Union[int, List[int]],
        clk_names: List[str],
    ) -> None:
        """Define necessary clocks to be generated in model.

        Args:
            ref_in (int, float, CpoExpr, GK_Intermediate): Reference frequency in hertz
            out_freq (int): list of required clocks to be output
            clk_names (List[str]): list of clock names

        Raises:
            Exception: If out_freq and clk_names are not the same length
        """
        if len(out_freq) != len(clk_names):
            raise Exception("out_freq and clk_names must be the same length")
        self._setup(ref_in)
        self._clk_names = clk_names

        for i, clk in enumerate(clk_names):
            o_div_name = f"o_div_{clk}_adf4030"
            self.config[o_div_name] = self._convert_input(self.o, o_div_name)
            self.config["out_dividers"].append(self.config[o_div_name])

            self._add_equation(
                self.config[o_div_name] * out_freq[i] == self.config["vco"],
            )

