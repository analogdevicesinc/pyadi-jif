"""Tests for type protocols and definitions."""

from adijif.pysym.types import Domain, SolverExpression
from adijif.pysym.variables import IntegerVar


def test_domain_type_alias_range():
    """Test Domain type alias with range."""
    domain: Domain = range(1, 10)
    assert isinstance(domain, range)
    assert domain.start == 1
    assert domain.stop == 10


def test_domain_type_alias_list():
    """Test Domain type alias with list."""
    domain: Domain = [1, 2, 4, 8]
    assert isinstance(domain, list)
    assert len(domain) == 4


def test_domain_type_alias_int():
    """Test Domain type alias with single int."""
    domain: Domain = 42
    assert isinstance(domain, int)
    assert domain == 42


def test_domain_type_alias_float():
    """Test Domain type alias with float."""
    domain: Domain = 3.14
    assert isinstance(domain, float)
    assert domain == 3.14


def test_solver_variable_protocol_arithmetic():
    """Test SolverVariable protocol - arithmetic operators."""
    # Create a variable that should implement the protocol
    var = IntegerVar(domain=range(1, 10), name="x")

    # Test that it has the required arithmetic operators
    assert hasattr(var, "__add__")
    assert hasattr(var, "__sub__")
    assert hasattr(var, "__mul__")
    assert hasattr(var, "__truediv__")

    # Test that operations return something (not necessarily SolverVariable)
    result_add = var + 5
    result_sub = var - 5
    result_mul = var * 2
    result_div = var / 2

    # All should return non-None
    assert result_add is not None
    assert result_sub is not None
    assert result_mul is not None
    assert result_div is not None


def test_solver_variable_protocol_comparison():
    """Test SolverVariable protocol - comparison operators."""
    var = IntegerVar(domain=range(1, 10), name="x")

    # Test that it has the required comparison operators
    assert hasattr(var, "__eq__")
    assert hasattr(var, "__le__")
    assert hasattr(var, "__ge__")
    assert hasattr(var, "__lt__")
    assert hasattr(var, "__gt__")

    # Test that comparisons return something
    eq_result = var == 5
    le_result = var <= 5
    ge_result = var >= 5
    lt_result = var < 5
    gt_result = var > 5

    # All should return non-None
    assert eq_result is not None
    assert le_result is not None
    assert ge_result is not None
    assert lt_result is not None
    assert gt_result is not None


def test_solver_expression_protocol():
    """Test SolverExpression protocol exists."""
    # SolverExpression is a minimal protocol (just a pass)
    # Verify it exists and can be used for type hints
    assert SolverExpression is not None

    # Create an expression and verify it can be treated as an expression
    from adijif.pysym.expressions import Expression

    var = IntegerVar(domain=range(1, 10), name="x")
    expr = var + 5

    # Should be an Expression
    assert isinstance(expr, Expression)
