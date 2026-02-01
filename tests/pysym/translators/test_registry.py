"""Tests for translator registry."""

import pytest

from adijif.pysym.translators.base import BaseTranslator
from adijif.pysym.translators.registry import (
    _translators,
    get_translator,
    list_available_translators,
    register_translator,
)


class MockTranslator(BaseTranslator):
    """Mock translator for testing."""

    def check_availability(self) -> bool:
        return True

    def build_native_model(self, model):
        return None

    def solve(self, native_model, pysym_model, time_limit=None):
        return None


class TestTranslatorRegistry:
    """Tests for translator registry."""

    def test_get_translator_cplex(self):
        """Test getting CPLEX translator if available."""
        try:
            translator = get_translator("CPLEX")
            assert translator.solver_name == "CPLEX"
        except ImportError:
            # CPLEX not installed
            pass

    def test_get_translator_gekko(self):
        """Test getting GEKKO translator if available."""
        try:
            translator = get_translator("gekko")
            assert translator.solver_name == "gekko"
        except ImportError:
            # GEKKO not installed
            pass

    def test_get_translator_ortools(self):
        """Test getting OR-Tools translator if available."""
        try:
            translator = get_translator("ortools")
            assert translator.solver_name == "ortools"
        except ImportError:
            # OR-Tools not installed
            pass

    def test_get_translator_invalid(self):
        """Test that invalid solver name raises ValueError."""
        with pytest.raises(ValueError):
            get_translator("invalid_solver")

    def test_get_translator_caches_result(self):
        """Test that get_translator caches results."""
        try:
            t1 = get_translator("CPLEX")
            t2 = get_translator("CPLEX")
            assert t1 is t2  # Should be same instance
        except ImportError:
            pass

    def test_list_available_translators(self):
        """Test listing available translators."""
        available = list_available_translators()

        # Should be a list
        assert isinstance(available, list)

        # Should contain valid solver names
        for solver in available:
            assert solver in ["CPLEX", "gekko", "ortools"]

    def test_register_translator_custom(self):
        """Test registering a custom translator."""
        # Clean up any existing test translator first
        if "test_solver" in _translators:
            del _translators["test_solver"]

        mock_translator = MockTranslator("test_solver")
        register_translator("test_solver", mock_translator)

        # Should be able to retrieve it
        retrieved = get_translator("test_solver")
        assert retrieved is mock_translator
        assert retrieved.solver_name == "test_solver"

        # Clean up
        del _translators["test_solver"]

    def test_register_translator_duplicate_raises(self):
        """Test that registering duplicate translator raises error."""
        # Clean up first
        if "test_dup" in _translators:
            del _translators["test_dup"]

        mock1 = MockTranslator("test_dup")
        mock2 = MockTranslator("test_dup")

        # First registration should work
        register_translator("test_dup", mock1)

        # Second registration should raise
        with pytest.raises(ValueError):
            register_translator("test_dup", mock2)

        # Clean up
        del _translators["test_dup"]
