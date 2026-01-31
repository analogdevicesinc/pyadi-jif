"""Constraint types for pysym."""


from adijif.pysym.expressions import Expression


class Constraint:
    """Base constraint class.

    A constraint is an Expression that represents a comparison
    (==, <=, >=, <, >, !=) between variables and constants.

    The constraint is stored as an Expression tree that can be
    compiled to any supported solver format.
    """

    def __init__(self, expr: Expression):
        """Initialize constraint from expression.

        Args:
            expr: Expression with comparison operator

        """
        if not expr.is_constraint():
            raise ValueError(
                f"Expression is not a constraint (no comparison operator). "
                f"Got operator: {expr.operator}"
            )
        self.expr = expr

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Constraint({self.expr})"


class ConditionalConstraint:
    """Conditional constraint (if-then pattern).

    Represents a constraint that is only enforced if a condition holds:
    IF condition THEN consequent

    Example:
        use_feature = BinaryVar(name="use_feature")
        value = IntegerVar(range(1, 100), name="value")

        # If use_feature == 1, then value >= 50
        cond = ConditionalConstraint(
            condition=(use_feature == 1),
            consequent=(value >= 50)
        )

    Note:
        Not all solvers support conditional constraints.
        Use Feature compatibility checking before adding.

    """

    def __init__(
        self,
        condition: Expression,
        consequent: Expression,
    ):
        """Initialize conditional constraint.

        Args:
            condition: Boolean expression that guards the constraint
            consequent: Constraint to apply if condition is true

        """
        if not condition.is_constraint():
            raise ValueError("Condition must be a constraint expression")
        if not consequent.is_constraint():
            raise ValueError("Consequent must be a constraint expression")

        self.condition = condition
        self.consequent = consequent

    def __repr__(self) -> str:
        """Return string representation."""
        return f"IF {self.condition} THEN {self.consequent}"
