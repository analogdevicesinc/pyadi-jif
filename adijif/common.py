"""Common class for all JIF components."""

import copy
from typing import Any, Dict, List, Optional, Union

from adijif.optimization import Objective
from adijif.solvers import GEKKO, CpoModel


class core:
    """Common class for all JIF components.

    This is the central point for all classes in module

    """

    solver = "CPLEX"

    def _add_objective(
        self,
        expr: Any,
        *,
        sense: str = "min",
        tier: int = 0,
        weight: float = 1.0,
        name: Optional[str] = None,
    ) -> None:
        """Register an optimization objective for this component.

        Skipped silently when ``name`` matches an entry in
        ``self._disabled_objectives``, letting users suppress built-in
        objectives via ``disable_objective``.

        Args:
            expr: Solver expression to optimize. May also be a list of
                expressions; each is registered as a separate Objective with
                the same metadata.
            sense: ``"min"`` to minimize (default) or ``"max"`` to maximize.
            tier: Lexicographic priority. Lower tier = higher priority.
            weight: Within-tier multiplier when summing.
            name: Optional identifier for debugging.
        """
        if name and name in self._disabled_objectives:
            return
        if isinstance(expr, list):
            for i, e in enumerate(expr):
                item_name = f"{name}[{i}]" if name else None
                if item_name and item_name in self._disabled_objectives:
                    continue
                self._objectives.append(
                    Objective(
                        expr=e,
                        sense=sense,
                        tier=tier,
                        weight=weight,
                        name=item_name,
                    )
                )
        else:
            self._objectives.append(
                Objective(
                    expr=expr,
                    sense=sense,
                    tier=tier,
                    weight=weight,
                    name=name,
                )
            )

    def disable_objective(self, name: str) -> None:
        """Suppress a built-in objective by name on subsequent solves.

        Components register their default objectives with stable names
        (e.g. ``"hmc7044.r2_min"``); calling this method causes future
        ``_add_objective`` calls with that name to be ignored. Already-
        registered objectives are also removed.

        Args:
            name: The ``name`` field of the Objective to suppress.
        """
        self._disabled_objectives.add(name)
        self._objectives = [o for o in self._objectives if o.name != name]

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
        self._last_config = None
        self.config: Dict = copy.deepcopy(getattr(type(self), "config", {}))
        self._objectives: List[Objective] = []
        self._disabled_objectives: set = set()
        self._solution = None
        self.configs = []  # type: List[dict]
        if hasattr(self, "_init_diagram"):
            self._init_diagram()
        if solver:
            self.solver = solver
        if self.solver == "gekko":
            if model:
                assert isinstance(model, GEKKO), (
                    "Input model must be of type gekko.GEKKO"
                )
            else:
                model = GEKKO(remote=False)
        elif self.solver == "CPLEX":
            if model:
                assert isinstance(model, CpoModel), (
                    "Input model must be of type docplex.cp.model.CpoModel"
                )
            else:
                model = CpoModel()
        else:
            raise Exception(f"Unknown solver {self.solver}")
        self.model = model
