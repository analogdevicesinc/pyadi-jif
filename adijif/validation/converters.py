from typing import Any, Dict, List
from .engine import ValidationEngine, ValidationResult
from .jesd204 import JESD204Rules

class ConverterRules(ValidationEngine):
    """Base class for converter-specific validation rules."""
    pass

class AD9081Rules(ConverterRules):
    """Validation rules for AD9081 MxFE."""

    def __init__(self):
        super().__init__()
        # Inherit JESD204 generic rules
        jesd_rules = JESD204Rules()
        for rule in jesd_rules.rules:
            self.add_rule(rule)
        
        self.add_rule(self._check_converter_clock)
        self.add_rule(self._check_decimation_interpolation)
        self.add_rule(self._check_bit_clock)
        self.add_rule(self._check_sample_clock)

    def _check_converter_clock(self, config: Dict[str, Any]) -> ValidationResult:
        device = config.get("device", "").upper()
        cc = config.get("converter_clock")
        if cc is None:
            return ValidationResult(is_valid=True, message="converter_clock not provided, skipping")
        
        if "AD9081_RX" in device:
            min_cc, max_cc = 1.45e9, 4e9
        elif "AD9081_TX" in device:
            min_cc, max_cc = 2.9e9, 12e9
        else:
            return ValidationResult(is_valid=True, message=f"Unknown or generic device {device}, skipping converter_clock check")

        if min_cc <= cc <= max_cc:
            return ValidationResult(is_valid=True, message=f"converter_clock={cc} is valid for {device}")
        return ValidationResult(is_valid=False, message=f"converter_clock={cc} is invalid for {device}. Must be between {min_cc} and {max_cc}")

    def _check_decimation_interpolation(self, config: Dict[str, Any]) -> ValidationResult:
        device = config.get("device", "").upper()
        
        if "RX" in device:
            val = config.get("decimation")
            label = "decimation"
            available = [1, 2, 3, 4, 6, 8, 9, 12, 16, 18, 24, 32, 36, 48, 64, 72, 96, 144]
        elif "TX" in device:
            val = config.get("interpolation")
            label = "interpolation"
            available = [1, 2, 3, 4, 6, 8, 9, 12, 16, 18, 24, 32, 36, 48, 64, 72, 96, 144]
        else:
            return ValidationResult(is_valid=True, message="Not an RX/TX device, skipping decimation/interpolation check")

        if val is None:
            return ValidationResult(is_valid=True, message=f"{label} not provided, skipping")
        
        if val in available:
            return ValidationResult(is_valid=True, message=f"{label}={val} is valid for {device}")
        return ValidationResult(is_valid=False, message=f"{label}={val} is invalid for {device}. Must be in {available}")

    def _check_bit_clock(self, config: Dict[str, Any]) -> ValidationResult:
        device = config.get("device", "").upper()
        jesd_mode = config.get("jesd_mode", "jesd204b").lower()
        bit_clock = config.get("bit_clock")
        
        if bit_clock is None:
            return ValidationResult(is_valid=True, message="bit_clock not provided, skipping")

        # Standard AD9081 limits
        limits = {
            "jesd204b": (1.5e9, 15.5e9),
            "jesd204c": (6e9, 24.75e9)
        }
        
        min_bc, max_bc = limits.get(jesd_mode, (0, float('inf')))
        
        if min_bc <= bit_clock <= max_bc:
            return ValidationResult(is_valid=True, message=f"bit_clock={bit_clock} is valid for {jesd_mode}")
        return ValidationResult(is_valid=False, message=f"bit_clock={bit_clock} is invalid for {jesd_mode}. Must be between {min_bc} and {max_bc}")

    def _check_sample_clock(self, config: Dict[str, Any]) -> ValidationResult:
        device = config.get("device", "").upper()
        sc = config.get("sample_clock")
        
        if sc is None:
            return ValidationResult(is_valid=True, message="sample_clock not provided, skipping")
        
        if "AD9081_RX" in device:
            min_sc, max_sc = 312.5e6 / 16, 4e9
        elif "AD9081_TX" in device:
            min_sc, max_sc = 2.9e9 / 144, 12e9
        else:
            return ValidationResult(is_valid=True, message=f"Unknown or generic device {device}, skipping sample_clock check")

        if min_sc <= sc <= max_sc:
            return ValidationResult(is_valid=True, message=f"sample_clock={sc} is valid for {device}")
        return ValidationResult(is_valid=False, message=f"sample_clock={sc} is invalid for {device}. Must be between {min_sc} and {max_sc}")
