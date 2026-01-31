"""PySym: Solver-agnostic abstraction layer for optimization models.

This module provides a unified API for defining optimization problems that can be
compiled to different solvers (CPLEX, GEKKO, OR-Tools, etc.) without code changes.

Basic usage:
    model = Model(solver="CPLEX")
    x = IntegerVar(domain=range(1, 10), name="x")
    y = IntegerVar(domain=range(1, 10), name="y")
    model.add_variable(x)
    model.add_variable(y)
    model.add_constraint(x + y == 10)
    model.add_objective(x, minimize=True)
    solution = model.solve()
    print(solution.get_value(x))
"""

from adijif.pysym.model import Model
from adijif.pysym.variables import BinaryVar, Constant, ContinuousVar, IntegerVar

__all__ = [
    "Model",
    "IntegerVar",
    "BinaryVar",
    "ContinuousVar",
    "Constant",
]
