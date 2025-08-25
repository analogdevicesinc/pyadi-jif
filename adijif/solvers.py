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

if not cplex_solver and not gekko_solver:
    raise ImportError(
        "No solver found. gekko or docplex/cplex must be installed."
        + "\n-> Use `pip install pyadi-jif[cplex]` or `pip install pyadi-jif[gekko]`"
    )


def tround(value: float, tol: float = 1e-4) -> Union[float, int]:
    """Round if expected to have computational noise."""
    if value.is_integer():
        return int(value)
    if abs(value - round(value)) < tol:
        return round(value)
    return value
