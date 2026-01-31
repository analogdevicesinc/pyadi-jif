"""Integration tests for simple optimization problems.

These tests verify that pysym can model and solve simple problems
correctly. They are placeholders for Phase 3+ implementation once
translators are complete.
"""

import pytest

from adijif.pysym.model import Model
from adijif.pysym.variables import IntegerVar


class TestSimpleProblems:
    """Tests for simple optimization problems (Phase 3+)."""

    def test_simple_integer_minimization(self):
        """Test simple integer minimization problem.

        Phase 3: Implement this test once CPLEX translator is ready
        """
        pytest.skip("Phase 3: Requires CPLEX translator implementation")

        # Simple problem: minimize x where 5 <= x <= 10
        model = Model(solver="CPLEX")

        x = IntegerVar(domain=range(1, 100), name="x")
        model.add_variable(x)
        model.add_constraint(x >= 5)
        model.add_constraint(x <= 10)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 5

    def test_simple_constraint_satisfaction(self):
        """Test simple constraint satisfaction problem.

        Phase 3: Implement this test once translators are ready
        """
        pytest.skip("Phase 3: Requires translator implementation")

        # Problem: x + y >= 10, x - y <= 5, minimize x
        model = Model(solver="CPLEX")

        x = IntegerVar(domain=range(1, 100), name="x")
        y = IntegerVar(domain=range(1, 100), name="y")

        model.add_variable(x)
        model.add_variable(y)

        model.add_constraint(x + y >= 10)
        model.add_constraint(x - y <= 5)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        x_val = solution.get_value(x)
        y_val = solution.get_value(y)

        # Verify constraints
        assert x_val + y_val >= 10
        assert x_val - y_val <= 5

    def test_multi_objective_problem(self):
        """Test multi-objective optimization.

        Phase 3: Implement this test once CPLEX translator supports lex
        """
        pytest.skip("Phase 3: Requires CPLEX translator lex objectives")

        # Problem: minimize x, then minimize y
        model = Model(solver="CPLEX")

        x = IntegerVar(domain=range(1, 100), name="x")
        y = IntegerVar(domain=range(1, 100), name="y")

        model.add_variable(x)
        model.add_variable(y)

        model.add_constraint(x + y >= 50)

        model.add_lexicographic_objective(
            objectives=[(x, True), (y, True)],
            names=["x", "y"]
        )

        solution = model.solve()

        assert solution.is_feasible
