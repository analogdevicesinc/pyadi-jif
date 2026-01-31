"""Tests for Solution class."""

import pytest

from adijif.pysym.solution import Solution
from adijif.pysym.variables import IntegerVar


class TestSolution:
    """Tests for Solution class."""

    def test_solution_creation(self):
        """Test creating a solution."""
        x = IntegerVar(range(1, 10), name="x")
        var_map = {"x": x}
        native_var_map = {"x": None}

        solution = Solution(None, "CPLEX", var_map, native_var_map)

        assert solution.solver_name == "CPLEX"
        assert solution.var_map == var_map

    def test_solution_repr(self):
        """Test solution string representation."""
        solution = Solution(None, "CPLEX", {}, {})
        solution._is_feasible = True

        repr_str = repr(solution)
        assert "Solution" in repr_str
        assert "CPLEX" in repr_str

    def test_solution_feasible_property(self):
        """Test feasible property."""
        solution = Solution(None, "CPLEX", {}, {})
        solution._is_feasible = True

        assert solution.is_feasible is True

        solution._is_feasible = False
        assert solution.is_feasible is False

    def test_solution_feasible_property_not_set(self):
        """Test accessing feasible property before it's set."""
        solution = Solution(None, "CPLEX", {}, {})

        with pytest.raises(ValueError):
            _ = solution.is_feasible

    def test_solution_optimal_property(self):
        """Test optimal property."""
        solution = Solution(None, "CPLEX", {}, {})
        solution._is_optimal = True

        assert solution.is_optimal is True

    def test_solution_optimal_default_false(self):
        """Test optimal property defaults to False."""
        solution = Solution(None, "CPLEX", {}, {})

        assert solution.is_optimal is False

    def test_solution_objective_value_property(self):
        """Test objective value property."""
        solution = Solution(None, "CPLEX", {}, {})
        solution._objective_value = 42.5

        assert solution.objective_value == 42.5

    def test_solution_objective_value_default_none(self):
        """Test objective value property defaults to None."""
        solution = Solution(None, "CPLEX", {}, {})

        assert solution.objective_value is None

    def test_solution_get_value_not_implemented(self):
        """Test get_value raises NotImplementedError."""
        x = IntegerVar(range(1, 10), name="x")
        solution = Solution(None, "CPLEX", {"x": x}, {})
        solution._is_feasible = True

        with pytest.raises(NotImplementedError):
            solution.get_value(x)

    def test_solution_get_value_infeasible(self):
        """Test get_value with infeasible solution."""
        x = IntegerVar(range(1, 10), name="x")
        solution = Solution(None, "CPLEX", {"x": x}, {})
        solution._is_feasible = False

        with pytest.raises(RuntimeError):
            solution.get_value(x)

    def test_solution_get_value_unknown_variable(self):
        """Test get_value with variable not in solution."""
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        solution = Solution(None, "CPLEX", {"x": x}, {})
        solution._is_feasible = True

        with pytest.raises(ValueError):
            solution.get_value(y)

    def test_solution_get_values_multiple(self):
        """Test get_values method."""
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        var_map = {"x": x, "y": y}
        native_var_map = {"x": None, "y": None}

        solution = Solution(None, "CPLEX", var_map, native_var_map)
        solution._is_feasible = True

        # This will raise NotImplementedError from get_value
        with pytest.raises(NotImplementedError):
            solution.get_values([x, y])
