"""Tests for CPLEX translator."""

import pytest

from adijif.pysym.model import Model
from adijif.pysym.translators.registry import get_translator
from adijif.pysym.variables import BinaryVar, IntegerVar
from adijif.solvers import cplex_solver


@pytest.mark.skipif(not cplex_solver, reason="CPLEX not installed")
class TestCPLEXTranslator:
    """Tests for CPLEX translator."""

    def test_cplex_availability(self):
        """Test CPLEX translator availability check."""
        translator = get_translator("CPLEX")
        assert translator.check_availability() is True

    def test_cplex_simple_variable_constraint(self):
        """Test simple integer variable with constraint."""
        model = Model(solver="CPLEX")

        x = IntegerVar(domain=range(1, 10), name="x")
        model.add_variable(x)
        model.add_constraint(x >= 5)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 5

    def test_cplex_two_variable_problem(self):
        """Test problem with two variables."""
        model = Model(solver="CPLEX")

        x = IntegerVar(domain=range(1, 100), name="x")
        y = IntegerVar(domain=range(1, 100), name="y")

        model.add_variable(x)
        model.add_variable(y)
        model.add_constraint(x + y >= 50)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        x_val = solution.get_value(x)
        y_val = solution.get_value(y)
        assert x_val + y_val >= 50

    def test_cplex_multiple_constraints(self):
        """Test problem with multiple constraints."""
        model = Model(solver="CPLEX")

        x = IntegerVar(domain=range(1, 100), name="x")
        y = IntegerVar(domain=range(1, 100), name="y")

        model.add_variable(x).add_variable(y)
        model.add_constraint(x + y >= 50)
        model.add_constraint(x - y <= 20)
        model.add_constraint(x >= 10)
        model.add_objective(x + y, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        x_val = solution.get_value(x)
        y_val = solution.get_value(y)

        # Verify all constraints
        assert x_val + y_val >= 50
        assert x_val - y_val <= 20
        assert x_val >= 10

    def test_cplex_binary_variable(self):
        """Test with binary variable."""
        model = Model(solver="CPLEX")

        flag = BinaryVar(name="flag")
        x = IntegerVar(domain=range(1, 100), name="x")

        model.add_variable(flag)
        model.add_variable(x)
        model.add_constraint(flag == 1)
        model.add_constraint(x >= 50)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(flag) == 1
        assert solution.get_value(x) == 50

    def test_cplex_list_domain(self):
        """Test variable with list domain."""
        model = Model(solver="CPLEX")

        x = IntegerVar(domain=[1, 2, 4, 8, 16], name="x")
        model.add_variable(x)
        model.add_constraint(x >= 4)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 4

    def test_cplex_expression_constraint(self):
        """Test constraint from complex expression."""
        model = Model(solver="CPLEX")

        x = IntegerVar(domain=range(1, 20), name="x")
        y = IntegerVar(domain=range(1, 20), name="y")

        model.add_variable(x).add_variable(y)
        # (x + y) * 2 >= 50
        model.add_constraint((x + y) * 2 >= 50)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        x_val = solution.get_value(x)
        y_val = solution.get_value(y)
        assert (x_val + y_val) * 2 >= 50

    def test_cplex_maximize_objective(self):
        """Test maximization objective."""
        model = Model(solver="CPLEX")

        x = IntegerVar(domain=range(1, 20), name="x")
        model.add_variable(x)
        model.add_constraint(x <= 15)
        model.add_objective(x, minimize=False)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 15

    def test_cplex_infeasible_problem(self):
        """Test handling of infeasible problem."""
        model = Model(solver="CPLEX")

        x = IntegerVar(domain=range(1, 10), name="x")
        model.add_variable(x)
        model.add_constraint(x >= 10)  # Infeasible: x max is 9
        model.add_constraint(x <= 5)  # Conflicting

        solution = model.solve()

        assert not solution.is_feasible

    def test_cplex_expression_objective(self):
        """Test objective from expression."""
        model = Model(solver="CPLEX")

        x = IntegerVar(domain=range(1, 20), name="x")
        y = IntegerVar(domain=range(1, 20), name="y")

        model.add_variable(x).add_variable(y)
        model.add_constraint(x + y >= 20)
        # Minimize x + 2*y
        model.add_objective(x + 2 * y, minimize=True)

        solution = model.solve()

        assert solution.is_feasible

    def test_cplex_negative_coefficients(self):
        """Test constraints with negative coefficients."""
        model = Model(solver="CPLEX")

        x = IntegerVar(domain=range(1, 100), name="x")
        y = IntegerVar(domain=range(1, 100), name="y")

        model.add_variable(x).add_variable(y)
        # -x + y >= 5
        model.add_constraint(-x + y >= 5)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        x_val = solution.get_value(x)
        y_val = solution.get_value(y)
        assert -x_val + y_val >= 5
