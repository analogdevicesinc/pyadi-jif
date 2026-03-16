from typing import Any, Callable, List, Optional

class ValidationResult:
    """Represents the result of a single validation rule."""

    def __init__(self, is_valid: bool, message: str, context: Optional[Any] = None):
        self.is_valid = is_valid
        self.message = message
        self.context = context

    def __repr__(self) -> str:
        status = "PASS" if self.is_valid else "FAIL"
        return f"[{status}] {self.message}"

class ValidationEngine:
    """Engine that manages and executes validation rules."""

    def __init__(self):
        self.rules: List[Callable[[Any], ValidationResult]] = []

    def add_rule(self, rule: Callable[[Any], ValidationResult]):
        """Adds a validation rule to the engine."""
        self.rules.append(rule)

    def validate(self, config: Any) -> List[ValidationResult]:
        """Executes all registered rules against the configuration."""
        results = []
        for rule in self.rules:
            try:
                result = rule(config)
                results.append(result)
            except Exception as e:
                results.append(ValidationResult(is_valid=False, message=f"Rule execution failed: {str(e)}"))
        return results
