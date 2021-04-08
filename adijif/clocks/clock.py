"""Clock parent metaclass to maintain consistency for all clock chip."""
from abc import ABCMeta, abstractmethod
from typing import Dict, List, Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from adijif.common import core
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
    def list_possible_references(self) -> List[int]:
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
        return False

    def _solve_cplex(self) -> CpoSolveResult:
        self.solution = self.model.solve(LogVerbosity="Quiet")
        if self.solution.solve_status != "Feasible":
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
