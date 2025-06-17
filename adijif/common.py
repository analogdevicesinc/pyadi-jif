"""Common class for all JIF components."""

from typing import List, Union

from adijif.solvers import CpoModel  # noqa: BLK100
from adijif.solvers import GK_Operators  # noqa: BLK100
from adijif.solvers import GEKKO, CpoExpr, GK_Intermediate, GKVariable


class core:
    """Common class for all JIF components.

    This is the central point for all classes in module

    """

    solver = "CPLEX"  # "CPLEX"

    _objectives = []

    def _add_objective(
        self,
        objective: List[Union[GKVariable, GK_Intermediate, GK_Operators, CpoExpr]],
    ) -> None:
        if isinstance(objective, list):
            self._objectives += objective
        else:
            self._objectives.append(objective)

    def __init__(
        self, model: Union[GEKKO, CpoModel] = None, solver: str = None
    ) -> None:
        """Initalize clocking model.

        When usings the clocking models standalone, typically for
        validation flows, a solver model is created internally.
        For system level work, a shared model is passed.

        Args:
            model (GEKKO,CpoModel): Solver model
            solver (str): Solver name (gekko or CPLEX)

        Raises:
            Exception: If solver is not valid
        """
        self._saved_solution = None
        self._objectives = []
        self._solution = None
        self.configs = []  # type: List[dict]
        if hasattr(self, "_init_diagram"):
            self._init_diagram()
        if solver:
            self.solver = solver
        if self.solver == "gekko":
            if model:
                assert isinstance(
                    model, GEKKO
                ), "Input model must be of type gekko.GEKKO"
            else:
                model = GEKKO(remote=False)
        elif self.solver == "CPLEX":
            if model:
                assert isinstance(
                    model, CpoModel
                ), "Input model must be of type docplex.cp.model.CpoModel"
            else:
                model = CpoModel()
        else:
            raise Exception(f"Unknown solver {self.solver}")
        self.model = model
