"""Core Model class for pysym."""

from typing import Any, Dict, List, Optional, Union

from adijif.pysym.constraints import Constraint, ConditionalConstraint
from adijif.pysym.expressions import Expression, Intermediate
from adijif.pysym.objectives import LexicographicObjective, Objective
from adijif.pysym.solution import Solution
from adijif.pysym.variables import Variable


class Model:
    """Optimization model that can be compiled to different solvers.

    The Model class is the main API for defining optimization problems.
    Variables, constraints, and objectives are added to the model, then
    compiled to a specific solver backend (CPLEX, GEKKO, OR-Tools, etc.)
    for solving.

    A single model definition can be compiled to multiple solvers for
    comparison and validation without code changes.

    Attributes:
        solver: Name of solver backend ("CPLEX", "gekko", "ortools")
        variables: List of decision variables in the model
        constraints: List of constraints
        objectives: List of objective functions
        intermediates: List of intermediate expressions

    Example:
        model = Model(solver="CPLEX")

        # Define variables
        x = IntegerVar(domain=range(1, 10), name="x")
        y = IntegerVar(domain=range(1, 10), name="y")

        # Add to model
        model.add_variable(x)
        model.add_variable(y)

        # Add constraints
        model.add_constraint(x + y >= 10)
        model.add_constraint(x - y <= 5)

        # Add objective
        model.add_objective(x, minimize=True)

        # Solve
        solution = model.solve()
        print(solution.get_value(x))
    """

    def __init__(self, solver: str = "CPLEX"):
        """Initialize model.

        Args:
            solver: Solver backend name ("CPLEX", "gekko", "ortools")

        Raises:
            ValueError: If solver name is invalid
        """
        valid_solvers = ["CPLEX", "gekko", "ortools"]
        if solver not in valid_solvers:
            raise ValueError(
                f"Invalid solver '{solver}'. Must be one of {valid_solvers}"
            )

        self.solver = solver
        self.variables: List[Variable] = []
        self.constraints: List[Constraint] = []
        self.conditional_constraints: List[ConditionalConstraint] = []
        self.objectives: List[Objective] = []
        self.lexicographic_objectives: List[LexicographicObjective] = []
        self.intermediates: List[Intermediate] = []

        # Native solver model (will be set during compilation)
        self._native_model = None
        self._translator = None

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Model(solver={self.solver}, "
            f"vars={len(self.variables)}, "
            f"constraints={len(self.constraints)}, "
            f"objectives={len(self.objectives)})"
        )

    def add_variable(self, var: Variable) -> "Model":
        """Add a decision variable to the model.

        Args:
            var: Variable to add

        Returns:
            Self (for method chaining)

        Raises:
            TypeError: If var is not a Variable
            ValueError: If variable with same name already exists
        """
        if not isinstance(var, Variable):
            raise TypeError(f"Expected Variable, got {type(var)}")

        # Check for duplicate names
        if any(v.name == var.name for v in self.variables):
            raise ValueError(f"Variable with name '{var.name}' already exists")

        self.variables.append(var)
        return self

    def add_constraint(
        self, constraint: Union[Constraint, Expression]
    ) -> "Model":
        """Add a constraint to the model.

        Args:
            constraint: Constraint object or Expression with comparison operator

        Returns:
            Self (for method chaining)

        Raises:
            TypeError: If constraint is not Constraint or Expression
            ValueError: If expression is not a constraint
        """
        if isinstance(constraint, Expression):
            constraint = Constraint(constraint)
        elif not isinstance(constraint, Constraint):
            raise TypeError(
                f"Expected Constraint or Expression, got {type(constraint)}"
            )

        self.constraints.append(constraint)
        return self

    def add_conditional_constraint(
        self, condition: Expression, consequent: Expression
    ) -> "Model":
        """Add a conditional constraint (if-then).

        Args:
            condition: Boolean expression (the condition)
            consequent: Constraint expression (consequence if condition is true)

        Returns:
            Self (for method chaining)

        Raises:
            ValueError: If expressions are invalid
        """
        cond_constraint = ConditionalConstraint(condition, consequent)
        self.conditional_constraints.append(cond_constraint)
        return self

    def add_objective(
        self,
        expr: Union[Variable, Expression],
        minimize: bool = True,
        name: Optional[str] = None,
        weight: float = 1.0,
    ) -> "Model":
        """Add an objective function to the model.

        Args:
            expr: Expression or variable to optimize
            minimize: If True, minimize; if False, maximize
            name: Optional name for the objective
            weight: Priority weight for multi-objective optimization

        Returns:
            Self (for method chaining)

        Raises:
            TypeError: If expr is not Variable or Expression
            ValueError: If expression is not arithmetic
        """
        objective = Objective(expr, minimize, name, weight)
        self.objectives.append(objective)
        return self

    def add_lexicographic_objective(
        self,
        objectives: List[tuple],
        names: Optional[List[str]] = None,
    ) -> "Model":
        """Add a lexicographic multi-objective.

        Args:
            objectives: List of (expression, minimize) tuples in priority order
            names: Optional names for each objective

        Returns:
            Self (for method chaining)

        Raises:
            ValueError: If objectives are invalid
        """
        lex_obj = LexicographicObjective(objectives, names)
        self.lexicographic_objectives.append(lex_obj)
        return self

    def add_intermediate(self, intermediate: Intermediate) -> "Model":
        """Add an intermediate expression.

        Args:
            intermediate: Intermediate expression

        Returns:
            Self (for method chaining)

        Raises:
            TypeError: If not an Intermediate
        """
        if not isinstance(intermediate, Intermediate):
            raise TypeError(f"Expected Intermediate, got {type(intermediate)}")

        self.intermediates.append(intermediate)
        return self

    def compile(self) -> "Model":
        """Compile model to native solver format.

        This step converts all pysym objects (variables, constraints,
        objectives) to the native solver representation based on the
        selected solver backend.

        Returns:
            Self (for method chaining)

        Raises:
            ImportError: If required solver not installed
            RuntimeError: If compilation fails
        """
        # Import translator here to avoid circular imports
        from adijif.pysym.translators.registry import get_translator

        # Get appropriate translator for this solver
        self._translator = get_translator(self.solver)

        # Compile to native model
        self._native_model = self._translator.build_native_model(self)

        return self

    def solve(
        self, time_limit: Optional[float] = None
    ) -> Solution:
        """Solve the compiled model.

        Args:
            time_limit: Optional time limit in seconds

        Returns:
            Solution object with results

        Raises:
            RuntimeError: If model has not been compiled
            RuntimeError: If solver fails
        """
        if self._native_model is None:
            self.compile()

        if self._translator is None:
            raise RuntimeError("Model must be compiled before solving")

        # Solve using translator
        solution = self._translator.solve(
            self._native_model, self, time_limit=time_limit
        )

        return solution

    def get_variables(self, name_pattern: Optional[str] = None) -> List[Variable]:
        """Get variables matching optional name pattern.

        Args:
            name_pattern: Optional regex pattern for variable names

        Returns:
            List of matching variables
        """
        if name_pattern is None:
            return self.variables

        import re

        pattern = re.compile(name_pattern)
        return [v for v in self.variables if pattern.search(v.name)]

    def get_variable_by_name(self, name: str) -> Optional[Variable]:
        """Get variable by exact name.

        Args:
            name: Variable name

        Returns:
            Variable or None if not found
        """
        for var in self.variables:
            if var.name == name:
                return var
        return None
