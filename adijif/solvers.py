# flake8: noqa
# pytype: skip-file
"""Common solver API management layer."""

from importlib.util import find_spec
from typing import Union

if find_spec("docplex"):
    from docplex.cp.expression import CpoExpr  # type: ignore
    from docplex.cp.expression import CpoFunctionCall  # type: ignore
    from docplex.cp.expression import CpoIntVar  # type: ignore
    from docplex.cp.model import binary_var  # type: ignore
    from docplex.cp.model import CpoModel, integer_var, interval_var  # type: ignore
    from docplex.cp.solution import CpoSolveResult  # type: ignore

    cplex_solver = True
else:
    cplex_solver = False
    CpoExpr = None
    CpoFunctionCall = None
    binary_var = None
    integer_var = None
    continuous_var = None
    interval_var = None
    CpoModel = None
    CpoSolveResult = None
    CpoIntVar = None

if find_spec("gekko"):
    import gekko  # type: ignore
    from gekko import GEKKO  # type: ignore
    from gekko.gk_operators import GK_Intermediate  # type: ignore
    from gekko.gk_operators import GK_Operators  # type: ignore
    from gekko.gk_variable import GKVariable  # type: ignore

    gekko_solver = True
else:
    gekko_solver = False
    gekko = None
    GEKKO = None
    GK_Intermediate = None
    GK_Operators = None
    GKVariable = None

if find_spec("ortools"):
    from ortools.sat.python import cp_model  # type: ignore

    ortools_solver = True
else:
    ortools_solver = False
    cp_model = None

if not cplex_solver and not gekko_solver and not ortools_solver:
    raise ImportError(
        "No solver found. Must install one of:"
        + "\n  - `pip install pyadi-jif[cplex]`"
        + "\n  - `pip install pyadi-jif[gekko]`"
        + "\n  - `pip install pyadi-jif[ortools]`"
    )


def if_then(condition, consequent):
    """Conditional constraint (if-then)."""
    # Check for pysym objects first (generic)
    try:
        from adijif.pysym.constraints import ConditionalConstraint, Constraint
        from adijif.pysym.expressions import Expression
        from adijif.pysym.variables import Constant

        # Only use ConditionalConstraint if BOTH parameters are pysym types
        is_condition_pysym = isinstance(condition, (Expression, Constraint))
        is_consequent_pysym = isinstance(consequent, (Expression, Constraint))

        # Handle boolean inputs only if we're using pysym path
        if is_condition_pysym or is_consequent_pysym:
            # Handle boolean inputs (result of constant comparisons)
            if isinstance(condition, bool):
                if condition:
                    return consequent
                else:
                    return Constant(1) == 1  # Always true

            if isinstance(consequent, bool):
                if consequent:
                    consequent = Constant(1) == 1
                else:
                    consequent = Constant(1) == 0

            # Only use ConditionalConstraint if BOTH are pysym types
            if is_condition_pysym and is_consequent_pysym:
                return ConditionalConstraint(condition, consequent)
    except ImportError:
        pass

    if cplex_solver:
        from docplex.cp.modeler import if_then as docplex_if_then

        return docplex_if_then(condition, consequent)

    raise Exception("No valid solver context for if_then")


def tround(value: float, tol: float = 1e-4) -> Union[float, int]:
    """Round if expected to have computational noise."""
    if value.is_integer():
        return int(value)
    if abs(value - round(value)) < tol:
        return round(value)
    return value
