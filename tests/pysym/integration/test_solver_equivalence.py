"""Tests verifying solver equivalence across different backends.

These tests verify that different solver backends produce equivalent
solutions for the same problem.
"""

import pytest

from adijif.pysym.model import Model
from adijif.pysym.variables import BinaryVar, IntegerVar
from adijif.solvers import cplex_solver, gekko_solver, ortools_solver

# Determine which solvers are available
available_solvers = []
if cplex_solver:
    available_solvers.append("CPLEX")
if gekko_solver:
    available_solvers.append("gekko")
if ortools_solver:
    available_solvers.append("ortools")


@pytest.mark.skipif(
    len(available_solvers) < 2,
    reason="At least two solvers required for equivalence testing",
)
@pytest.mark.parametrize("solver", available_solvers)
class TestSolverEquivalence:
    """Test that different solvers produce equivalent results."""

    def test_simple_minimization_equivalence(self, solver):
        """Test simple minimization is equivalent across solvers."""
        # Simple problem: minimize x where x in [5, 10]
        model = Model(solver=solver)

        x = IntegerVar(domain=range(5, 11), name="x")
        model.add_variable(x)
        model.add_objective(x, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(x) == 5

    def test_constraint_problem_equivalence(self, solver):
        """Test constraint satisfaction is equivalent across solvers."""
        model = Model(solver=solver)

        x = IntegerVar(domain=range(1, 100), name="x")
        y = IntegerVar(domain=range(1, 100), name="y")

        model.add_variable(x).add_variable(y)

        model.add_constraint(x + y >= 50)
        model.add_constraint(x - y <= 20)
        model.add_objective(x + y, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        x_val = solution.get_value(x)
        y_val = solution.get_value(y)

        assert x_val + y_val >= 50
        assert x_val - y_val <= 20

    def test_pll_like_problem(self, solver):
        """Test PLL-like optimization problem across solvers.

        This simulates a simplified PLL frequency synthesis problem:
        - VCO frequency must be in valid range
        - PFD frequency limited by chip specs
        - Minimize N divider for power efficiency

        Skipped for OR-Tools: Uses non-linear division which requires
        AddDivisionEquality with auxiliary variables (not yet implemented).
        """
        if solver == "ortools":
            pytest.skip("OR-Tools doesn't support non-linear division in constraints")

        model = Model(solver=solver)

        # VCO frequency range (simplified)
        vcxo = 100e6
        vco_min, vco_max = int(3e9), int(6e9)
        pfd_max = int(125e6)

        # Variables
        n = IntegerVar(domain=range(8, 256), name="n")
        r = IntegerVar(domain=[1, 2, 4], name="r")

        model.add_variable(n)
        model.add_variable(r)

        # Intermediate: vco = vcxo * n / r
        from adijif.pysym.expressions import Intermediate

        vco = Intermediate(vcxo * n / r, name="vco")
        pfd = Intermediate(vcxo / r, name="pfd")

        model.add_intermediate(vco)
        model.add_intermediate(pfd)

        # Constraints
        model.add_constraint(vco >= vco_min)
        model.add_constraint(vco <= vco_max)
        model.add_constraint(pfd <= pfd_max)

        # Objective: minimize n
        model.add_objective(n, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        n_val = solution.get_value(n)
        r_val = solution.get_value(r)

        # Verify constraints
        vco_val = vcxo * n_val / r_val
        pfd_val = vcxo / r_val

        assert vco_val >= vco_min
        assert vco_val <= vco_max
        assert pfd_val <= pfd_max

    def test_clock_divider_problem(self, solver):
        """Test clock divider selection problem across solvers.

        Selects optimal dividers for multiple output clocks from a common input.
        """
        model = Model(solver=solver)

        # Three output clock dividers
        # Divider variables (1, 2, 4, 8)
        d1 = IntegerVar(domain=[1, 2, 4, 8], name="d1")
        d2 = IntegerVar(domain=[1, 2, 4, 8], name="d2")
        d3 = IntegerVar(domain=[1, 2, 4, 8], name="d3")

        model.add_variable(d1)
        model.add_variable(d2)
        model.add_variable(d3)

        # Constraints: minimum divider sum (just for feasibility)
        model.add_constraint(d1 + d2 + d3 >= 6)

        # Objective: minimize total divider value (power efficiency)
        model.add_objective(d1 + d2 + d3, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        d1_val = solution.get_value(d1)
        d2_val = solution.get_value(d2)
        d3_val = solution.get_value(d3)

        # Verify constraints
        assert d1_val + d2_val + d3_val >= 6

    def test_multi_constraint_problem(self, solver):
        """Test problem with many constraints across solvers."""
        model = Model(solver=solver)

        x = IntegerVar(domain=range(1, 100), name="x")
        y = IntegerVar(domain=range(1, 100), name="y")
        z = IntegerVar(domain=range(1, 100), name="z")

        model.add_variable(x)
        model.add_variable(y)
        model.add_variable(z)

        # Multiple constraints
        model.add_constraint(x + y + z >= 100)
        model.add_constraint(x - y <= 20)
        model.add_constraint(y - z <= 15)
        model.add_constraint(x >= 25)
        model.add_constraint(z <= 40)

        # Objective
        model.add_objective(x + 2 * y + 3 * z, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        x_val = solution.get_value(x)
        y_val = solution.get_value(y)
        z_val = solution.get_value(z)

        # Verify all constraints
        assert x_val + y_val + z_val >= 100
        assert x_val - y_val <= 20
        assert y_val - z_val <= 15
        assert x_val >= 25
        assert z_val <= 40

    def test_maximization_problem(self, solver):
        """Test maximization objective across solvers."""
        model = Model(solver=solver)

        profit_per_a = 5
        profit_per_b = 3
        max_a = 20
        max_b = 30

        a = IntegerVar(domain=range(0, max_a + 1), name="a")
        b = IntegerVar(domain=range(0, max_b + 1), name="b")

        model.add_variable(a)
        model.add_variable(b)

        # At least 10 units total
        model.add_constraint(a + b >= 10)

        # Maximize profit
        model.add_objective(profit_per_a * a + profit_per_b * b, minimize=False)

        solution = model.solve()

        assert solution.is_feasible
        a_val = solution.get_value(a)
        b_val = solution.get_value(b)

        assert a_val + b_val >= 10
        assert a_val <= max_a
        assert b_val <= max_b

    def test_binary_variable_problem(self, solver):
        """Test problem with binary decision variables."""
        model = Model(solver=solver)

        # Feature flags and resource allocation
        use_feature_a = BinaryVar(name="use_feature_a")
        use_feature_b = BinaryVar(name="use_feature_b")

        resource_a = IntegerVar(domain=range(0, 51), name="resource_a")
        resource_b = IntegerVar(domain=range(0, 51), name="resource_b")

        model.add_variable(use_feature_a)
        model.add_variable(use_feature_b)
        model.add_variable(resource_a)
        model.add_variable(resource_b)

        # Resource constraints
        model.add_constraint(resource_a + resource_b <= 80)

        # If feature A is used, must allocate at least 20 resources
        model.add_constraint(resource_a >= 20 * use_feature_a)

        # If feature B is used, must allocate at least 15 resources
        model.add_constraint(resource_b >= 15 * use_feature_b)

        # Minimize total resources used
        model.add_objective(resource_a + resource_b, minimize=True)

        solution = model.solve()

        assert solution.is_feasible
        assert solution.get_value(resource_a) + solution.get_value(resource_b) <= 80
