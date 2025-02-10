"""Xilinx Common PLL class."""

from typing import Optional, Union

from docplex.cp.solution import CpoSolveResult  # type: ignore

from ...common import core
from ...gekko_trans import gekko_translation
from ...solvers import CpoModel


class XilinxPLL(core, gekko_translation):
    """Xilinx Common PLL class."""

    plls = None
    parent = None
    _model = None  # Hold internal model when used standalone
    _solution = None  # Hold internal solution when used standalone

    def __init__(
        self,
        parent=None,  # noqa: ANN001
        speed_grade: Optional[str] = "-2",
        transceiver_type: Optional[str] = "GTXE2",
        *args,  # noqa: ANN002
        **kwargs,  # noqa: ANN003
    ) -> None:
        """Initalize 7 series transceiver PLLs.

        Args:
            parent (system or converter, optional): Parent object. Defaults to None.
            speed_grade (str, optional): Speed grade. Defaults to "-2".
            transceiver_type (str, optional): Transceiver type. Defaults to "GTXE2".
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Raises:
            Exception: If Gekko solver is used
        """
        self.transceiver_type = transceiver_type
        self.speed_grade = speed_grade
        super().__init__(*args, **kwargs)
        self.parent = parent
        if parent:
            self._model = parent.model
            self._solution = parent.solution
            self.solver = parent.solver
        self.add_plls()
        if self.solver == "gekko":
            raise Exception("Gekko solver not supported for Xilinx PLLs")

    @property
    def model(self) -> CpoModel:
        """Internal system model for solver.

        Returns:
            CpoModel: Internal system model for solver
        """
        if self.parent:
            return self.parent.model
        return self._model

    @model.setter
    def model(self, val: CpoModel) -> None:
        """Set internal system model for solver.

        Args:
            val (CpoModel): Internal system model for solver

        Raises:
            Exception: If parent model is used
        """
        if self.parent:
            raise Exception("Cannot set model when parent model is used")
        self._model = val

    @property
    def solution(self) -> CpoSolveResult:
        """Solution object from solver."""
        if self.parent:
            return self.parent.solution
        return self._solution

    @solution.setter
    def solution(self, val: CpoSolveResult) -> None:
        """Set solution object from solver.

        Args:
            val (CpoSolveResult): Solution object from solver

        Raises:
            Exception: If parent model is used
        """
        if self.parent:
            raise Exception("Cannot set solution when parent model is used")
        self._solution = val

    @property
    def transceiver_type(self) -> str:
        """Transceiver type.

        Returns:
            str: Transceiver type
        """
        return self._transceiver_type

    @transceiver_type.setter
    def transceiver_type(self, val: str) -> None:
        """Set transceiver type.

        Args:
            val (str): Transceiver type
        """
        self._check_in_range(val, self.transceiver_types_available, "transceiver_type")
        self._transceiver_type = val

    _speed_grade = -2

    @property
    def speed_grade(self) -> str:
        """speed_grade for transceiver.

        Returns:
            str: Speed grade
        """
        if self.parent:
            return self.parent.speed_grade
        return self._speed_grade

    @speed_grade.setter
    def speed_grade(self, val: str) -> None:
        """Set speed grade for transceiver.

        Args:
            val (str): Speed grade

        Raises:
            Exception: If parent model is used
        """
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
    """Common PLL class for Xilinx and Intel PLLs."""

    def __init__(self, parent_transceiver: CpoModel) -> None:
        """Initialize PLL common class.

        Args:
            parent_transceiver (CpoModel): Parent transceiver object
        """
        self.parent = parent_transceiver

    @property
    def model(self) -> CpoModel:
        """Internal system model for solver.

        Returns:
            CpoModel: Internal system model for solver
        """
        return self.parent.model

    @property
    def solver(self) -> str:
        """Solver type.

        Returns:
            str: Solver type
        """
        return self.parent.solver

    @property
    def solution(self) -> CpoSolveResult:
        """Solution object from solver.

        Returns:
            CpoSolveResult: Solution object from solver
        """
        return self.parent.solution
