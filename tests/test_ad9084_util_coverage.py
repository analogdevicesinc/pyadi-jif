"""Additional tests for adijif.converters.ad9084_util to improve coverage."""

import json
import os
import pytest
import adijif
from adijif.converters.ad9084_util import _convert_to_config, parse_json_config, apply_settings

def test_ad9084_util_convert_to_config():
    """Verify _convert_to_config correctly maps parameters."""
    res = _convert_to_config("1", 1, 2, 3, 4, 1, 32, 16, 16, 0, 0, 0, "jesd204c")
    assert res["L"] == 1
    assert res["M"] == 2
    assert res["jesd_class"] == "jesd204c"

def test_ad9084_util_parse_json_config_file_not_found():
    """Verify parse_json_config raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Profile JSON file does not exist"):
        parse_json_config("non_existent.json")

def test_ad9084_util_parse_json_config_invalid_version():
    """Verify parse_json_config raises KeyError on unsupported version."""
    data = {
        "profile_cfg": {
            "profile_version": {"major": 0, "minor": 0, "patch": 0}
        }
    }
    with open("tmp_profile.json", "w") as f:
        json.dump(data, f)
    
    try:
        with pytest.raises(KeyError, match="supported"):
            parse_json_config("tmp_profile.json")
    finally:
        if os.path.exists("tmp_profile.json"):
            os.remove("tmp_profile.json")

def test_ad9084_util_apply_settings_mode_mismatch():
    """Verify apply_settings raises ValueError on TX/RX mode mismatch."""
    conv = adijif.ad9084_rx(solver="CPLEX")
    profile_settings = {
        "device_clock_Hz": 10e9,
        "datapath": {"cddc_decimation": 1, "fddc_decimation": 1},
        "jesd_settings": {
            "jtx": {"M": 2, "L": 1, "S": 1, "Np": 16},
            "jrx": {"M": 4, "L": 1, "S": 1, "Np": 16} # Mismatch
        }
    }
    with pytest.raises(ValueError, match="TX and RX JESD204C modes do not match"):
        apply_settings(conv, profile_settings)

def test_ad9084_util_apply_settings_mode_not_found():
    """Verify apply_settings raises Exception if mode not found."""
    conv = adijif.ad9084_rx(solver="CPLEX")
    profile_settings = {
        "device_clock_Hz": 10e9,
        "datapath": {"cddc_decimation": 1, "fddc_decimation": 1},
        "jesd_settings": {
            "jtx": {"M": 99, "L": 1, "S": 1, "Np": 16},
            "jrx": {"M": 99, "L": 1, "S": 1, "Np": 16}
        }
    }
    with pytest.raises(Exception, match="No JESD mode found"):
        apply_settings(conv, profile_settings)
