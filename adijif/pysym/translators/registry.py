"""Translator registry for solver plugin management."""

from typing import Dict, Optional, Type

from adijif.pysym.translators.base import BaseTranslator

# Global registry of translators
_translators: Dict[str, BaseTranslator] = {}


def register_translator(solver_name: str, translator: BaseTranslator) -> None:
    """Register a translator for a solver.

    Args:
        solver_name: Name of the solver (CPLEX, gekko, ortools, etc.)
        translator: Translator instance (subclass of BaseTranslator)

    Raises:
        ValueError: If translator already registered for this solver
    """
    if solver_name in _translators:
        raise ValueError(f"Translator already registered for {solver_name}")

    _translators[solver_name] = translator


def get_translator(solver_name: str) -> BaseTranslator:
    """Get translator for a specific solver.

    Lazily loads and registers translators on first use to avoid
    circular imports and dependency issues.

    Args:
        solver_name: Name of the solver (CPLEX, gekko, ortools, etc.)

    Returns:
        Translator instance for the solver

    Raises:
        ValueError: If solver name is invalid
        ImportError: If required solver not installed
    """
    if solver_name in _translators:
        return _translators[solver_name]

    # Lazy load translators
    if solver_name == "CPLEX":
        from adijif.pysym.translators.cplex_translator import CPLEXTranslator

        translator = CPLEXTranslator()
        if not translator.check_availability():
            raise ImportError(
                "CPLEX solver not installed. "
                "Install with: pip install pyadi-jif[cplex]"
            )
        _translators[solver_name] = translator
        return translator

    elif solver_name == "gekko":
        from adijif.pysym.translators.gekko_translator import GEKKOTranslator

        translator = GEKKOTranslator()
        if not translator.check_availability():
            raise ImportError(
                "GEKKO solver not installed. "
                "Install with: pip install pyadi-jif[gekko]"
            )
        _translators[solver_name] = translator
        return translator

    elif solver_name == "ortools":
        from adijif.pysym.translators.ortools_translator import ORToolsTranslator

        translator = ORToolsTranslator()
        if not translator.check_availability():
            raise ImportError(
                "OR-Tools solver not installed. "
                "Install with: pip install pyadi-jif[ortools]"
            )
        _translators[solver_name] = translator
        return translator

    else:
        raise ValueError(f"Unknown solver: {solver_name}")


def list_available_translators() -> list:
    """List all available solvers.

    Returns:
        List of solver names that have installed backends
    """
    available = []

    for solver_name in ["CPLEX", "gekko", "ortools"]:
        try:
            translator = get_translator(solver_name)
            if translator.check_availability():
                available.append(solver_name)
        except ImportError:
            pass

    return available
