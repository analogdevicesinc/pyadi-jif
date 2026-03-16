import pytest
from adijif.validation.converters import AD9152Rules

def test_ad9152_valid_config():
    rules = AD9152Rules()
    config = {
        "device": "AD9152",
        "converter_clock": 2e9,
        "interpolation": 4,
        "L": 4,
        "M": 2,
        "F": 1,
        "S": 1,
        "K": 32,
        "Np": 16
    }
    results = rules.validate(config)
    for r in results:
        assert r.is_valid is True, f"Failed on: {r.message}"

def test_ad9152_invalid_converter_clock():
    rules = AD9152Rules()
    config = {
        "device": "AD9152",
        "converter_clock": 3e9, # Max is 2.25e9
    }
    results = rules.validate(config)
    cc_results = [r for r in results if "converter_clock" in r.message]
    assert any(not r.is_valid for r in cc_results)

def test_ad9152_invalid_interpolation():
    rules = AD9152Rules()
    config = {
        "device": "AD9152",
        "interpolation": 3, # Invalid: [1, 2, 4, 8]
    }
    results = rules.validate(config)
    interp_results = [r for r in results if "interpolation" in r.message]
    assert any(not r.is_valid for r in interp_results)
