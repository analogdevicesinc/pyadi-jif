"""Tests for OR-Tools translator.

These tests are for Phase 11 implementation. They are marked as skipped
until the OR-Tools translator is fully implemented.
"""

import pytest

from importlib.util import find_spec

ortools_available = find_spec("ortools") is not None


@pytest.mark.skipif(not ortools_available, reason="OR-Tools not installed")
class TestORToolsTranslator:
    """Tests for OR-Tools translator (Phase 11)."""

    def test_ortools_availability(self):
        """Test OR-Tools translator availability check."""
        from adijif.pysym.translators.registry import get_translator
        translator = get_translator("ortools")
        assert translator.check_availability() is True

    def test_ortools_build_native_model(self):
        """Test building native OR-Tools model."""
        from adijif.pysym import Model, IntegerVar

        model = Model(solver="ortools")

        x = IntegerVar(domain=range(1, 10), name="x")
        y = IntegerVar(domain=range(1, 10), name="y")

        model.add_variable(x)
        model.add_variable(y)

        model.add_constraint(x + y >= 10)
        model.add_objective(x + y, minimize=True)

        # Get translator and build native model
        from adijif.pysym.translators.registry import get_translator
        translator = get_translator("ortools")

        native_model = translator.build_native_model(model)

        # Verify native model was created
        assert native_model is not None

    def test_ortools_solve(self):
        """Test solving with OR-Tools."""
        from adijif.pysym import Model, IntegerVar

        model = Model(solver="ortools")

        x = IntegerVar(domain=range(1, 10), name="x")
        y = IntegerVar(domain=range(1, 10), name="y")

        model.add_variable(x)
        model.add_variable(y)

        model.add_constraint(x + y >= 10)
        model.add_objective(x, minimize=True)

        # Solve
        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        x_val = solution.get_value(x)
        y_val = solution.get_value(y)

        # Check constraint is satisfied
        assert x_val + y_val >= 10

        # Check x is minimized (should be 1)
        assert x_val == 1
