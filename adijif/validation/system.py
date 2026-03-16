from typing import Any, Dict, List
from .engine import ValidationEngine, ValidationResult

class SystemValidator(ValidationEngine):
    """Validator for end-to-end signal chain consistency."""

    def __init__(self):
        super().__init__()
        self.add_rule(self._check_clock_consistency)
        self.add_rule(self._check_sysref_presence)

    def _check_clock_consistency(self, config: Dict[str, Any]) -> ValidationResult:
        clock_cfg = config.get("clock", {})
        output_clocks = clock_cfg.get("output_clocks", {})
        
        # Check consistency for each converter in the config
        converter_keys = [k for k in config.keys() if k.startswith("converter_")]
        
        for ck in converter_keys:
            conv_name = ck.replace("converter_", "")
            conv_cfg = config[ck]
            target_sample_clock = conv_cfg.get("sample_clock")
            
            if target_sample_clock is None:
                continue
            
            # Look for a matching clock in the clock chip outputs
            # Common naming: <FPGA_NAME>_<CONV_NAME>_ref_clk
            matching_clks = [v for k, v in output_clocks.items() if conv_name in k and "ref_clk" in k]
            
            if not matching_clks:
                return ValidationResult(is_valid=False, message=f"No matching clock output found for converter {conv_name}")
            
            # For simplicity in this validator, we check if ANY matching clock matches the rate
            actual_rate = matching_clks[0].get("rate")
            if actual_rate != target_sample_clock:
                return ValidationResult(is_valid=False, message=f"Clock mismatch for {conv_name}: Converter expects {target_sample_clock}, Clock chip provides {actual_rate}")

        return ValidationResult(is_valid=True, message="All converter clocks are consistent with clock chip outputs")

    def _check_sysref_presence(self, config: Dict[str, Any]) -> ValidationResult:
        clock_cfg = config.get("clock", {})
        output_clocks = clock_cfg.get("output_clocks", {})
        
        converter_keys = [k for k in config.keys() if k.startswith("converter_")]
        
        for ck in converter_keys:
            conv_name = ck.replace("converter_", "")
            # Every JESD204 converter needs a sysref
            matching_sysrefs = [v for k, v in output_clocks.items() if conv_name in k and "sysref" in k]
            
            if not matching_sysrefs:
                return ValidationResult(is_valid=False, message=f"No sysref clock output found for converter {conv_name}")
        
        return ValidationResult(is_valid=True, message="All converters have corresponding sysref outputs")
