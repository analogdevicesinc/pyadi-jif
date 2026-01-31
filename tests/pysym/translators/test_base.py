"""Tests for BaseTranslator abstract class."""

import pytest

from adijif.pysym.translators.base import BaseTranslator
from adijif.pysym.variables import IntegerVar


class MockTranslator(BaseTranslator):
    """Mock translator for testing."""

    def check_availability(self) -> bool:
        return True

    def build_native_model(self, model):
        return None

    def solve(self, native_model, pysym_model, time_limit=None):
        return None


class TestBaseTranslator:
    """Tests for BaseTranslator."""

    def test_translator_initialization(self):
        """Test translator initialization."""
        translator = MockTranslator("test")
        assert translator.solver_name == "test"

    def test_translator_enforces_abstract_methods(self):
        """Test that abstract methods must be implemented."""

        class IncompleteTranslator(BaseTranslator):
            pass

        with pytest.raises(TypeError):
            IncompleteTranslator("test")

    def test_translator_methods_exist(self):
        """Test that all required methods exist."""
        translator = MockTranslator("test")

        assert hasattr(translator, "check_availability")
        assert hasattr(translator, "build_native_model")
        assert hasattr(translator, "solve")
        assert hasattr(translator, "translate_variable")
        assert hasattr(translator, "translate_expression")
        assert hasattr(translator, "translate_constraint")
        assert hasattr(translator, "translate_objective")

    def test_translator_optional_methods_raise_notimplemented(self):
        """Test that optional methods raise NotImplementedError."""
        translator = MockTranslator("test")

        # These are optional and should raise NotImplementedError
        x = IntegerVar(range(1, 10), name="x")

        with pytest.raises(NotImplementedError):
            translator.translate_variable(x)

        with pytest.raises(NotImplementedError):
            translator.translate_expression(None, {})

        with pytest.raises(NotImplementedError):
            translator.translate_constraint(None, {})

        with pytest.raises(NotImplementedError):
            translator.translate_objective(None, {})
