import pytest
from adijif.validation.engine import ValidationResult
from adijif.validation.converters import AD9081Rules

def test_ad9081_rx_valid_config():
    rules = AD9081Rules()
    config = {
        "device": "AD9081_RX",
        "converter_clock": 3e9, # Valid: 1.45e9 to 4e9
        "sample_clock": 375e6,  # Valid: 1.45e9 / 4 = 362.5e6 (min is lower)
        "decimation": 8,
        "jesd_mode": "jesd204b",
        "L": 4,
        "M": 2,
        "F": 2,
        "S": 1,
        "K": 32,
        "Np": 16
    }
    results = rules.validate(config)
    for r in results:
        assert r.is_valid is True, f"Failed on: {r.message}"

def test_ad9081_rx_invalid_converter_clock():
    rules = AD9081Rules()
    config = {
        "device": "AD9081_RX",
        "converter_clock": 5e9, # Invalid: max is 4e9
    }
    results = rules.validate(config)
    cc_results = [r for r in results if "converter_clock" in r.message]
    assert any(not r.is_valid for r in cc_results)

def test_ad9081_rx_invalid_decimation():
    rules = AD9081Rules()
    config = {
        "device": "AD9081_RX",
        "decimation": 7, # Invalid: not in decimation_available
    }
    results = rules.validate(config)
    dec_results = [r for r in results if "decimation" in r.message]
    assert any(not r.is_valid for r in dec_results)

def test_ad9081_tx_invalid_converter_clock():
    rules = AD9081Rules()
    config = {
        "device": "AD9081_TX",
        "converter_clock": 2e9, # Invalid: min is 2.9e9
    }
    results = rules.validate(config)
    cc_results = [r for r in results if "converter_clock" in r.message]
    assert any(not r.is_valid for r in cc_results)

def test_ad9081_invalid_bit_clock():
    rules = AD9081Rules()
    config = {
        "jesd_mode": "jesd204c",
        "bit_clock": 5e9, # Invalid for 204c: min 6e9
    }
    results = rules.validate(config)
    bc_results = [r for r in results if "bit_clock" in r.message]
    assert any(not r.is_valid for r in bc_results)

def test_ad9081_rx_invalid_sample_clock():
    rules = AD9081Rules()
    config = {
        "device": "AD9081_RX",
        "sample_clock": 5e9, # Invalid: max 4e9
    }
    results = rules.validate(config)
    sc_results = [r for r in results if "sample_clock" in r.message]
    assert any(not r.is_valid for r in sc_results)
