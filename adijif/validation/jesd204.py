from typing import Any, Dict, List
from .engine import ValidationEngine, ValidationResult

class JESD204Rules(ValidationEngine):
    """Validation rules for generic JESD204 parameters."""

    def __init__(self):
        super().__init__()
        self.add_rule(self._check_l)
        self.add_rule(self._check_m)
        self.add_rule(self._check_f)
        self.add_rule(self._check_s)
        self.add_rule(self._check_k)
        self.add_rule(self._check_np)

    def _check_l(self, config: Dict[str, Any]) -> ValidationResult:
        l_val = config.get("L")
        if l_val is None:
            return ValidationResult(is_valid=True, message="L not provided, skipping")
        valid_l = [1, 2, 4, 8, 16, 32]
        if l_val in valid_l:
            return ValidationResult(is_valid=True, message=f"L={l_val} is valid")
        return ValidationResult(is_valid=False, message=f"L={l_val} is invalid. Must be in {valid_l}")

    def _check_m(self, config: Dict[str, Any]) -> ValidationResult:
        m_val = config.get("M")
        if m_val is None:
            return ValidationResult(is_valid=True, message="M not provided, skipping")
        if 1 <= m_val <= 32:
            return ValidationResult(is_valid=True, message=f"M={m_val} is valid")
        return ValidationResult(is_valid=False, message=f"M={m_val} is invalid. Must be between 1 and 32")

    def _check_f(self, config: Dict[str, Any]) -> ValidationResult:
        f_val = config.get("F")
        if f_val is None:
            return ValidationResult(is_valid=True, message="F not provided, skipping")
        if 1 <= f_val <= 256:
            return ValidationResult(is_valid=True, message=f"F={f_val} is valid")
        return ValidationResult(is_valid=False, message=f"F={f_val} is invalid. Must be between 1 and 256")

    def _check_s(self, config: Dict[str, Any]) -> ValidationResult:
        s_val = config.get("S")
        if s_val is None:
            return ValidationResult(is_valid=True, message="S not provided, skipping")
        if 1 <= s_val <= 32:
            return ValidationResult(is_valid=True, message=f"S={s_val} is valid")
        return ValidationResult(is_valid=False, message=f"S={s_val} is invalid. Must be between 1 and 32")

    def _check_k(self, config: Dict[str, Any]) -> ValidationResult:
        k_val = config.get("K")
        if k_val is None:
            return ValidationResult(is_valid=True, message="K not provided, skipping")
        if 1 <= k_val <= 32:
            return ValidationResult(is_valid=True, message=f"K={k_val} is valid")
        return ValidationResult(is_valid=False, message=f"K={k_val} is invalid. Must be between 1 and 32")

    def _check_np(self, config: Dict[str, Any]) -> ValidationResult:
        np_val = config.get("Np")
        if np_val is None:
            return ValidationResult(is_valid=True, message="Np not provided, skipping")
        valid_np = [12, 14, 16]
        if np_val in valid_np:
            return ValidationResult(is_valid=True, message=f"Np={np_val} is valid")
        return ValidationResult(is_valid=False, message=f"Np={np_val} is invalid. Must be in {valid_np}")
