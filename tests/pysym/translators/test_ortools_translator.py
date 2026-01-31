"""Tests for OR-Tools translator."""

from importlib.util import find_spec

import pytest

from adijif.pysym.model import Model
from adijif.pysym.translators.registry import get_translator
from adijif.pysym.variables import BinaryVar, IntegerVar

ortools_available = find_spec("ortools") is not None


@pytest.mark.skipif(not ortools_available, reason="OR-Tools not installed")
class TestORToolsTranslator:
    """Tests for OR-Tools translator."""

    def test_ortools_availability(self):
        """Test OR-Tools translator availability check."""
        translator = get_translator("ortools")
        assert translator.check_availability() is True

    def test_ortools_simple_problem(self):
        """Test solving a simple optimization problem with OR-Tools."""
        model = Model(solver="ortools")

        # Create variables: minimize x where x >= 5
        x = IntegerVar(domain=range(1, 20), name="x")
        model.add_variable(x)
        model.add_constraint(x >= 5)
        model.add_objective(x, minimize=True)

        # Solve
        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        assert solution.get_value(x) == 5

    def test_ortools_multiple_variables(self):
        """Test OR-Tools with multiple variables and constraints."""
        model = Model(solver="ortools")

        # Variables
        x = IntegerVar(domain=range(1, 20), name="x")
        y = IntegerVar(domain=range(1, 20), name="y")

        model.add_variable(x)
        model.add_variable(y)

        # Constraints: x + y == 10, x >= 3
        model.add_constraint(x + y == 10)
        model.add_constraint(x >= 3)

        # Objective: minimize x
        model.add_objective(x, minimize=True)

        # Solve
        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        x_val = solution.get_value(x)
        y_val = solution.get_value(y)
        assert x_val + y_val == 10
        assert x_val >= 3
        assert x_val == 3  # Minimum feasible value

    def test_ortools_binary_variables(self):
        """Test OR-Tools with binary variables."""
        model = Model(solver="ortools")

        # Binary variables
        b1 = BinaryVar(name="b1")
        b2 = BinaryVar(name="b2")

        model.add_variable(b1)
        model.add_variable(b2)

        # Constraint: at least one must be 1
        model.add_constraint(b1 + b2 >= 1)

        # Objective: minimize sum
        model.add_objective(b1 + b2, minimize=True)

        # Solve
        solution = model.solve()

        # Verify
        assert solution.is_feasible
        assert solution.get_value(b1) + solution.get_value(b2) >= 1
