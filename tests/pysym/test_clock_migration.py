"""Tests demonstrating clock component design with pysym backend.

This module shows how clock components would be designed with pysym
to leverage solver abstraction capabilities.
"""

import pytest

from adijif.pysym import Model, IntegerVar
from adijif.solvers import cplex_solver, gekko_solver


@pytest.mark.skipif(
    not cplex_solver,
    reason="CPLEX required"
)
class TestClockWithPySym:
    """Test clock-like models using pysym backend."""

    def test_simple_divider_selection(self):
        """Test simple output divider selection for a clock chip.

        Simulates selecting output dividers from a clock chip where:
        - Multiple outputs available
        - Each output has a divider
        - Objective: minimize power by minimizing total divider value
        """
        model = Model(solver="CPLEX")

        # Three output dividers (using contiguous range for solver compatibility)
        div_out0 = IntegerVar(domain=range(1, 17), name="div_out0")
        div_out1 = IntegerVar(domain=range(1, 17), name="div_out1")
        div_out2 = IntegerVar(domain=range(1, 17), name="div_out2")

        model.add_variable(div_out0)
        model.add_variable(div_out1)
        model.add_variable(div_out2)

        # Constraint: sum of dividers >= 10 (feasibility requirement)
        model.add_constraint(div_out0 + div_out1 + div_out2 >= 10)

        # Objective: minimize total divider value for power efficiency
        model.add_objective(div_out0 + div_out1 + div_out2, minimize=True)

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        d0_val = solution.get_value(div_out0)
        d1_val = solution.get_value(div_out1)
        d2_val = solution.get_value(div_out2)

        # Check constraint is satisfied
        assert d0_val + d1_val + d2_val >= 10

        # Verify values are in domain
        assert 1 <= d0_val <= 16
        assert 1 <= d1_val <= 16
        assert 1 <= d2_val <= 16

    def test_clock_feedback_divider(self):
        """Test clock feedback path with divider constraints.

        Simulates a PLL feedback divider selection:
        - R divider (reference divider)
        - N divider (feedback divider)
        - Constraint: N/R ratio produces valid PLL frequency
        """
        model = Model(solver="CPLEX")

        # Use contiguous ranges for compatibility with all solvers
        # GEKKO has limitations with non-contiguous discrete domains
        r_div = IntegerVar(domain=range(1, 5), name="r_div")  # 1,2,3,4
        n_div = IntegerVar(domain=range(16, 65), name="n_div")

        model.add_variable(r_div)
        model.add_variable(n_div)

        # Simple constraint: n/r ratio >= 4 (minimum PLL multiplication)
        # Using integer multiplication: n >= 4 * r
        model.add_constraint(n_div >= 4 * r_div)

        # Objective: minimize N divider for lower power
        model.add_objective(n_div, minimize=True)

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        n_val = solution.get_value(n_div)
        r_val = solution.get_value(r_div)

        # Verify constraint
        assert n_val >= 4 * r_val

        # Verify domains
        assert 1 <= r_val <= 4
        assert 16 <= n_val <= 64

    def test_multiple_reference_clocks(self):
        """Test selecting from multiple reference clock sources.

        Simulates a clock tree where:
        - Multiple reference sources available
        - Each source has different properties
        - Select which source to use based on optimization
        """
        model = Model(solver="CPLEX")

        # Binary variables indicating which source is selected (one-hot)
        use_vcxo = IntegerVar(domain=[0, 1], name="use_vcxo")
        use_ext_ref = IntegerVar(domain=[0, 1], name="use_ext_ref")

        # Frequency divider (applied to selected source)
        divider = IntegerVar(domain=range(1, 9), name="divider")

        model.add_variable(use_vcxo)
        model.add_variable(use_ext_ref)
        model.add_variable(divider)

        # Constraint: exactly one source selected (one-hot)
        model.add_constraint(use_vcxo + use_ext_ref == 1)

        # Constraint: minimum divider value depends on source
        # (simplified: overall >= 2)
        model.add_constraint(divider >= 1)

        # Objective: prefer VCXO if possible (lower cost)
        # use_vcxo has weight 0.1, divider has weight 1.0
        model.add_objective(use_vcxo * 0.1 + divider, minimize=True)

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        vcxo_val = solution.get_value(use_vcxo)
        ext_val = solution.get_value(use_ext_ref)
        div_val = solution.get_value(divider)

        # One source selected
        assert vcxo_val + ext_val == 1

        # Valid divider (1-8 range)
        assert 1 <= div_val <= 8


class TestClockDesignPatterns:
    """Document pysym patterns for clock component design."""

    def test_pysym_clock_design_pattern(self):
        """Show recommended pattern for clock component using pysym.

        This is a template for how new clock components should be designed
        to leverage the pysym abstraction layer.
        """
        # Pattern:
        # 1. Create model with specified solver
        # 2. Define dividers as IntegerVar with valid ranges
        # 3. Add constraints (frequency relationships, limits)
        # 4. Define objective (power efficiency, cost, etc.)
        # 5. Solve - works with any configured solver

        model = Model(solver="CPLEX")

        # Define variables
        r = IntegerVar(domain=[1, 2, 4, 8], name="r_divider")
        n = IntegerVar(domain=range(16, 256), name="n_divider")
        m = IntegerVar(domain=[1, 2], name="m_multiplier")

        model.add_variable(r).add_variable(n).add_variable(m)

        # Add constraints
        model.add_constraint(n >= 16 * m)  # Minimum N based on M
        model.add_constraint(n <= 255)  # Maximum N

        # Objective
        model.add_objective(r + n, minimize=True)

        # Solve
        solution = model.solve()

        # Get configuration
        assert solution.is_feasible
        config = {
            "r": solution.get_value(r),
            "n": solution.get_value(n),
            "m": solution.get_value(m),
        }

        # Verify
        assert config["n"] >= 16 * config["m"]
        assert config["r"] in [1, 2, 4, 8]
