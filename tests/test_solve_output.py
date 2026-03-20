"""Tests for the output structure of the solve method.

These tests ensure that the dictionaries returned by sys.solve() and
component.get_config() match the documented structure.
"""


import pytest

import adijif


@pytest.mark.parametrize(
    "converter_name, clock_chip, fpga_vendor, vcxo_freq, dev_kit",
    [
        ("ad9680", "ad9523_1", "xilinx", 125e6, "zc706"),
    ],
)
def test_solve_output_should_contain_documented_keys(
    converter_name: str,
    clock_chip: str,
    fpga_vendor: str,
    vcxo_freq: float,
    dev_kit: str,
):
    """Verify that sys.solve() returns a dictionary with the expected top-level keys."""
    # Arrange
    sys = adijif.system(
        converter_name, clock_chip, fpga_vendor, vcxo_freq, solver="CPLEX"
    )
    sys.fpga.setup_by_dev_kit_name(dev_kit)

    # Act
    config = sys.solve()

    # Assert
    assert isinstance(config, dict)
    assert "clock" in config
    assert isinstance(config["clock"], dict)

    # Check for converter and jesd keys
    # The keys use the converter's .name attribute (typically uppercase)
    cname = sys.converter.name
    assert f"jesd_{cname}" in config
    assert f"fpga_{cname}" in config
    assert f"converter_{cname}" in config


def test_component_get_config_should_contain_documented_keys():
    """Verify that component.get_config() returns expected keys for standalone components."""
    # Arrange: Clock Chip
    clk = adijif.ad9523_1()
    vcxo = 125e6
    output_clocks = [1e9, 500e6, 7.8125e6]
    clock_names = ["ADC", "FPGA", "SYSREF"]
    clk.set_requested_clocks(vcxo, output_clocks, clock_names)
    clk.n2 = 24

    # Act
    clk.solve()
    config = clk.get_config()

    # Assert
    assert isinstance(config, dict)
    assert "out_dividers" in config
    assert "output_clocks" in config
    assert "m1" in config
    assert "n2" in config
    assert "r2" in config


def test_ad9084_datapath_config_structure():
    """Verify AD9084 datapath config structure matches documentation."""
    # Arrange
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", 125e6, solver="CPLEX")
    sys.converter.datapath.cddc_decimations = [4, 4, 4, 4]
    sys.converter.datapath.fddc_decimations = [2, 2, 2, 2, 2, 2, 2, 2]
    sys.converter.datapath.fddc_enabled = [True] * 8

    # Act
    config = sys.converter.datapath.get_config()

    # Assert
    assert "cddc" in config
    assert "decimations" in config["cddc"]
    assert "fddc" in config
    assert "decimations" in config["fddc"]
    assert config["cddc"]["decimations"] == [4, 4, 4, 4]
