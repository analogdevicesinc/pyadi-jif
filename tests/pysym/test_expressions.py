"""Tests for pysym Expression and Intermediate."""


from adijif.pysym.expressions import Expression, Intermediate
from adijif.pysym.variables import Constant, IntegerVar


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


class TestExpressionOperators:
    """Tests for right-side operators and edge cases."""

    def test_radd_operator(self):
        """Test right-side addition (constant + variable)."""
        x = IntegerVar(range(1, 10), name="x")
        expr = 5 + x

        assert expr.operator == "+"
        assert expr.left == 5
        assert expr.right is x

    def test_rsub_operator(self):
        """Test right-side subtraction (constant - variable)."""
        x = IntegerVar(range(1, 10), name="x")
        expr = 10 - x

        assert expr.operator == "-"
        assert expr.left == 10
        assert expr.right is x

    def test_rmul_operator(self):
        """Test right-side multiplication (constant * variable)."""
        x = IntegerVar(range(1, 10), name="x")
        expr = 3 * x

        assert expr.operator == "*"
        assert expr.left == 3
        assert expr.right is x

    def test_rtruediv_operator(self):
        """Test right-side division (constant / variable)."""
        x = IntegerVar(range(1, 10), name="x")
        expr = 20 / x

        assert expr.operator == "/"
        assert expr.left == 20
        assert expr.right is x

    def test_neg_operator(self):
        """Test unary negation operator."""
        x = IntegerVar(range(1, 10), name="x")
        expr = -x

        assert expr.operator == "-"
        assert expr.left is None
        assert expr.right is x

    def test_not_equal_operator(self):
        """Test not-equal comparison operator."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = x != 5

        assert constraint.is_constraint()
        assert constraint.operator == "!="

    def test_less_than_operator(self):
        """Test less-than comparison operator."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = x < 5

        assert constraint.is_constraint()
        assert constraint.operator == "<"

    def test_greater_than_operator(self):
        """Test greater-than comparison operator."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = x > 5

        assert constraint.is_constraint()
        assert constraint.operator == ">"

    def test_collect_variables_from_negation(self):
        """Test collecting variables from negated expression."""
        x = IntegerVar(range(1, 10), name="x")
        expr = -x

        vars = expr.collect_variables()
        assert len(vars) == 1
        assert vars[0] is x

    def test_expression_with_all_right_operators(self):
        """Test expression built with all right-side operators."""
        x = IntegerVar(range(1, 20), name="x")

        # 10 + x * 2 - y (would need y, so just test with constants)
        expr = 10 + x
        assert expr.operator == "+"
        expr = 10 - expr
        assert expr.operator == "-"
        expr = 2 * expr
        assert expr.operator == "*"

    def test_not_equal_in_collect_variables(self):
        """Test that != operator works in variable collection."""
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        constraint = x != y
        vars = constraint.collect_variables()

        assert len(vars) == 2
        assert x in vars
        assert y in vars

    def test_less_than_collect_variables(self):
        """Test < operator in variable collection."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = x < 5
        vars = constraint.collect_variables()

        assert len(vars) == 1
        assert x in vars

    def test_greater_than_collect_variables(self):
        """Test > operator in variable collection."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = x > 3
        vars = constraint.collect_variables()

        assert len(vars) == 1
        assert x in vars

    def test_expression_left_variable_repr(self):
        """Test repr with variable on left side."""
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        expr = x + y
        repr_str = repr(expr)

        # Should contain variable names
        assert "x" in repr_str or "+" in repr_str
        assert isinstance(repr_str, str)

    def test_expression_right_variable_repr(self):
        """Test repr with variable on right side."""
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        expr = x * y
        repr_str = repr(expr)

        # Should be a valid string representation
        assert isinstance(repr_str, str)
        assert "*" in repr_str
