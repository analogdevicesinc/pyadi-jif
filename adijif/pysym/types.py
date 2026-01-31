"""Type hints and protocols for pysym."""

from typing import Any, Protocol, Union

Domain = Union[range, list, int, float]
"""Type for variable domains. Can be range, list, or single value."""


class SolverVariable(Protocol):
    """Protocol for solver-specific variable types."""

    def __add__(self, other: Any) -> Any:
        """Addition operator."""
        ...

    def __sub__(self, other: Any) -> Any:
        """Subtraction operator."""
        ...

    def __mul__(self, other: Any) -> Any:
        """Multiplication operator."""
        ...

    def __truediv__(self, other: Any) -> Any:
        """Division operator."""
        ...

    def __eq__(self, other: Any) -> Any:
        """Equality operator."""
        ...

    def __le__(self, other: Any) -> Any:
        """Less than or equal operator."""
        ...

    def __ge__(self, other: Any) -> Any:
        """Greater than or equal operator."""
        ...

    def __lt__(self, other: Any) -> Any:
        """Less than operator."""
        ...

    def __gt__(self, other: Any) -> Any:
        """Greater than operator."""
        ...


class SolverExpression(Protocol):
    """Protocol for solver-specific expression types."""

    pass
