"""Tests for GEKKO translator."""

import pytest

from adijif.pysym.model import Model
from adijif.pysym.translators.registry import get_translator
from adijif.pysym.variables import BinaryVar, IntegerVar
from adijif.solvers import gekko_solver


@pytest.mark.skipif(not gekko_solver, reason="GEKKO not installed")
class TestGEKKOTranslator:
    """Tests for GEKKO translator."""

    def test_gekko_availability(self):
        """Test GEKKO translator availability check."""
        translator = get_translator("gekko")
        assert translator.check_availability() is True

    def test_gekko_simple_variable_constraint(self):
        """Test simple integer variable with constraint."""
        model = Model(solver="gekko")

        x = IntegerVar(domain=range(1, 10), name="x")
        model.add_variable(x)
        model.add_constraint(x >= 5)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 5

    def test_gekko_two_variable_problem(self):
        """Test problem with two variables."""
        model = Model(solver="gekko")

        x = IntegerVar(domain=range(1, 50), name="x")
        y = IntegerVar(domain=range(1, 50), name="y")

        model.add_variable(x)
        model.add_variable(y)
        model.add_constraint(x + y >= 50)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        x_val = solution.get_value(x)
        y_val = solution.get_value(y)
        assert x_val + y_val >= 50

    def test_gekko_binary_variable(self):
        """Test with binary variable."""
        model = Model(solver="gekko")

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

    def test_gekko_list_domain(self):
        """Test variable with list domain (uses SOS1)."""
        model = Model(solver="gekko")

        x = IntegerVar(domain=[1, 2, 4, 8, 16], name="x")
        model.add_variable(x)
        model.add_constraint(x >= 4)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 4

    def test_gekko_rejects_conditional_constraints(self):
        """Test that GEKKO rejects conditional constraints."""
        model = Model(solver="gekko")

        use_feature = BinaryVar(name="use_feature")
        value = IntegerVar(domain=range(1, 100), name="value")

        model.add_variable(use_feature)
        model.add_variable(value)

        condition = use_feature == 1
        consequent = value >= 50

        model.add_conditional_constraint(condition, consequent)

        with pytest.raises(NotImplementedError):
            model.solve()

    def test_gekko_rejects_lexicographic_objectives(self):
        """Test that GEKKO rejects lexicographic objectives."""
        model = Model(solver="gekko")

        x = IntegerVar(domain=range(1, 20), name="x")
        y = IntegerVar(domain=range(1, 20), name="y")

        model.add_variable(x).add_variable(y)

        objectives = [(x, True), (y, True)]
        model.add_lexicographic_objective(objectives)

        with pytest.raises(NotImplementedError):
            model.solve()

    def test_gekko_expression_constraint(self):
        """Test constraint from complex expression."""
        model = Model(solver="gekko")

        x = IntegerVar(domain=range(1, 20), name="x")
        y = IntegerVar(domain=range(1, 20), name="y")

        model.add_variable(x).add_variable(y)
        model.add_constraint((x + y) * 2 >= 40)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        x_val = solution.get_value(x)
        y_val = solution.get_value(y)
        assert (x_val + y_val) * 2 >= 40

    def test_gekko_maximize_objective(self):
        """Test maximization objective."""
        model = Model(solver="gekko")

        x = IntegerVar(domain=range(1, 20), name="x")
        model.add_variable(x)
        model.add_constraint(x <= 15)
        model.add_objective(x, minimize=False)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 15

    def test_gekko_negative_coefficients(self):
        """Test constraints with negative coefficients."""
        model = Model(solver="gekko")

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
