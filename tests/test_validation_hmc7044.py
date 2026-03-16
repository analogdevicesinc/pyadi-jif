import pytest
from adijif.validation.clocks import HMC7044Rules

def test_hmc7044_valid_config():
    rules = HMC7044Rules()
    config = {
        "device": "HMC7044",
        "vcxo": 125e6,
        "vcxo_doubler": 1,
        "r2": 1,
        "n2": 20,
        "vco": 2500e6, # Valid: 2400 to 3200
        "out_dividers": [2, 4, 10] # Valid: d_available
    }
    results = rules.validate(config)
    for r in results:
        assert r.is_valid is True, f"Failed on: {r.message}"

def test_hmc7044_invalid_vco():
    rules = HMC7044Rules()
    config = {
        "device": "HMC7044",
        "vco": 2000e6, # Invalid: min 2400
    }
    results = rules.validate(config)
    vco_results = [r for r in results if "vco" in r.message]
    assert any(not r.is_valid for r in vco_results)

def test_hmc7044_invalid_divider():
    rules = HMC7044Rules()
    config = {
        "device": "HMC7044",
        "out_dividers": [7] # Invalid: not in d_available (1, 3, 5, or even)
    }
    results = rules.validate(config)
    div_results = [r for r in results if "divider" in r.message]
    assert any(not r.is_valid for r in div_results)
