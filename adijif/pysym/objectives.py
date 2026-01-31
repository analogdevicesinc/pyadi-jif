"""Objective function types for pysym."""

from typing import List, Optional, Union

from adijif.pysym.expressions import Expression
from adijif.pysym.variables import Variable


class Objective:
    """Single-objective function.

    Represents a single objective to minimize or maximize.
    Multiple objectives can be added to a model; the behavior
    depends on the underlying solver.

    Args:
        expr: Expression to optimize
        minimize: If True, minimize; if False, maximize
        name: Optional name for debugging
        weight: Priority weight for multi-objective optimization
               (used when multiple objectives present)
               Higher weight = higher priority

    Examples:
        # Minimize x
        obj = Objective(x, minimize=True)

        # Maximize profit
        profit = revenue - cost
        obj = Objective(profit, minimize=False, name="profit")
    """

    def __init__(
        self,
        expr: Union[Variable, Expression],
        minimize: bool = True,
        name: Optional[str] = None,
        weight: float = 1.0,
    ):
        """Initialize objective."""
        if isinstance(expr, Variable):
            self.expr = expr
        elif isinstance(expr, Expression):
            if expr.is_constraint():
                raise ValueError(
                    "Cannot use constraint as objective. "
                    "Objective must be an arithmetic expression."
                )
            self.expr = expr
        else:
            raise TypeError(f"Invalid expression type: {type(expr)}")

        self.minimize = minimize
        self.name = name or ("minimize" if minimize else "maximize")
        self.weight = weight

    def __repr__(self) -> str:
        """Return string representation."""
        direction = "minimize" if self.minimize else "maximize"
        return f"Objective({direction} {self.expr})"


class LexicographicObjective:
    """Multi-objective with lexicographic priority.

    Solves a sequence of single objectives in priority order:
    1. First, find the best value for objective[0]
    2. Then, holding objective[0] at that best value, optimize objective[1]
    3. Continue for remaining objectives

    This is useful for hierarchical optimization where some goals
    are more important than others.

    Args:
        objectives: List of (expression, minimize) tuples in priority order
        names: Optional list of objective names for debugging

    Examples:
        # First minimize cost, then minimize weight (given optimal cost)
        obj = LexicographicObjective(
            objectives=[
                (cost_expr, True),
                (weight_expr, True),
            ],
            names=["cost", "weight"]
        )

        # Maximize frequency, then minimize power consumption
        obj = LexicographicObjective(
            objectives=[
                (frequency_expr, False),
                (power_expr, True),
            ],
            names=["frequency", "power"]
        )

    Note:
        Not all solvers support lexicographic objectives.
        Use Feature compatibility checking before using.
    """

    def __init__(
        self,
        objectives: List[tuple],
        names: Optional[List[str]] = None,
    ):
        """Initialize lexicographic objective.

        Args:
            objectives: List of (expression, minimize) tuples
            names: Optional list of names for objectives
        """
        if not objectives:
            raise ValueError("Must provide at least one objective")

        self.objectives = []
        for i, (expr, minimize) in enumerate(objectives):
            name = names[i] if names else f"obj_{i}"
            if isinstance(expr, Variable):
                self.objectives.append(Objective(expr, minimize, name))
            elif isinstance(expr, Expression):
                if expr.is_constraint():
                    raise ValueError(
                        f"Objective {i} is a constraint, not an arithmetic expression"
                    )
                self.objectives.append(Objective(expr, minimize, name))
            else:
                raise TypeError(f"Invalid expression type at index {i}: {type(expr)}")

    def __repr__(self) -> str:
        """Return string representation."""
        obj_strs = [str(obj) for obj in self.objectives]
        return f"LexicographicObjective([{', '.join(obj_strs)}])"
