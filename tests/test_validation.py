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

from adijif.validation.jesd204 import JESD204Rules

def test_jesd204_rules_pass_valid_config():
    rules = JESD204Rules()
    config = {
        "L": 4,
        "M": 2,
        "F": 2,
        "S": 1,
        "K": 32,
        "Np": 16
    }
    results = rules.validate(config)
    for r in results:
        assert r.is_valid is True

def test_jesd204_rules_fail_invalid_l():
    rules = JESD204Rules()
    config = {"L": 3} # Invalid L
    results = rules.validate(config)
    l_results = [r for r in results if "L" in r.message]
    assert any(not r.is_valid for r in l_results)

def test_jesd204_rules_fail_invalid_k():
    rules = JESD204Rules()
    config = {"K": 40} # Invalid K
    results = rules.validate(config)
    k_results = [r for r in results if "K" in r.message]
    assert any(not r.is_valid for r in k_results)

def test_jesd204_rules_fail_invalid_m():
    rules = JESD204Rules()
    config = {"M": 0} # Invalid M
    results = rules.validate(config)
    m_results = [r for r in results if "M" in r.message]
    assert any(not r.is_valid for r in m_results)

def test_jesd204_rules_fail_invalid_f():
    rules = JESD204Rules()
    config = {"F": 300} # Invalid F
    results = rules.validate(config)
    f_results = [r for r in results if "F" in r.message]
    assert any(not r.is_valid for r in f_results)

def test_jesd204_rules_fail_invalid_s():
    rules = JESD204Rules()
    config = {"S": 100} # Invalid S
    results = rules.validate(config)
    s_results = [r for r in results if "S" in r.message]
    assert any(not r.is_valid for r in s_results)

def test_jesd204_rules_fail_invalid_np():
    rules = JESD204Rules()
    config = {"Np": 10} # Invalid Np
    results = rules.validate(config)
    np_results = [r for r in results if "Np" in r.message]
    assert any(not r.is_valid for r in np_results)
