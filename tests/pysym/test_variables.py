"""Tests for pysym Variable types."""

import pytest

from adijif.pysym.variables import (
    BinaryVar,
    Constant,
    ContinuousVar,
    IntegerVar,
    Variable,
)


class TestVariable:
    """Tests for Variable base class."""

    def test_variable_creation(self):
        """Test creating a basic variable."""
        var = Variable(name="test_var")
        assert var.name == "test_var"
        assert var.initial_value is None

    def test_variable_with_initial_value(self):
        """Test variable with initial value."""
        var = Variable(name="test", initial_value=5)
        assert var.initial_value == 5

    def test_variable_repr(self):
        """Test variable string representation."""
        var = Variable(name="x")
        assert "Variable" in repr(var)
        assert "x" in repr(var)


class TestIntegerVar:
    """Tests for IntegerVar."""

    def test_integer_var_with_range(self):
        """Test integer variable with range domain."""
        var = IntegerVar(domain=range(1, 10), name="x")
        assert var.name == "x"
        assert var.domain == range(1, 10)
        assert not var.is_constant

    def test_integer_var_with_list(self):
        """Test integer variable with list domain."""
        domain = [1, 2, 4, 8, 16]
        var = IntegerVar(domain=domain, name="powers")
        assert var.domain == domain
        assert not var.is_constant

    def test_integer_var_constant(self):
        """Test integer variable as constant."""
        var = IntegerVar(domain=42, name="constant_var")
        assert var.is_constant
        assert var.constant_value == 42

    def test_integer_var_single_value_list(self):
        """Test integer variable with single-value list (constant)."""
        var = IntegerVar(domain=[42], name="const")
        assert var.is_constant
        assert var.constant_value == 42

    def test_integer_var_invalid_domain(self):
        """Test integer variable with invalid domain."""
        with pytest.raises(TypeError):
            IntegerVar(domain={1, 2, 3}, name="invalid")

    def test_integer_var_with_initial_value(self):
        """Test integer variable with initial value."""
        var = IntegerVar(domain=range(1, 100), name="x", initial_value=50)
        assert var.initial_value == 50

    def test_integer_var_repr(self):
        """Test integer variable string representation."""
        var = IntegerVar(domain=range(1, 10), name="x")
        assert "IntegerVar" in repr(var)
        assert "x" in repr(var)

    def test_integer_var_domain_with_non_integers(self):
        """Test integer variable rejects non-integer domains."""
        with pytest.raises(AssertionError):
            IntegerVar(domain=[1, 2.5, 4], name="invalid")


class TestBinaryVar:
    """Tests for BinaryVar."""

    def test_binary_var_creation(self):
        """Test creating a binary variable."""
        var = BinaryVar(name="flag")
        assert var.name == "flag"
        assert var.domain == [0, 1]

    def test_binary_var_with_initial_value(self):
        """Test binary variable with initial value."""
        var = BinaryVar(name="flag", initial_value=1)
        assert var.initial_value == 1
        assert var.domain == [0, 1]

    def test_binary_var_repr(self):
        """Test binary variable string representation."""
        var = BinaryVar(name="enabled")
        assert "BinaryVar" in repr(var)
        assert "enabled" in repr(var)


class TestContinuousVar:
    """Tests for ContinuousVar."""

    def test_continuous_var_creation(self):
        """Test creating a continuous variable."""
        var = ContinuousVar(lb=0.0, ub=1.0, name="x")
        assert var.name == "x"
        assert var.lb == 0.0
        assert var.ub == 1.0

    def test_continuous_var_domain_property(self):
        """Test domain property returns bounds tuple."""
        var = ContinuousVar(lb=-10.0, ub=10.0, name="x")
        assert var.domain == (-10.0, 10.0)

    def test_continuous_var_with_initial_value(self):
        """Test continuous variable with initial value."""
        var = ContinuousVar(lb=0.0, ub=100.0, name="freq", initial_value=50.0)
        assert var.initial_value == 50.0

    def test_continuous_var_invalid_bounds(self):
        """Test continuous variable with invalid bounds."""
        with pytest.raises(ValueError):
            ContinuousVar(lb=100.0, ub=0.0, name="invalid")

    def test_continuous_var_repr(self):
        """Test continuous variable string representation."""
        var = ContinuousVar(lb=0.0, ub=1.0, name="x")
        assert "ContinuousVar" in repr(var)
        assert "x" in repr(var)


class TestConstant:
    """Tests for Constant."""

    def test_constant_integer(self):
        """Test creating an integer constant."""
        const = Constant(42)
        assert const.value == 42
        assert const.domain == [42]

    def test_constant_float(self):
        """Test creating a float constant."""
        const = Constant(3.14159)
        assert const.value == 3.14159
        assert const.domain == [3.14159]

    def test_constant_with_name(self):
        """Test constant with explicit name."""
        const = Constant(2.718, name="e")
        assert const.name == "e"
        assert const.value == 2.718

    def test_constant_repr(self):
        """Test constant string representation."""
        const = Constant(42)
        assert "Constant" in repr(const)
        assert "42" in repr(const)


class TestVariableOperators:
    """Tests for Variable operator overloading."""

    def test_addition_operator(self):
        """Test variable + operator."""
        x = IntegerVar(range(1, 10), name="x")
        expr = x + 5
        assert expr is not None
        assert expr.operator == "+"

    def test_subtraction_operator(self):
        """Test variable - operator."""
        x = IntegerVar(range(1, 10), name="x")
        expr = x - 5
        assert expr.operator == "-"

    def test_multiplication_operator(self):
        """Test variable * operator."""
        x = IntegerVar(range(1, 10), name="x")
        expr = x * 2
        assert expr.operator == "*"

    def test_division_operator(self):
        """Test variable / operator."""
        x = IntegerVar(range(1, 10), name="x")
        expr = x / 2
        assert expr.operator == "/"

    def test_equality_operator(self):
        """Test variable == operator."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = x == 5
        assert constraint.operator == "=="

    def test_less_equal_operator(self):
        """Test variable <= operator."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = x <= 5
        assert constraint.operator == "<="

    def test_greater_equal_operator(self):
        """Test variable >= operator."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = x >= 5
        assert constraint.operator == ">="

    def test_less_than_operator(self):
        """Test variable < operator."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = x < 5
        assert constraint.operator == "<"

    def test_greater_than_operator(self):
        """Test variable > operator."""
        x = IntegerVar(range(1, 10), name="x")
        constraint = x > 5
        assert constraint.operator == ">"

    def test_negation_operator(self):
        """Test variable unary negation."""
        x = IntegerVar(range(1, 10), name="x")
        expr = -x
        assert expr.operator == "-"
        assert expr.left is None

    def test_right_addition(self):
        """Test right addition (constant + variable)."""
        x = IntegerVar(range(1, 10), name="x")
        expr = 5 + x
        assert expr.operator == "+"

    def test_right_subtraction(self):
        """Test right subtraction."""
        x = IntegerVar(range(1, 10), name="x")
        expr = 10 - x
        assert expr.operator == "-"

    def test_right_multiplication(self):
        """Test right multiplication."""
        x = IntegerVar(range(1, 10), name="x")
        expr = 3 * x
        assert expr.operator == "*"
