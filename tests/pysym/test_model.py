"""Tests for pysym Model class."""

import pytest

from adijif.pysym.expressions import Intermediate
from adijif.pysym.model import Model
from adijif.pysym.variables import BinaryVar, IntegerVar


class TestModelCreation:
    """Tests for Model creation and initialization."""

    def test_model_default_solver(self):
        """Test model creation with default solver."""
        model = Model()
        assert model.solver == "CPLEX"

    def test_model_with_gekko_solver(self):
        """Test model creation with GEKKO solver."""
        model = Model(solver="gekko")
        assert model.solver == "gekko"

    def test_model_with_ortools_solver(self):
        """Test model creation with OR-Tools solver."""
        model = Model(solver="ortools")
        assert model.solver == "ortools"

    def test_model_invalid_solver(self):
        """Test model rejects invalid solver."""
        with pytest.raises(ValueError):
            Model(solver="invalid")

    def test_model_empty_initialization(self):
        """Test model initializes empty."""
        model = Model()
        assert len(model.variables) == 0
        assert len(model.constraints) == 0
        assert len(model.objectives) == 0
        assert len(model.intermediates) == 0


class TestModelVariables:
    """Tests for adding variables to Model."""

    def test_add_single_variable(self):
        """Test adding a single variable."""
        model = Model()
        x = IntegerVar(range(1, 10), name="x")
        model.add_variable(x)

        assert len(model.variables) == 1
        assert model.variables[0] is x

    def test_add_multiple_variables(self):
        """Test adding multiple variables."""
        model = Model()
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        model.add_variable(x).add_variable(y)

        assert len(model.variables) == 2

    def test_method_chaining(self):
        """Test method chaining with add_variable."""
        model = Model()
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        result = model.add_variable(x).add_variable(y)

        assert result is model

    def test_add_variable_duplicate_name(self):
        """Test that duplicate variable names are rejected."""
        model = Model()
        x1 = IntegerVar(range(1, 10), name="x")
        x2 = IntegerVar(range(1, 20), name="x")

        model.add_variable(x1)

        with pytest.raises(ValueError):
            model.add_variable(x2)

    def test_add_invalid_variable(self):
        """Test that non-Variable objects are rejected."""
        model = Model()

        with pytest.raises(TypeError):
            model.add_variable("not_a_variable")

    def test_get_variables_all(self):
        """Test getting all variables."""
        model = Model()
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        model.add_variable(x).add_variable(y)

        vars = model.get_variables()
        assert len(vars) == 2

    def test_get_variable_by_name(self):
        """Test getting variable by name."""
        model = Model()
        x = IntegerVar(range(1, 10), name="x")
        model.add_variable(x)

        retrieved = model.get_variable_by_name("x")
        assert retrieved is x

    def test_get_variable_by_name_not_found(self):
        """Test getting non-existent variable by name."""
        model = Model()

        retrieved = model.get_variable_by_name("nonexistent")
        assert retrieved is None


class TestModelConstraints:
    """Tests for adding constraints to Model."""

    def test_add_constraint_from_expression(self):
        """Test adding constraint from expression."""
        model = Model()
        x = IntegerVar(range(1, 10), name="x")
        model.add_variable(x)

        expr = x >= 5
        model.add_constraint(expr)

        assert len(model.constraints) == 1

    def test_add_multiple_constraints(self):
        """Test adding multiple constraints."""
        model = Model()
        x = IntegerVar(range(1, 10), name="x")
        y = IntegerVar(range(1, 10), name="y")

        model.add_variable(x).add_variable(y)
        model.add_constraint(x >= 5)
        model.add_constraint(y <= 8)
        model.add_constraint(x + y >= 10)

        assert len(model.constraints) == 3

    def test_add_constraint_invalid_expression(self):
        """Test that arithmetic expressions are rejected as constraints."""
        model = Model()
        x = IntegerVar(range(1, 10), name="x")
        model.add_variable(x)

        # x + 5 is arithmetic, not a constraint
        with pytest.raises(ValueError):
            model.add_constraint(x + 5)

    def test_add_constraint_invalid_type(self):
        """Test that non-Expression/Constraint objects are rejected."""
        model = Model()

        with pytest.raises(TypeError):
            model.add_constraint("not_a_constraint")

    def test_add_conditional_constraint(self):
        """Test adding conditional constraint."""
        model = Model()
        use_feature = BinaryVar(name="use_feature")
        value = IntegerVar(range(1, 100), name="value")

        model.add_variable(use_feature).add_variable(value)

        condition = use_feature == 1
        consequent = value >= 50

        model.add_conditional_constraint(condition, consequent)

        assert len(model.conditional_constraints) == 1


