"""Base translator abstract class."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from adijif.pysym.model import Model
from adijif.pysym.solution import Solution
from adijif.pysym.variables import Variable


class BaseTranslator(ABC):
    """Abstract base class for solver translators.

    Each solver backend (CPLEX, GEKKO, OR-Tools, etc.) implements a translator
    that converts pysym models to the native solver format.

    Subclasses must implement all abstract methods to support compiling and
    solving pysym models with their specific solver backend.
    """

    def __init__(self, solver_name: str):
        """Initialize translator.

        Args:
            solver_name: Name of the solver (CPLEX, gekko, ortools, etc.)
        """
        self.solver_name = solver_name

    @abstractmethod
    def check_availability(self) -> bool:
        """Check if the required solver is installed.

        Returns:
            True if solver is available, False otherwise
        """
        pass

    @abstractmethod
    def build_native_model(self, model: Model) -> Any:
        """Build native solver model from pysym model.

        Args:
            model: The pysym Model to compile

        Returns:
            Native solver model object ready for solving

        Raises:
            ImportError: If required solver not installed
            RuntimeError: If model compilation fails
        """
        pass

    @abstractmethod
    def solve(
        self,
        native_model: Any,
        pysym_model: Model,
        time_limit: Optional[float] = None,
    ) -> Solution:
        """Solve the compiled model.

        Args:
            native_model: Native solver model (from build_native_model)
            pysym_model: Original pysym Model (for reference)
            time_limit: Optional time limit in seconds

        Returns:
            Solution object with results

        Raises:
            RuntimeError: If solving fails
        """
        pass

    def translate_variable(self, var: Variable) -> Any:
        """Translate a pysym variable to native solver variable.

        Args:
            var: pysym Variable to translate

        Returns:
            Native solver variable

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(
            f"{self.solver_name} translator does not implement translate_variable"
        )

    def translate_expression(self, expr: Any, var_map: Dict[str, Any]) -> Any:
        """Translate a pysym expression to native solver expression.

        Args:
            expr: pysym Expression to translate
            var_map: Mapping of variable names to native variables

        Returns:
            Native solver expression

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(
            f"{self.solver_name} translator does not implement translate_expression"
        )

    def translate_constraint(self, constraint: Any, var_map: Dict[str, Any]) -> Any:
        """Translate a pysym constraint to native solver constraint.

        Args:
            constraint: pysym Constraint to translate
            var_map: Mapping of variable names to native variables

        Returns:
            Native solver constraint

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(
            f"{self.solver_name} translator does not implement translate_constraint"
        )

    def translate_objective(self, objective: Any, var_map: Dict[str, Any]) -> Any:
        """Translate a pysym objective to native solver objective.

        Args:
            objective: pysym Objective to translate
            var_map: Mapping of variable names to native variables

        Returns:
            Native solver objective expression

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(
            f"{self.solver_name} translator does not implement translate_objective"
        )
