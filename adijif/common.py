"""Common class for all JIF components."""
from typing import Union

from adijif.solvers import GEKKO, CpoModel  # type: ignore


class core:
    """Common class for all JIF components.

    This is the central point for all classes in module

    """

    solver = "gekko"  # "CPLEX"

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
