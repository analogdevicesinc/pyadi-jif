import pytest
from adijif.validation.engine import ValidationEngine, ValidationResult

def test_validation_result_initialization():
    result = ValidationResult(is_valid=True, message="Success")
    assert result.is_valid is True
    assert result.message == "Success"

def test_validation_engine_runs_rules():
    engine = ValidationEngine()
    
    def dummy_rule(config):
        return ValidationResult(is_valid=True, message="Rule passed")
    
    engine.add_rule(dummy_rule)
    results = engine.validate({"param": 1})
    assert len(results) == 1
    assert results[0].is_valid is True
    assert results[0].message == "Rule passed"

def test_validation_engine_handles_failures():
    engine = ValidationEngine()
    
    def failing_rule(config):
        return ValidationResult(is_valid=False, message="Rule failed")
    
    engine.add_rule(failing_rule)
    results = engine.validate({"param": 1})
    assert len(results) == 1
    assert results[0].is_valid is False
    assert results[0].message == "Rule failed"
