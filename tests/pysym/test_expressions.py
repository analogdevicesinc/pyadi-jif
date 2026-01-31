"""Tests for pysym Expression and Intermediate."""

import pytest

from adijif.pysym.expressions import Expression, Intermediate
from adijif.pysym.variables import BinaryVar, Constant, IntegerVar


class TestExpression:
    """Tests for Expression class."""

    def test_expression_creation(self):
        """Test creating a basic expression."""
        x = IntegerVar(range(1, 10), name="x")
        expr = Expression(x, "+", 5)
        assert expr.left is x
        assert expr.operator == "+"
        assert expr.right == 5

    def test_arithmetic_expression(self):
        """Test building arithmetic expressions."""
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        expr = x + y
        assert expr.operator == "+"
        assert expr.left is x
        assert expr.right is y

    def test_constraint_expression(self):
        """Test building constraint expressions."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = x >= 5
        assert constraint.operator == ">="
        assert constraint.left is x
        assert constraint.right == 5

    def test_nested_expressions(self):
        """Test nested expression building."""
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        expr = (x + y) * 2
        assert expr.operator == "*"
        assert expr.left.operator == "+"
        assert expr.right == 2

    def test_is_constraint(self):
        """Test is_constraint() method."""
        x = IntegerVar(range(1, 10), name="x")

        # Constraint
        assert (x == 5).is_constraint()
        assert (x <= 5).is_constraint()
        assert (x >= 5).is_constraint()
        assert (x < 5).is_constraint()
        assert (x > 5).is_constraint()

    def test_is_arithmetic(self):
        """Test is_arithmetic() method."""
        x = IntegerVar(range(1, 10), name="x")

        # Arithmetic
        assert (x + 5).is_arithmetic()
        assert (x - 5).is_arithmetic()
        assert (x * 5).is_arithmetic()
        assert (x / 5).is_arithmetic()

        # Not arithmetic
        assert not (x == 5).is_arithmetic()

    def test_collect_variables_simple(self):
        """Test collecting variables from simple expression."""
        x = IntegerVar(range(1, 10), name="x")
        expr = x + 5

        vars = expr.collect_variables()
        assert len(vars) == 1
        assert vars[0] is x

    def test_collect_variables_multiple(self):
        """Test collecting variables from complex expression."""
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")
        z = IntegerVar(range(1, 10), name="z")

        expr = (x + y) * z - 10
        vars = expr.collect_variables()

        assert len(vars) == 3
        assert x in vars
        assert y in vars
        assert z in vars

    def test_collect_variables_duplicates(self):
        """Test that collecting variables doesn't duplicate."""
        x = IntegerVar(range(1, 10), name="x")

        expr = x + x + x

        vars = expr.collect_variables()
        assert len(vars) == 1  # Only one unique variable
        assert vars[0] is x

    def test_expression_with_constants(self):
        """Test expression with Constant objects."""
        x = IntegerVar(range(1, 10), name="x")
        c = Constant(42)

        expr = x + c
        assert expr.operator == "+"

        vars = expr.collect_variables()
        # Constant is a Variable, so it will be collected
        assert len(vars) == 2

    def test_expression_repr(self):
        """Test expression string representation."""
        x = IntegerVar(range(1, 10), name="x")
        expr = x + 5

        repr_str = repr(expr)
        assert "+" in repr_str

    def test_expression_operators_chain(self):
        """Test chaining multiple operators."""
        x = IntegerVar(range(1, 10), name="x")

        # x + 1 - (2 * 3) / 4 due to Python operator precedence
        # The expression is evaluated left to right for same precedence
        # (x + 1) - 2 gives Expression(Expression, "-", 2)
        # Then (Expression) * 3 gives Expression(Expression, "*", 3)
        # Then (Expression) / 4 gives Expression(Expression, "/", 4)
        expr = ((x + 1) - 2) * 3 / 4

        # Should build nested structure
        assert expr.operator == "/"

    def test_expression_comparison_chain(self):
        """Test building constraints from expressions."""
        x = IntegerVar(range(1, 100), name="x")
        y = IntegerVar(range(1, 100), name="y")

        # Build complex constraint from arithmetic expression
        lhs = x + y
        constraint = lhs >= 50

        assert constraint.is_constraint()
        assert constraint.operator == ">="

    def test_negation_expression(self):
        """Test unary negation in expressions."""
        x = IntegerVar(range(1, 10), name="x")
        expr = -x

        assert expr.operator == "-"
        assert expr.left is None
        assert expr.right is x


class TestIntermediate:
    """Tests for Intermediate expressions."""

    def test_intermediate_creation(self):
        """Test creating an intermediate expression."""
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        expr = x * y
        intermediate = Intermediate(expr, name="product")

        assert intermediate.name == "product"
        assert intermediate.left is expr
        assert intermediate.operator == "intermediate"

    def test_intermediate_with_variable(self):
        """Test intermediate wrapping a simple variable."""
        x = IntegerVar(range(1, 100), name="x")
        intermediate = Intermediate(x, name="aux")

        assert intermediate.name == "aux"
        assert intermediate.left is x

    def test_intermediate_repr(self):
        """Test intermediate string representation."""
        x = IntegerVar(range(1, 10), name="x")
        inter = Intermediate(x * 2, name="doubled")

        repr_str = repr(inter)
        assert "Intermediate" in repr_str
        assert "doubled" in repr_str

    def test_intermediate_in_expression(self):
        """Test using intermediate in further expressions."""
        x = IntegerVar(range(1, 100), name="x")
        y = IntegerVar(range(1, 100), name="y")

        # Create intermediate
        sum_xy = Intermediate(x + y, name="sum")

        # Use intermediate in constraint
        constraint = sum_xy >= 50

        assert constraint.is_constraint()
        assert constraint.operator == ">="
