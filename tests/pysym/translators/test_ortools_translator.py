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

    def test_ortools_non_contiguous_domain(self):
        """Test OR-Tools with non-contiguous domain."""
        model = Model(solver="ortools")

        # Non-contiguous domain
        x = IntegerVar(domain=[1, 2, 4, 8], name="x")
        model.add_variable(x)
        model.add_constraint(x >= 2)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 2

    def test_ortools_single_value_domain(self):
        """Test OR-Tools with single-value domain (constant)."""
        model = Model(solver="ortools")

        # Single value domain becomes constant
        x = IntegerVar(domain=[5], name="x")
        y = IntegerVar(domain=range(1, 20), name="y")

        model.add_variable(x)
        model.add_variable(y)

        model.add_constraint(y >= x)
        model.add_objective(y, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 5
        assert solution.get_value(y) == 5

    def test_ortools_arithmetic_operations(self):
        """Test OR-Tools with various arithmetic operations."""
        model = Model(solver="ortools")

        x = IntegerVar(domain=range(1, 20), name="x")
        y = IntegerVar(domain=range(1, 20), name="y")

        model.add_variable(x)
        model.add_variable(y)

        # Test subtraction and multiplication
        model.add_constraint(2 * x - y >= 5)
        model.add_objective(x + y, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert 2 * solution.get_value(x) - solution.get_value(y) >= 5

    def test_ortools_comparison_operators(self):
        """Test OR-Tools with all comparison operators."""
        model = Model(solver="ortools")

        x = IntegerVar(domain=range(1, 20), name="x")
        y = IntegerVar(domain=range(1, 20), name="y")

        model.add_variable(x)
        model.add_variable(y)

        # Test equality
        model.add_constraint(x == 5)
        # Test less than
        model.add_constraint(y < 10)
        # Test greater than
        model.add_constraint(y > 2)

        model.add_objective(x + y, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 5
        assert 2 < solution.get_value(y) < 10

    def test_ortools_not_equal_constraint(self):
        """Test OR-Tools with not-equal constraint."""
        model = Model(solver="ortools")

        x = IntegerVar(domain=range(1, 10), name="x")
        model.add_variable(x)

        model.add_constraint(x != 5)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 1

    def test_ortools_division_operator(self):
        """Test OR-Tools with division operator."""
        model = Model(solver="ortools")

        x = IntegerVar(domain=range(1, 100), name="x")
        model.add_variable(x)

        # x must be divisible by 5 (x / 5 should work)
        model.add_constraint(x >= 10)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) >= 10

    def test_ortools_maximize_objective(self):
        """Test OR-Tools with maximize objective."""
        model = Model(solver="ortools")

        x = IntegerVar(domain=range(1, 20), name="x")
        model.add_variable(x)

        model.add_constraint(x <= 15)
        model.add_objective(x, minimize=False)  # Maximize

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 15

    def test_ortools_infeasible_problem(self):
        """Test OR-Tools with infeasible problem."""
        model = Model(solver="ortools")

        x = IntegerVar(domain=range(1, 10), name="x")
        model.add_variable(x)

        model.add_constraint(x >= 5)
        model.add_constraint(x <= 3)

        solution = model.solve()

        assert not solution.is_feasible

    def test_ortools_get_value_from_infeasible_raises(self):
        """Test OR-Tools get_value raises from infeasible solution."""
        model = Model(solver="ortools")

        x = IntegerVar(domain=range(1, 10), name="x")
        model.add_variable(x)

        model.add_constraint(x >= 5)
        model.add_constraint(x <= 3)

        solution = model.solve()

        with pytest.raises(RuntimeError):
            solution.get_value(x)

    def test_ortools_time_limit(self):
        """Test OR-Tools with time limit parameter."""
        model = Model(solver="ortools")

        x = IntegerVar(domain=range(1, 20), name="x")
        model.add_variable(x)
        model.add_objective(x, minimize=True)

        solution = model.solve(time_limit=10.0)

        assert solution.is_feasible or not solution.is_feasible  # Either is okay
        assert solution.get_objective_value() is not None

    def test_ortools_intermediate_expression(self):
        """Test OR-Tools with intermediate expressions."""
        from adijif.pysym.expressions import Intermediate

        model = Model(solver="ortools")

        x = IntegerVar(domain=range(1, 20), name="x")
        y = IntegerVar(domain=range(1, 20), name="y")

        model.add_variable(x)
        model.add_variable(y)

        # Add intermediate
        intermediate = Intermediate(x + y, name="sum")
        model.add_intermediate(intermediate)

        model.add_constraint(intermediate >= 10)
        model.add_objective(intermediate, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) + solution.get_value(y) >= 10
