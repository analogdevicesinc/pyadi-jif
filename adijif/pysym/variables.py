"""Variable types for pysym expressions."""

from typing import Any, List, Optional, Union


class Variable:
    """Base class for optimization variables.

    Variables represent unknown quantities to be determined by the solver.
    Each variable has a name and optionally an initial value for debugging.
    """

    def __init__(self, name: str, initial_value: Optional[Union[int, float]] = None):
        """Initialize a variable.

        Args:
            name: Unique variable name for debugging and solution extraction
            initial_value: Optional initial/hint value for solver

        """
        self.name = name
        self.initial_value = initial_value
        self._native_var = None  # Will be set by translator

    def __repr__(self) -> str:
        """Return string representation."""
        return f"{self.__class__.__name__}({self.name})"

    def __add__(self, other: Any) -> "Expression":
        """Addition operator."""
        from adijif.pysym.expressions import Expression

        return Expression(self, "+", other)

    def __sub__(self, other: Any) -> "Expression":
        """Subtraction operator."""
        from adijif.pysym.expressions import Expression

        return Expression(self, "-", other)

    def __mul__(self, other: Any) -> "Expression":
        """Multiplication operator."""
        from adijif.pysym.expressions import Expression

        return Expression(self, "*", other)

    def __truediv__(self, other: Any) -> "Expression":
        """Division operator."""
        from adijif.pysym.expressions import Expression

        return Expression(self, "/", other)

    def __eq__(self, other: Any) -> "Expression":
        """Equality constraint."""
        from adijif.pysym.expressions import Expression

        return Expression(self, "==", other)

    def __le__(self, other: Any) -> "Expression":
        """Less than or equal constraint."""
        from adijif.pysym.expressions import Expression

        return Expression(self, "<=", other)

    def __ge__(self, other: Any) -> "Expression":
        """Greater than or equal constraint."""
        from adijif.pysym.expressions import Expression

        return Expression(self, ">=", other)

    def __lt__(self, other: Any) -> "Expression":
        """Less than constraint."""
        from adijif.pysym.expressions import Expression

        return Expression(self, "<", other)

    def __gt__(self, other: Any) -> "Expression":
        """Greater than constraint."""
        from adijif.pysym.expressions import Expression

        return Expression(self, ">", other)

    def __ne__(self, other: Any) -> "Expression":
        """Not equal constraint."""
        from adijif.pysym.expressions import Expression

        return Expression(self, "!=", other)

    def __radd__(self, other: Any) -> "Expression":
        """Right addition."""
        from adijif.pysym.expressions import Expression

        return Expression(other, "+", self)

    def __rsub__(self, other: Any) -> "Expression":
        """Right subtraction."""
        from adijif.pysym.expressions import Expression

        return Expression(other, "-", self)

    def __rmul__(self, other: Any) -> "Expression":
        """Right multiplication."""
        from adijif.pysym.expressions import Expression

        return Expression(other, "*", self)

    def __rtruediv__(self, other: Any) -> "Expression":
        """Right division."""
        from adijif.pysym.expressions import Expression

        return Expression(other, "/", self)

    def __neg__(self) -> "Expression":
        """Negation operator."""
        from adijif.pysym.expressions import Expression

        return Expression(None, "-", self)


class IntegerVar(Variable):
    """Integer variable with bounded domain.

    Args:
        domain: Range of valid values. Can be:
            - range(min, max+1): contiguous integers
            - list of ints: specific allowed values
            - single int: constant value
        name: Unique variable name
        initial_value: Optional initial/hint value

    Examples:
        x = IntegerVar(domain=range(1, 100), name="x")
        y = IntegerVar(domain=[1, 2, 4, 8, 16], name="y")
        z = IntegerVar(domain=42, name="z")  # Constant

    """

    def __init__(
        self,
        domain: Union[range, List[int], int],
        name: str,
        initial_value: Optional[int] = None,
    ):
        """Initialize integer variable."""
        super().__init__(name, initial_value)
        self.domain = domain
        self._normalize_domain()

    def _normalize_domain(self) -> None:
        """Convert domain to normalized form."""
        if isinstance(self.domain, int):
            self.domain = [self.domain]
        elif isinstance(self.domain, range):
            # Keep range as-is, will handle specially in translators
            pass
        elif isinstance(self.domain, list):
            # Verify all are integers
            assert all(
                isinstance(x, int) for x in self.domain
            ), f"Non-integer in domain: {self.domain}"
        else:
            raise TypeError(f"Invalid domain type: {type(self.domain)}")

    @property
    def is_constant(self) -> bool:
        """Check if this variable is actually a constant."""
        if isinstance(self.domain, list):
            return len(self.domain) == 1
        return False

    @property
    def constant_value(self) -> Optional[int]:
        """Get value if this is a constant variable."""
        if isinstance(self.domain, list) and len(self.domain) == 1:
            return self.domain[0]
        return None

    def __repr__(self) -> str:
        """Return string representation."""
        return f"IntegerVar({self.name}, domain={self.domain})"


class BinaryVar(Variable):
    """Binary variable with domain {0, 1}.

    Args:
        name: Unique variable name
        initial_value: Optional initial value (0 or 1)

    Examples:
        use_feature = BinaryVar(name="use_feature")
        is_enabled = BinaryVar(name="is_enabled", initial_value=1)

    """

    def __init__(self, name: str, initial_value: Optional[int] = None):
        """Initialize binary variable."""
        super().__init__(name, initial_value)
        self.domain = [0, 1]

    def __repr__(self) -> str:
        """Return string representation."""
        return f"BinaryVar({self.name})"


class ContinuousVar(Variable):
    """Continuous (floating-point) variable with bounds.

    Args:
        lb: Lower bound (inclusive)
        ub: Upper bound (inclusive)
        name: Unique variable name
        initial_value: Optional initial value

    Examples:
        voltage = ContinuousVar(lb=0.0, ub=3.3, name="voltage")
        frequency = ContinuousVar(lb=1e6, ub=1e9, name="frequency")

    """

    def __init__(
        self,
        lb: float,
        ub: float,
        name: str,
        initial_value: Optional[float] = None,
    ):
        """Initialize continuous variable."""
        super().__init__(name, initial_value)
        if lb > ub:
            raise ValueError(f"Lower bound {lb} > upper bound {ub}")
        self.lb = lb
        self.ub = ub

    @property
    def domain(self) -> tuple:
        """Return domain as (lb, ub) tuple."""
        return (self.lb, self.ub)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ContinuousVar({self.name}, [{self.lb}, {self.ub}])"


class Constant(Variable):
    """Constant value in expressions.

    Used to represent fixed values in constraint and objective definitions.
    A Constant is not a decision variable and cannot be solved for.

    Args:
        value: The constant numeric value
        name: Optional name for debugging

    Examples:
        c = Constant(3.14159, name="pi")
        expr = x + Constant(10)

    """

    def __init__(self, value: Union[int, float], name: Optional[str] = None):
        """Initialize constant."""
        if name is None:
            name = f"const_{value}"
        super().__init__(name, None)
        self.value = value
        self.domain = [value]

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Constant({self.value})"
