import pytest
from adijif.validation.engine import ValidationResult
from adijif.validation.system import SystemValidator

def test_system_valid_config():
    validator = SystemValidator()
    config = {
        "clock": {
            "output_clocks": {
                "AD9081_RX_ref_clk": {"rate": 375e6, "divider": 8},
                "AD9081_RX_sysref": {"rate": 3.125e6, "divider": 800}
            }
        },
        "converter_AD9081_RX": {
            "sample_clock": 375e6,
            "jesd_mode": "jesd204b"
        }
    }
    results = validator.validate(config)
    for r in results:
        assert r.is_valid is True, f"Failed on: {r.message}"

def test_system_clock_mismatch():
    validator = SystemValidator()
    config = {
        "clock": {
            "output_clocks": {
                "AD9081_RX_ref_clk": {"rate": 500e6, "divider": 6},
            }
        },
        "converter_AD9081_RX": {
            "sample_clock": 375e6,
        }
    }
    results = validator.validate(config)
    mismatch_results = [r for r in results if "mismatch" in r.message.lower()]
    assert any(not r.is_valid for r in mismatch_results)

def test_system_missing_sysref():
    validator = SystemValidator()
    config = {
        "clock": {
            "output_clocks": {
                "AD9081_RX_ref_clk": {"rate": 375e6},
            }
        },
        "converter_AD9081_RX": {
            "sample_clock": 375e6,
        }
    }
    results = validator.validate(config)
    sysref_results = [r for r in results if "sysref" in r.message.lower()]
    assert any(not r.is_valid for r in sysref_results)