class TestModelObjectives:
    """Tests for adding objectives to Model."""

    def test_add_single_objective(self):
        """Test adding a single objective."""
        model = Model()
        x = IntegerVar(range(1, 10), name="x")
        model.add_variable(x)

        model.add_objective(x, minimize=True)

        assert len(model.objectives) == 1

    def test_add_objective_with_name(self):
        """Test adding objective with name."""
        model = Model()
        x = IntegerVar(range(1, 10), name="x")
        model.add_variable(x)

        model.add_objective(x, minimize=True, name="minimize_x")

        assert model.objectives[0].name == "minimize_x"

    def test_add_objective_from_expression(self):
        """Test adding objective from arithmetic expression."""
        model = Model()
        x = IntegerVar(range(1, 100), name="x")
        y = IntegerVar(range(1, 100), name="y")

        model.add_variable(x).add_variable(y)

        expr = x * 2 + y
        model.add_objective(expr, minimize=True)

        assert len(model.objectives) == 1

    def test_add_objective_with_weight(self):
        """Test adding objective with weight."""
        model = Model()
        x = IntegerVar(range(1, 10), name="x")
        model.add_variable(x)

        model.add_objective(x, minimize=True, weight=2.0)

        assert model.objectives[0].weight == 2.0

    def test_add_lexicographic_objective(self):
        """Test adding lexicographic multi-objective."""
        model = Model()
        x = IntegerVar(range(1, 100), name="x")
        y = IntegerVar(range(1, 100), name="y")

        model.add_variable(x).add_variable(y)

        objectives = [
            (x, True),
            (y, True),
        ]

        model.add_lexicographic_objective(objectives)

        assert len(model.lexicographic_objectives) == 1
        assert len(model.lexicographic_objectives[0].objectives) == 2


class TestModelIntermediates:
    """Tests for adding intermediate expressions."""

    def test_add_intermediate(self):
        """Test adding an intermediate expression."""
        model = Model()
        x = IntegerVar(range(1, 100), name="x")
        y = IntegerVar(range(1, 100), name="y")

        model.add_variable(x).add_variable(y)

        product = Intermediate(x * y, name="product")
        model.add_intermediate(product)

        assert len(model.intermediates) == 1

    def test_add_multiple_intermediates(self):
        """Test adding multiple intermediates."""
        model = Model()
        x = IntegerVar(range(1, 100), name="x")

        model.add_variable(x)

        inter1 = Intermediate(x * 2, name="doubled")
        inter2 = Intermediate(x + 10, name="plus_ten")

        model.add_intermediate(inter1).add_intermediate(inter2)

        assert len(model.intermediates) == 2

    def test_add_invalid_intermediate(self):
        """Test that non-Intermediate objects are rejected."""
        model = Model()

        with pytest.raises(TypeError):
            model.add_intermediate("not_intermediate")


class TestModelProperties:
    """Tests for Model properties and methods."""

    def test_model_repr(self):
        """Test model string representation."""
        model = Model(solver="CPLEX")
        x = IntegerVar(range(1, 10), name="x")

        model.add_variable(x)
        model.add_constraint(x >= 5)
        model.add_objective(x, minimize=True)

        repr_str = repr(model)
        assert "Model" in repr_str
        assert "CPLEX" in repr_str
        assert "vars=1" in repr_str

    def test_model_solver_attribute(self):
        """Test that solver attribute is stored."""
        for solver in ["CPLEX", "gekko", "ortools"]:
            model = Model(solver=solver)
            assert model.solver == solver


class TestModelIntegration:
    """Integration tests for Model building."""

    def test_build_simple_optimization_problem(self):
        """Test building a simple optimization problem."""
        model = Model(solver="CPLEX")

        # Variables
        x = IntegerVar(domain=range(1, 10), name="x")
        y = IntegerVar(domain=range(1, 10), name="y")

        # Add to model
        model.add_variable(x)
        model.add_variable(y)

        # Constraints
        model.add_constraint(x + y >= 10)
        model.add_constraint(x - y <= 5)

        # Objective
        model.add_objective(x, minimize=True)

        # Verify structure
        assert len(model.variables) == 2
        assert len(model.constraints) == 2
        assert len(model.objectives) == 1

    def test_build_complex_problem(self):
        """Test building a complex optimization problem."""
        model = Model(solver="CPLEX")

        # Variables
        x = IntegerVar(domain=range(1, 100), name="x")
        y = IntegerVar(domain=range(1, 100), name="y")
        z = IntegerVar(domain=[1, 2, 4, 8], name="z")
        use_z = BinaryVar(name="use_z")

        # Add to model
        for var in [x, y, z, use_z]:
            model.add_variable(var)

        # Intermediates
        product = Intermediate(x * z, name="product")
        model.add_intermediate(product)

        # Constraints
        model.add_constraint(x + y >= 50)
        model.add_constraint(product <= 1000)
        model.add_conditional_constraint(
            condition=(use_z == 1),
            consequent=(z >= 4)
        )

        # Objectives
        model.add_objective(x, minimize=True, weight=2.0)
        model.add_objective(y, minimize=True, weight=1.0)

        # Verify structure
        assert len(model.variables) == 4
        assert len(model.constraints) == 2
        assert len(model.conditional_constraints) == 1
        assert len(model.intermediates) == 1
        assert len(model.objectives) == 2
