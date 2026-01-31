"""Tests for pysym Constraint types."""

import pytest

from adijif.pysym.constraints import Constraint, ConditionalConstraint
from adijif.pysym.variables import BinaryVar, IntegerVar


class TestConstraint:
    """Tests for Constraint class."""

    def test_constraint_from_equality(self):
        """Test creating constraint from equality expression."""
        x = IntegerVar(range(1, 10), name="x")
        expr = x == 5
        constraint = Constraint(expr)

        assert constraint.expr is expr

    def test_constraint_from_inequality(self):
        """Test creating constraint from inequality."""
        x = IntegerVar(range(1, 10), name="x")
        expr = x <= 5
        constraint = Constraint(expr)

        assert constraint.expr.operator == "<="

    def test_constraint_from_complex_expression(self):
        """Test creating constraint from complex expression."""
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        expr = x + y >= 10
        constraint = Constraint(expr)

        assert constraint.expr.operator == ">="

    def test_constraint_rejects_non_constraint(self):
        """Test that Constraint rejects arithmetic expressions."""
        x = IntegerVar(range(1, 10), name="x")
        expr = x + 5  # Arithmetic, not constraint

        with pytest.raises(ValueError):
            Constraint(expr)

    def test_constraint_repr(self):
        """Test constraint string representation."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = Constraint(x >= 5)

        repr_str = repr(constraint)
        assert "Constraint" in repr_str


class TestConditionalConstraint:
    """Tests for ConditionalConstraint."""

    def test_conditional_constraint_basic(self):
        """Test creating a basic conditional constraint."""
        use_feature = BinaryVar(name="use_feature")
        value = IntegerVar(range(1, 100), name="value")

        condition = use_feature == 1
        consequent = value >= 50

        cond = ConditionalConstraint(condition, consequent)

        assert cond.condition is condition
        assert cond.consequent is consequent

    def test_conditional_constraint_rejects_non_constraint_condition(self):
        """Test that ConditionalConstraint rejects arithmetic conditions."""
        use_feature = BinaryVar(name="use_feature")
        value = IntegerVar(range(1, 100), name="value")

        # Condition is not a constraint (arithmetic)
        condition = use_feature + 1  # Not a constraint

        with pytest.raises(ValueError):
            ConditionalConstraint(condition, value >= 50)

    def test_conditional_constraint_rejects_non_constraint_consequent(self):
        """Test that ConditionalConstraint rejects arithmetic consequent."""
        use_feature = BinaryVar(name="use_feature")
        value = IntegerVar(range(1, 100), name="value")

        condition = use_feature == 1

        # Consequent is not a constraint (arithmetic)
        consequent = value + 10  # Not a constraint

        with pytest.raises(ValueError):
            ConditionalConstraint(condition, consequent)

    def test_conditional_constraint_complex(self):
        """Test conditional constraint with complex expressions."""
        x = IntegerVar(range(1, 100), name="x")
        y = IntegerVar(range(1, 100), name="y")
        use_constraint = BinaryVar(name="use_constraint")

        # Complex condition
        condition = (x + y) >= 50

        # Complex consequent
        consequent = x * 2 <= y

        cond = ConditionalConstraint(condition, consequent)

        assert cond.condition is not None
        assert cond.consequent is not None

    def test_conditional_constraint_repr(self):
        """Test conditional constraint string representation."""
        use_feature = BinaryVar(name="use_feature")
        value = IntegerVar(range(1, 100), name="value")

        cond = ConditionalConstraint(
            condition=(use_feature == 1),
            consequent=(value >= 50)
        )

        repr_str = repr(cond)
        assert "IF" in repr_str
        assert "THEN" in repr_str
