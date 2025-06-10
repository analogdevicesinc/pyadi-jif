"""Clock parent metaclass to maintain consistency for all clock chip."""

from abc import ABCMeta, abstractmethod
from typing import Dict, List, Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.common import core
from adijif.draw import Layout, Node
from adijif.gekko_trans import gekko_translation


class clock(core, gekko_translation, metaclass=ABCMeta):
    """Parent metaclass for all clock chip classes."""

    @property
    @abstractmethod
    def find_dividers(self) -> Dict:
        """Find all possible divider settings that validate config.

        Raises:
            NotImplementedError: Method not implemented
        """
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def list_available_references(self) -> List[int]:
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
        self.solution = self.model.solve(LogVerbosity="Quiet")
        if self.solution.solve_status not in ["Feasible", "Optimal"]:
            raise Exception("Solution Not Found")
        return self.solution

    def solve(self) -> Union[None, CpoSolveResult]:
        """Local solve method for clock model.

        Call model solver with correct arguments.

        Returns:
            [None,CpoSolveResult]: When cplex solver is used CpoSolveResult is returned

        Raises:
            Exception: If solver is not valid

        """
        if self.solver == "gekko":
            return self._solve_gekko()
        elif self.solver == "CPLEX":
            return self._solve_cplex()
        else:
            raise Exception(f"Unknown solver {self.solver}")

    def draw(self, lo: Layout = None) -> str:
        """Generic Draw converter model.

        Args:
            lo (Layout): Layout object to draw on

        Returns:
            str: Path to image file

        Raises:
            Exception: If no solution is saved
        """
        if not self._saved_solution:
            raise Exception("No solution to draw. Must call solve first.")
        clocks = self._saved_solution
        system_draw = lo is not None
        name = self.name.lower()

        if not system_draw:
            lo = Layout(f"{name} Example")
        else:
            assert isinstance(lo, Layout), "lo must be a Layout object"

        ic_node = Node(self.name)
        lo.add_node(ic_node)

        # rate = clocks[f"{name}_ref_clk"]
        # Find key with ending
        ref_name = None
        for key in clocks.keys():
            if "vcxo" in key.lower():
                ref_name = key
                break
        if ref_name is None:
            raise Exception(f"No clock found for vcxo\n.Options: {clocks.keys()}")

        if not system_draw:
            ref_in = Node("REF_IN", ntype="input")
            lo.add_node(ref_in)
        else:
            to_node = lo.get_node(ref_name)
            from_node = lo.get_connection(to=to_node.name)
            assert from_node, "No connection found"
            assert isinstance(from_node, list), "Connection must be a list"
            assert len(from_node) == 1, "Only one connection allowed"
            ref_in = from_node[0]["from"]
            # Remove to_node since it is not needed
            lo.remove_node(to_node.name)

        rate = clocks[ref_name]

        lo.add_connection({"from": ref_in, "to": ic_node, "rate": rate})

        # Add each output clock
        for o_clk_name in clocks["output_clocks"]:
            rate = clocks["output_clocks"][o_clk_name]["rate"]
            # div = clocks['output_clocks'][o_clk_name]['divider']
            if not system_draw:
                out_node = Node(o_clk_name, ntype="out_clock_connected")
                lo.add_node(out_node)
                lo.add_connection({"from": ic_node, "to": out_node, "rate": rate})

        if not system_draw:
            return lo.draw()
