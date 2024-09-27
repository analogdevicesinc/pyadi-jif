# flake8: noqa

import pytest

import adijif


def test_converter_lane_count_valid():
    sys = adijif.system("ad9144", "ad9523_1", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zcu102")

    sys.converter.sample_clock = 1e9
    # Mode 0
    sys.converter.interpolation = 1
    sys.converter.L = 8
    sys.converter.M = 4
    sys.converter.N = 16
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.converter.HD = 1
    sys.converter.clocking_option = "integrated_pll"

    cfg = sys.solve()


def test_converter_lane_count_exceeds_fpga_lane_count():
    convs = ["ad9144", "ad9144", "ad9144"]
    sys = adijif.system(convs, "ad9523_1", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zcu102")

    for i, _ in enumerate(convs):
        # Mode 0
        sys.converter[i].sample_clock = 1e9
        sys.converter[i].interpolation = 1
        sys.converter[i].L = 8
        sys.converter[i].M = 4
        sys.converter[i].N = 16
        sys.converter[i].Np = 16
        sys.converter[i].K = 32
        sys.converter[i].F = 1
        sys.converter[i].HD = 1
        sys.converter[i].clocking_option = "integrated_pll"

    with pytest.raises(Exception, match=f"Max SERDES lanes exceeded. 8 only available"):
        cfg = sys.solve()


def test_nested_converter_lane_count_valid():
    sys = adijif.system("adrv9009", "ad9528", "xilinx", 122.88e6)
    sys.fpga.setup_by_dev_kit_name("zcu102")
    sys.converter.adc.sample_clock = 122.88e6
    sys.converter.dac.sample_clock = 122.88e6

    sys.converter.adc.decimation = 4
    sys.converter.dac.interpolation = 4

    mode_rx = "17"
    mode_tx = "6"
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204b")
    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204b")

    cfg = sys.solve()


def test_nested_converter_lane_count_exceeds_fpga_lane_count():
    fpga_L = 1

    sys = adijif.system("adrv9009", "ad9528", "xilinx", 122.88e6)

    sys.fpga.setup_by_dev_kit_name("zcu102")
    sys.fpga.max_serdes_lanes = fpga_L  # Force it to break

    sys.converter.adc.sample_clock = 122.88e6
    sys.converter.dac.sample_clock = 122.88e6

    sys.converter.adc.decimation = 4
    sys.converter.dac.interpolation = 4

    mode_rx = "17"
    mode_tx = "6"
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204b")
    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204b")

    with pytest.raises(
        Exception, match=f"Max SERDES lanes exceeded. {fpga_L} only available"
    ):
        cfg = sys.solve()
