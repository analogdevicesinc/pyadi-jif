from typing import Any, Dict, List
from .engine import ValidationEngine, ValidationResult

class ClockRules(ValidationEngine):
    """Base class for clock-specific validation rules."""
    pass

class HMC7044Rules(ClockRules):
    """Validation rules for HMC7044 clock chip."""

    def __init__(self):
        super().__init__()
        self.add_rule(self._check_vco)
        self.add_rule(self._check_pfd)
        self.add_rule(self._check_dividers)
        self.add_rule(self._check_vcxo)

    def _check_vco(self, config: Dict[str, Any]) -> ValidationResult:
        vco = config.get("vco")
        if vco is None:
            return ValidationResult(is_valid=True, message="vco not provided, skipping")
        
        vco_min, vco_max = 2400e6, 3200e6
        if vco_min <= vco <= vco_max:
            return ValidationResult(is_valid=True, message=f"vco={vco} is valid")
        return ValidationResult(is_valid=False, message=f"vco={vco} is invalid. Must be between {vco_min} and {vco_max}")

    def _check_pfd(self, config: Dict[str, Any]) -> ValidationResult:
        vcxo = config.get("vcxo")
        vd = config.get("vcxo_doubler", 1)
        r2 = config.get("r2")
        
        if any(x is None for x in [vcxo, r2]):
            return ValidationResult(is_valid=True, message="vcxo or r2 not provided, skipping PFD check")
        
        pfd = (vcxo * vd) / r2
        pfd_max = 250e6
        if pfd <= pfd_max:
            return ValidationResult(is_valid=True, message=f"PFD={pfd} is valid (max {pfd_max})")
        return ValidationResult(is_valid=False, message=f"PFD={pfd} exceeds max {pfd_max}")

    def _check_dividers(self, config: Dict[str, Any]) -> ValidationResult:
        divs = config.get("out_dividers")
        if divs is None:
            return ValidationResult(is_valid=True, message="out_dividers not provided, skipping")
        
        if not isinstance(divs, list):
            divs = [divs]

        for d in divs:
            is_valid_d = (d in [1, 3, 5]) or (d % 2 == 0 and 2 <= d <= 4094)
            if not is_valid_d:
                return ValidationResult(is_valid=False, message=f"divider={d} is invalid. Must be 1, 3, 5, or even up to 4094")
        
        return ValidationResult(is_valid=True, message=f"All dividers {divs} are valid")

    def _check_vcxo(self, config: Dict[str, Any]) -> ValidationResult:
        vcxo = config.get("vcxo")
        if vcxo is None:
            return ValidationResult(is_valid=True, message="vcxo not provided, skipping")
        
        vcxo_min, vcxo_max = 10e6, 500e6
        if vcxo_min <= vcxo <= vcxo_max:
            return ValidationResult(is_valid=True, message=f"vcxo={vcxo} is valid")
        return ValidationResult(is_valid=False, message=f"vcxo={vcxo} is invalid. Must be between {vcxo_min} and {vcxo_max}")
