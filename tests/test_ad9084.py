# flake8: noqa
import os
import pprint

import pytest

import adijif
import adijif.converters
import adijif.converters.ad9084_util

here = os.path.dirname(os.path.abspath(__file__))
profile_json = os.path.join(
    here, "apollo_profiles", "ad9084_profiles", "id00_stock_mode.json"
)
summary_json = os.path.join(
    here, "apollo_profiles", "ad9084_profiles", "id00_stock_mode.summary"
)


ref = {
    "common_lane_rate_Hz": 20625000000,
    "core_clock_Hz": None,
    "datapath": {
        "cddc_decimation": 4,
        "cduc_interpolation": 4,
        "fddc_decimation": 2,
        "fduc_interpolation": 2,
    },
    "device_clock_Hz": 20000000000,
    "id": "id00_stock_mode",
    "is_8t8r": False,
    "jesd_settings": {
        "jrx": {
            "F": 1,
            "HD": True,
            # "K": 256,
            "L": 8,
            "M": 4,
            # "N": 16,
            "Np": 16,
            "S": 1,
        },
        "jtx": {
            "F": 1,
            "HD": True,
            # "K": 256,
            "L": 8,
            "M": 4,
            # "N": 16,
            "Np": 16,
            "S": 1,
        },
    },
    "profile_name": "id00_stock_mode",
    "rx_jesd_mode": 47,
    "tx_jesd_mode": 47,
}


def test_config_parser():

    settings = adijif.converters.ad9084_util.parse_json_config(profile_json)

    print("Settings:")
    pprint.pprint(settings)

    assert settings is not None

    # Verify the settings match the reference
    for key in ref:
        if isinstance(ref[key], dict):
            assert settings[key] == ref[key]
        else:
            assert settings[key] == ref[key], f"Mismatch for key: {key}"


def test_ad9084_separate_model_update():

    settings = adijif.converters.ad9084_util.parse_json_config(profile_json)

    print("Settings:")
    pprint.pprint(settings)

    assert settings is not None

    # Apply the settings to the AD9084 RX
    vcxo = 125000000
    clock = "hmc7044"
    sys = adijif.system("ad9084_rx", clock, "xilinx", vcxo, solver="CPLEX")

    adijif.converters.ad9084_util.apply_settings(sys.converter, settings)

    # Verify the settings were applied correctly
    # converter_rate / (cddc_dec * fddc_dec)
    assert sys.converter.converter_clock == settings["device_clock_Hz"]
    assert sys.converter.sample_clock == settings["device_clock_Hz"] / (
        settings["datapath"]["cddc_decimation"]
        * settings["datapath"]["fddc_decimation"]
    )
    # Check the JESD settings
    keys = settings["jesd_settings"]["jrx"].keys()
    for key in keys:
        assert (
            getattr(sys.converter, key) == settings["jesd_settings"]["jtx"][key]
        ), f"Mismatch for key: {key}"


def test_ad9084_model_update():

    settings = adijif.converters.ad9084_util.parse_json_config(profile_json)

    print("Settings:")
    pprint.pprint(settings)

    assert settings is not None

    # Apply the settings to the AD9084 RX
    vcxo = 125000000
    clock = "hmc7044"
    sys = adijif.system("ad9084_rx", clock, "xilinx", vcxo, solver="CPLEX")

    sys.converter.apply_profile_settings(profile_json)

    # Verify the settings were applied correctly
    # converter_rate / (cddc_dec * fddc_dec)
    assert sys.converter.converter_clock == settings["device_clock_Hz"]
    assert sys.converter.sample_clock == settings["device_clock_Hz"] / (
        settings["datapath"]["cddc_decimation"]
        * settings["datapath"]["fddc_decimation"]
    )
    # Check the JESD settings
    keys = settings["jesd_settings"]["jrx"].keys()
    for key in keys:
        assert (
            getattr(sys.converter, key) == settings["jesd_settings"]["jtx"][key]
        ), f"Mismatch for key: {key}"
