"""Tests for pysym Objective types."""

import pytest

from adijif.pysym.objectives import LexicographicObjective, Objective
from adijif.pysym.variables import IntegerVar


class TestObjective:
    """Tests for Objective class."""

    def test_objective_minimize(self):
        """Test creating a minimize objective."""
        x = IntegerVar(range(1, 10), name="x")
        obj = Objective(x, minimize=True)

        assert obj.expr is x
        assert obj.minimize is True

    def test_objective_maximize(self):
        """Test creating a maximize objective."""
        x = IntegerVar(range(1, 10), name="x")
        obj = Objective(x, minimize=False)

        assert obj.expr is x
        assert obj.minimize is False

    def test_objective_with_name(self):
        """Test objective with custom name."""
        x = IntegerVar(range(1, 10), name="x")
        obj = Objective(x, minimize=True, name="cost")

        assert obj.name == "cost"

    def test_objective_with_weight(self):
        """Test objective with weight."""
        x = IntegerVar(range(1, 10), name="x")
        obj = Objective(x, minimize=True, weight=2.5)

        assert obj.weight == 2.5

    def test_objective_default_name(self):
        """Test objective default names."""
        x = IntegerVar(range(1, 10), name="x")

        obj_min = Objective(x, minimize=True)
        assert "minimize" in obj_min.name

        obj_max = Objective(x, minimize=False)
        assert "maximize" in obj_max.name

    def test_objective_from_expression(self):
        """Test creating objective from arithmetic expression."""
        x = IntegerVar(range(1, 100), name="x")
        y = IntegerVar(range(1, 100), name="y")

        expr = x * 2 + y
        obj = Objective(expr, minimize=True)

        assert obj.expr is expr

    def test_objective_rejects_constraint(self):
        """Test that Objective rejects constraint expressions."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = x >= 5  # This is a constraint, not arithmetic

        with pytest.raises(ValueError):
            Objective(constraint, minimize=True)

    def test_objective_invalid_type(self):
        """Test that Objective rejects invalid types."""
        with pytest.raises(TypeError):
            Objective("not_a_variable", minimize=True)

    def test_objective_repr(self):
        """Test objective string representation."""
        x = IntegerVar(range(1, 10), name="x")
        obj = Objective(x, minimize=True)

        repr_str = repr(obj)
        assert "Objective" in repr_str
        assert "minimize" in repr_str


class TestLexicographicObjective:
    """Tests for LexicographicObjective."""

    def test_lexicographic_basic(self):
        """Test creating basic lexicographic objective."""
        x = IntegerVar(range(1, 100), name="x")
        y = IntegerVar(range(1, 100), name="y")

        objectives = [
            (x, True),  # First: minimize x
            (y, True),  # Then: minimize y
        ]

        lex_obj = LexicographicObjective(objectives)

        assert len(lex_obj.objectives) == 2
        assert lex_obj.objectives[0].expr is x
        assert lex_obj.objectives[1].expr is y

    def test_lexicographic_with_names(self):
        """Test lexicographic objective with names."""
        x = IntegerVar(range(1, 100), name="x")
        y = IntegerVar(range(1, 100), name="y")

        objectives = [(x, True), (y, False)]
        names = ["cost", "weight"]

        lex_obj = LexicographicObjective(objectives, names)

        assert lex_obj.objectives[0].name == "cost"
        assert lex_obj.objectives[1].name == "weight"

    def test_lexicographic_mixed_directions(self):
        """Test lexicographic with mixed minimize/maximize."""
        x = IntegerVar(range(1, 100), name="x")
        y = IntegerVar(range(1, 100), name="y")

        objectives = [
            (x, False),  # Maximize x
            (y, True),  # Minimize y
        ]

        lex_obj = LexicographicObjective(objectives)

        assert lex_obj.objectives[0].minimize is False
        assert lex_obj.objectives[1].minimize is True

    def test_lexicographic_from_expressions(self):
        """Test lexicographic from complex expressions."""
        x = IntegerVar(range(1, 100), name="x")
        y = IntegerVar(range(1, 100), name="y")

        cost_expr = x * 2 + y
        weight_expr = x + y * 3

        objectives = [
            (cost_expr, True),  # Minimize cost
            (weight_expr, True),  # Minimize weight
        ]

        lex_obj = LexicographicObjective(objectives)

        assert len(lex_obj.objectives) == 2

    def test_lexicographic_empty_objectives(self):
        """Test that lexicographic rejects empty objective list."""
        with pytest.raises(ValueError):
            LexicographicObjective([])

    def test_lexicographic_rejects_constraints(self):
        """Test that lexicographic rejects constraint expressions."""
        x = IntegerVar(range(1, 10), name="x")

        # One objective is a constraint
        objectives = [
            (x >= 5, True),  # This is a constraint
        ]

        with pytest.raises(ValueError):
            LexicographicObjective(objectives)

    def test_lexicographic_invalid_type(self):
        """Test that lexicographic rejects invalid expression types."""
        objectives = [
            ("not_a_variable", True),
        ]

        with pytest.raises(TypeError):
            LexicographicObjective(objectives)

    def test_lexicographic_repr(self):
        """Test lexicographic objective string representation."""
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        lex_obj = LexicographicObjective([(x, True), (y, False)])

        repr_str = repr(lex_obj)
        assert "LexicographicObjective" in repr_str

    def test_lexicographic_many_objectives(self):
        """Test lexicographic with many objectives."""
        vars = [IntegerVar(range(1, 100), name=f"x{i}") for i in range(5)]
        objectives = [(var, i % 2 == 0) for i, var in enumerate(vars)]

        lex_obj = LexicographicObjective(objectives)

        assert len(lex_obj.objectives) == 5
