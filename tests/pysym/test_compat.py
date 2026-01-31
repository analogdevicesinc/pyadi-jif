"""Tests for backward compatibility layer."""

import pytest

from adijif.pysym.compat import pysym_translation
from adijif.pysym.variables import Constant, IntegerVar
from adijif.solvers import cplex_solver, gekko_solver


class TestPySymTranslation:
    """Tests for pysym_translation compatibility class."""

    def test_initialization_default(self):
        """Test initialization with default solver."""
        trans = pysym_translation()
        assert trans.solver == "CPLEX"
        assert trans.model is not None

    def test_initialization_with_solver(self):
        """Test initialization with specific solver."""
        trans = pysym_translation(solver="gekko")
        assert trans.solver == "gekko"

    def test_convert_input_constant(self):
        """Test converting single value to constant."""
        trans = pysym_translation()
        const = trans._convert_input(42, name="answer")
        assert isinstance(const, Constant)
        assert const.value == 42

    def test_convert_input_single_value_list(self):
        """Test converting single-value list to constant."""
        trans = pysym_translation()
        const = trans._convert_input([42], name="single")
        assert isinstance(const, Constant)
        assert const.value == 42

    def test_convert_input_domain_list(self):
        """Test converting list to IntegerVar domain."""
        trans = pysym_translation()
        var = trans._convert_input([1, 2, 4, 8], name="powers")
        assert isinstance(var, IntegerVar)
        assert var.domain == [1, 2, 4, 8]

    def test_add_equation_single(self):
        """Test adding single constraint."""
        trans = pysym_translation()
        x = IntegerVar(range(1, 10), name="x")
        trans._convert_input([1, 2, 4, 8], name="x")  # Register variable
        constraint = x >= 5
        trans._add_equation(constraint)
        assert len(trans.model.constraints) == 1

    def test_add_equation_multiple(self):
        """Test adding multiple constraints."""
        trans = pysym_translation()
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        trans.model.add_variable(x)
        trans.model.add_variable(y)

        constraints = [x >= 5, y <= 8]
        trans._add_equation(constraints)
        assert len(trans.model.constraints) == 2

    def test_add_objective_single(self):
        """Test adding single objective."""
        trans = pysym_translation()
        x = IntegerVar(range(1, 10), name="x")
        trans.model.add_variable(x)
        trans._add_objective(x)
        assert len(trans.model.objectives) == 1

    def test_add_objective_multiple(self):
        """Test adding multiple objectives (lexicographic)."""
        trans = pysym_translation()
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")
        trans.model.add_variable(x)
        trans.model.add_variable(y)
        trans._add_objective([x, y])
        assert len(trans.model.lexicographic_objectives) == 1

    def test_check_in_range_valid(self):
        """Test range checking with valid value."""
        trans = pysym_translation()
        # Should not raise
        trans._check_in_range(5, [1, 2, 5, 10], "test_var")

    def test_check_in_range_invalid(self):
        """Test range checking with invalid value."""
        trans = pysym_translation()
        with pytest.raises(ValueError):
            trans._check_in_range(7, [1, 2, 5, 10], "test_var")

    def test_get_val_constant(self):
        """Test extracting constant value."""
        trans = pysym_translation()
        val = trans._get_val(42)
        assert val == 42

    def test_get_val_float(self):
        """Test extracting float value."""
        trans = pysym_translation()
        val = trans._get_val(3.14)
        assert val == 3.14

    @pytest.mark.skipif(not cplex_solver, reason="CPLEX not installed")
    def test_solve_simple_problem(self):
        """Test solving simple problem through compatibility layer."""
        trans = pysym_translation(solver="CPLEX")

        x = IntegerVar(range(1, 10), name="x")
        trans.model.add_variable(x)
        trans.model.add_constraint(x >= 5)
        trans._add_objective(x)

        trans.solve()

        assert trans.solution.is_feasible
        assert trans.solution.get_value(x) == 5

    @pytest.mark.skipif(not cplex_solver, reason="CPLEX not installed")
    def test_convert_and_solve(self):
        """Test using _convert_input and solving."""
        trans = pysym_translation(solver="CPLEX")

        # Use compatibility method
        x = trans._convert_input([1, 2, 4, 8], name="x")
        trans.model.add_constraint(x >= 4)
        trans._add_objective(x)

        trans.solve()

        assert trans.solution.is_feasible

    def test_get_variable(self):
        """Test retrieving registered variable."""
        trans = pysym_translation()
        trans._convert_input([1, 2, 4, 8], name="x")
        retrieved = trans.get_variable("x")
        assert retrieved is not None
        assert retrieved.name == "x"

    def test_get_variables(self):
        """Test retrieving all variables."""
        trans = pysym_translation()
        trans._convert_input([1, 2, 4, 8], name="x")
        trans._convert_input([1, 2, 4], name="y")

        variables = trans.get_variables()
        assert len(variables) >= 2
        assert "x" in variables
        assert "y" in variables


@pytest.mark.skipif(
    not (cplex_solver and gekko_solver),
    reason="Both CPLEX and GEKKO required"
)
@pytest.mark.parametrize("solver", ["CPLEX", "gekko"])
class TestCompatibilityEquivalence:
    """Test that compatibility layer works with both solvers."""

    def test_simple_problem(self, solver):
        """Test simple problem through compatibility layer."""
        trans = pysym_translation(solver=solver)

        x = IntegerVar(range(1, 100), name="x")
        y = IntegerVar(range(1, 100), name="y")

        trans.model.add_variable(x)
        trans.model.add_variable(y)

        trans.model.add_constraint(x + y >= 50)
        trans._add_objective(x)

        trans.solve()

        assert trans.solution.is_feasible
        x_val = trans.solution.get_value(x)
        y_val = trans.solution.get_value(y)
        assert x_val + y_val >= 50

    def test_convert_input_workflow(self, solver):
        """Test workflow using _convert_input."""
        trans = pysym_translation(solver=solver)

        # Register variables through _convert_input
        x = trans._convert_input([1, 2, 4, 8], name="x")
        y = trans._convert_input([1, 2, 4, 8], name="y")

        trans.model.add_constraint(x + y >= 10)
        trans._add_objective(x)

        trans.solve()

        assert trans.solution.is_feasible
