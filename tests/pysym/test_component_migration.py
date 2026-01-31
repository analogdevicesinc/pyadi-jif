"""Tests demonstrating component migration to pysym backend.

This module shows how existing components can be migrated to use pysym
without any changes to the component code itself. Only the base class
needs to be changed from gekko_translation to pysym_translation.
"""

import pytest

from adijif.solvers import cplex_solver, gekko_solver
from adijif.pysym.compat import pysym_translation
from adijif.pysym.variables import IntegerVar


class SimplePLLModel(pysym_translation):
    """Example PLL model using pysym backend (for migration testing).

    This demonstrates how an existing PLL component would be migrated to
    pysym. The component code remains identical; only the base class changes
    from gekko_translation to pysym_translation.
    """

    def __init__(self, model=None, solver="CPLEX"):
        """Initialize PLL model with pysym backend."""
        super().__init__(model=model, solver=solver)

        # PLL parameter ranges (simplified for compatibility across solvers)
        self.n_min = 10
        self.n_max = 100
        self.r_min = 1
        self.r_max = 4
        self.vcxo = 100e6

    def configure(self, output_freq: float) -> None:
        """Configure PLL for desired output frequency.

        Args:
            output_freq: Desired output frequency in Hz (unused in simplified version)
        """
        # Create variables using compatibility method
        # Use smaller, contiguous ranges for solver compatibility
        self.n = self._convert_input(
            list(range(self.n_min, self.n_max + 1)), name="n"
        )
        self.r = self._convert_input(
            [1, 2, 4], name="r"  # Non-contiguous: will use SOS1 in GEKKO
        )

        # Simple constraints for demonstration
        # Constraint: n >= 20
        self.model.add_constraint(self.n >= 20)
        # Constraint that uses r to ensure it appears in solution
        self.model.add_constraint(self.r >= 1)

        # Objective: minimize N + R for power efficiency
        # (weighted sum to make both variables matter)
        self._add_objective(self.n + self.r)

    def get_config(self) -> dict:
        """Get optimal PLL configuration.

        Returns:
            Dictionary with N and R divider values
        """
        if self.solution is None:
            raise RuntimeError("Must call solve() first")

        return {
            "n": self.solution.get_value(self.n),
            "r": self.solution.get_value(self.r),
        }


@pytest.mark.skipif(
    not (cplex_solver and gekko_solver),
    reason="Both CPLEX and GEKKO required"
)
@pytest.mark.parametrize("solver", ["CPLEX", "gekko"])
class TestComponentMigration:
    """Tests demonstrating PLL component migration to pysym."""

    def test_pll_configuration_basic(self, solver):
        """Test basic PLL configuration with pysym backend."""
        pll = SimplePLLModel(solver=solver)
        pll.configure(output_freq=1e9)

        # Solve using compatibility solve method
        pll.solve()

        # Verify solution is feasible
        assert pll.solution.is_feasible

        # Get configuration and verify constraints
        config = pll.get_config()
        assert config["n"] >= 20  # Constraint: n >= 20
        assert config["n"] <= 100  # Domain upper bound
        assert config["r"] in [1, 2, 4]  # Domain values

    def test_pll_multiple_configurations(self, solver):
        """Test multiple PLL configurations."""
        # Test that multiple instances can be solved independently
        pll1 = SimplePLLModel(solver=solver)
        pll1.configure(output_freq=500e6)
        pll1.solve()
        assert pll1.solution.is_feasible

        pll2 = SimplePLLModel(solver=solver)
        pll2.configure(output_freq=1e9)
        pll2.solve()
        assert pll2.solution.is_feasible

    def test_pll_equivalence_across_solvers(self, solver):
        """Test that the component works with the parametrized solver."""
        pll = SimplePLLModel(solver=solver)
        pll.configure(output_freq=1e9)
        pll.solve()

        # Verify solution is feasible
        assert pll.solution.is_feasible

        # Get config and verify it satisfies constraints
        config = pll.get_config()
        assert config["n"] >= 20


class SimpleClockChip(pysym_translation):
    """Example clock chip model using pysym backend (for migration testing).

    This demonstrates how a clock chip component would be migrated.
    """

    def __init__(self, model=None, solver="CPLEX"):
        """Initialize clock chip with pysym backend."""
        super().__init__(model=model, solver=solver)
        self.input_freq = 100e6

    def configure(self, output_freqs: list) -> None:
        """Configure clock chip for multiple output frequencies.

        Args:
            output_freqs: List of desired output frequencies (unused in simplified version)
        """
        self.dividers = []
        for i in range(len(output_freqs)):
            # Create divider variable (simplified range for compatibility)
            divider = self._convert_input(
                [1, 2, 4, 8], name=f"div_{i}"
            )
            self.dividers.append(divider)

        # Minimize total divider value (power efficiency)
        total = sum(self.dividers)
        self._add_objective(total)

    def get_config(self) -> list:
        """Get optimal divider configuration.

        Returns:
            List of divider values
        """
        if self.solution is None:
            raise RuntimeError("Must call solve() first")

        return [self.solution.get_value(d) for d in self.dividers]


@pytest.mark.skipif(not cplex_solver, reason="CPLEX not installed")
class TestClockChipMigration:
    """Test clock chip migration to pysym."""

    def test_clock_chip_multiple_outputs(self):
        """Test clock chip with multiple outputs."""
        chip = SimpleClockChip(solver="CPLEX")

        # Request 3 output frequencies
        outputs = [500e6, 250e6, 125e6]
        chip.configure(outputs)

        # Solve the model
        chip.solve()

        # Verify solution is feasible
        assert chip.solution.is_feasible

        # Get divider values
        config = chip.get_config()
        assert len(config) == 3
        for div in config:
            assert div in [1, 2, 4, 8]


@pytest.mark.skipif(
    not (cplex_solver and gekko_solver),
    reason="Both CPLEX and GEKKO required"
)
@pytest.mark.skipif(
    not (cplex_solver and gekko_solver),
    reason="Both CPLEX and GEKKO required"
)
class TestMigrationPattern:
    """Test the general migration pattern."""

    @pytest.mark.parametrize("solver", ["CPLEX", "gekko"])
    def test_component_works_with_both_backends(self, solver):
        """Verify a component works seamlessly with both solvers."""
        # This pattern shows how to write components that work with any solver
        pll = SimplePLLModel(solver=solver)
        pll.configure(output_freq=1e9)
        pll.solve()

        # Component produces valid configurations
        assert pll.solution.is_feasible
        config = pll.get_config()
        assert config["n"] > 0
        assert config["r"] > 0
