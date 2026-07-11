"""Clock parent metaclass to maintain consistency for all clock chip."""

import copy
from abc import ABCMeta, abstractmethod
from typing import Any, Dict, List, Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.common import core
from adijif.draw import Layout, Node
from adijif.gekko_trans import gekko_translation
from adijif.optimization import apply_objectives
from adijif.solvers import CpoExpr


class clock(core, gekko_translation, metaclass=ABCMeta):
    """Parent metaclass for all clock chip classes.

    Two supported call orders:

    Standalone mode (used in validation/exploration scripts)::

        clk = HMC7044()
        clk.n2 = 24                                       # optional divider constraints
        clk.set_requested_clocks(vcxo, freqs, names)      # define requested outputs
        clk.solve()                                       # caches config internally
        cfg = clk.get_config()                            # optional: returns same dict
        img = clk.draw()                                  # uses cached config

    System mode (driven by ``adijif.system``)::

        clk.setup_constraints(vcxo)                       # called by system.initialize()
        expr = clk.request_clock_constraint(name)         # repeated for each output
        # solver runs at the system level (system.do_solve)
        cfg = clk.get_config(solution)
        clk.draw(layout)

    In both modes, ``set_requested_clocks`` / ``setup_constraints`` must be
    called before ``solve``/``get_config``, and dividers must be configured
    via properties (e.g. ``n2``, ``r2``, ``d``) before either entry point
    if you want to constrain the search space.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize solver state and isolate mutable clock selections."""
        super().__init__(*args, **kwargs)
        for cls in type(self).mro():
            for name, value in vars(cls).items():
                if (
                    name.startswith("_")
                    and not name.startswith("__")
                    and name not in self.__dict__
                    and isinstance(value, (list, dict, set))
                ):
                    setattr(self, name, copy.deepcopy(value))

    def _parse_reference(
        self, vcxo: Union[int, float, CpoExpr]
    ) -> Union[int, float, CpoExpr]:
        """Parse reference clock input.

        Args:
            vcxo (Union[int, float, CpoExpr]): Reference clock input

        Returns:
            Union[int, float, CpoExpr]: Parsed reference clock
        """
        if type(vcxo) not in [int, float]:
            vcxo_result = vcxo(self.model)
            # Handle range type (returns dict with "range" key)
            if isinstance(vcxo_result, dict):
                self.vcxo_i = vcxo_result
                self.vcxo_arb = None
                vcxo = self.vcxo_i["range"]
            # Handle arb_source type (returns direct expression)
            else:
                self.vcxo_i = False
                self.vcxo_arb = vcxo  # Store original for get_config
                vcxo = vcxo_result
        else:
            self.vcxo_i = False
            self.vcxo_arb = None

        return vcxo

    @abstractmethod
    def find_dividers(self, *args: Any, **kwargs: Any) -> Dict:
        """Find all possible divider settings that validate config.

        Raises:
            NotImplementedError: Method not implemented
        """
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def list_available_references(
        self, *args: Any, **kwargs: Any
    ) -> List[int]:
        """Determine all references that can be generated.

        Based on config list possible references that can be generated
        based on VCO and output dividers

        Raises:
            NotImplementedError: Method not implemented
        """
        raise NotImplementedError  # pragma: no cover

    def _solve_gekko(self) -> bool:
        """Local solve method for clock model.

        Call model solver with correct arguments.

        Returns:
            bool: Always False
        """
        apply_objectives(self.model, self.solver, self._objectives)
        self.model.options.SOLVER = 1  # APOPT solver
        self.model.solver_options = [
            "minlp_maximum_iterations 1000",  # minlp iterations with integer solution
            "minlp_max_iter_with_int_sol 100",  # treat minlp as nlp
            "minlp_as_nlp 0",  # nlp sub-problem max iterations
            "nlp_maximum_iterations 500",  # 1 = depth first, 2 = breadth first
            "minlp_branch_method 1",  # maximum deviation from whole number
            "minlp_integer_tol 0",  # covergence tolerance (MUST BE 0 TFC)
            "minlp_gap_tol 0.1",
        ]

        self.model.solve(disp=False)
        self.model.cleanup()
        return False

    # def _add_objective(self, sysrefs: List) -> None:
    #     pass

    def _solve_cplex(self) -> CpoSolveResult:
        apply_objectives(self.model, self.solver, self._objectives)
        self._solution = self.model.solve(LogVerbosity="Quiet")
        if self._solution.solve_status not in ["Feasible", "Optimal"]:
            raise Exception("Solution Not Found")
        return self._solution

    def solve(self) -> Union[None, CpoSolveResult]:
        """Local solve method for clock model.

        Call the underlying solver and immediately cache the resulting
        configuration so ``draw()`` can be invoked without an
        intermediate ``get_config()`` call.

        Returns:
            [None,CpoSolveResult]: When cplex solver is used CpoSolveResult is returned

        Raises:
            Exception: If solver is not valid

        """
        if self.solver == "gekko":
            result = self._solve_gekko()
        elif self.solver == "CPLEX":
            result = self._solve_cplex()
        else:
            raise Exception(f"Unknown solver {self.solver}")
        # Best-effort cache of the config so draw() can be called after
        # solve() alone in the standard standalone flow. Some chips
        # (e.g. AD9545) impose extra requirements on get_config that may
        # not be satisfied in minimal smoke tests; swallow those here so
        # solve() retains its narrow "just solve the model" contract.
        try:
            self.get_config()
        except Exception:  # noqa: S110 - intentional best-effort cache
            pass
        return result

    def draw(self, lo: Layout = None) -> str:
        """Generic Draw converter model.

        Args:
            lo (Layout): Layout object to draw on

        Returns:
            str: Path to image file

        Raises:
            Exception: If no solution is saved
        """
        if not self._last_config:
            raise Exception("No solution to draw. Must call solve first.")
        clocks = self._last_config
        system_draw = lo is not None
        name = self.name.lower()

        if not system_draw:
            lo = Layout(f"{name} Example")
        else:
            assert isinstance(lo, Layout), "lo must be a Layout object"

        ic_node = Node(self.name)
        lo.add_node(ic_node)
        # Expose the IC node so system_draw can connect downstream
        # converters/PLLs to this clock. Subclasses with chip-internal
        # diagrams (HMC7044, LTC6953) populate this in _init_diagram().
        self.ic_diagram_node = ic_node

        # rate = clocks[f"{name}_ref_clk"]
        # Find key with ending
        ref_name = None
        for key in clocks.keys():
            if "vcxo" in key.lower():
                ref_name = key
                break
        if ref_name is None:
            raise Exception(
                f"No clock found for vcxo\n.Options: {clocks.keys()}"
            )

        if not system_draw:
            ref_in = Node("REF_IN", ntype="input")
            lo.add_node(ref_in)
        else:
            try:
                to_node = lo.get_node(ref_name)
            except ValueError:
                # Nothing upstream placed a reference-clock placeholder for
                # us to splice into; create our own REF_IN like HMC7044 and
                # LTC6953 do in the same situation.
                ref_in = Node("REF_IN", ntype="input")
                lo.add_node(ref_in)
            else:
                from_node = lo.get_connection(to=to_node.name)
                assert from_node, "No connection found"
                assert isinstance(from_node, list), "Connection must be a list"
                assert len(from_node) == 1, "Only one connection allowed"
                ref_in = from_node[0]["from"]
                # Remove to_node since it is not needed
                lo.remove_node(to_node.name)

        rate = clocks[ref_name]

        lo.add_connection({"from": ref_in, "to": ic_node, "rate": rate})

        # Add each output clock. In system_draw mode the converter and FPGA
        # diagrams later look these up by name (e.g. ``AD9680_ref_clk``) to
        # wire their inputs, so we must place the nodes regardless of mode.
        for o_clk_name in clocks["output_clocks"]:
            rate = clocks["output_clocks"][o_clk_name]["rate"]
            ntype = "dummy" if system_draw else "out_clock_connected"
            out_node = Node(o_clk_name, ntype=ntype)
            lo.add_node(out_node)
            lo.add_connection({"from": ic_node, "to": out_node, "rate": rate})

        if not system_draw:
            return lo.draw()
