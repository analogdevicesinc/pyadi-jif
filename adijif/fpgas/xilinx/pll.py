from abc import ABC, ABCMeta, abstractmethod
from typing import Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from ...gekko_trans import gekko_translation


class XilinxPLL:
    plls = None
    parent = None
    _model = None  # Hold internal model when used standalone
    _solution = None  # Hold internal solution when used standalone

    def __init__(self, parent=None, speed_grade="-2", transceiver_type="GTXE2", *args, **kwargs) -> None:
        """Initalize 7 series transceiver PLLs.

        Args:
            parent (system or converter, optional): Parent object. Defaults to None.
            transceiver_type (str, optional): Transceiver type. Defaults to "GTXE2".
        """
        self.transceiver_type = transceiver_type
        super().__init__(*args, **kwargs)
        self.parent = parent
        self.add_plls()

    @property
    def model(self):
        """Internal system model for solver."""
        if self.parent:
            return self.parent.model
        return self._model

    @model.setter
    def model(self, val):
        if self.parent:
            raise Exception("Cannot set model when parent model is used")
        self._model = val

    @property
    def solution(self):
        """Solution object from solver."""
        if self.parent:
            return self.parent.solution
        return self._solution

    @solution.setter
    def solution(self, val):
        if self.parent:
            raise Exception("Cannot set solution when parent model is used")
        self._solution = val

    @property
    def transceiver_type(self):
        return self._transceiver_type

    @transceiver_type.setter
    def transceiver_type(self, val):
        self._check_in_range(val, self.transceiver_types_available, "transceiver_type")
        self._transceiver_type = val

    _speed_grade = -2
    @property
    def speed_grade(self):
        if self.parent:
            return self.parent.speed_grade
        return self._speed_grade
    
    @speed_grade.setter
    def speed_grade(self, val):
        if self.parent:
            raise Exception("Cannot set speed_grade when parent model is used")
        self._speed_grade = val

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
        self.solution = self.model.solve(LogVerbosity="Normal")
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


class PLLCommon(gekko_translation):
    def __init__(self, parent_transceiver) -> None:
        self.parent = parent_transceiver

    @property
    def model(self):
        return self.parent.model

    @property
    def solver(self):
        return self.parent.solver

    @property
    def solution(self):
        return self.parent.solution
