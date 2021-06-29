# flake8: noqa
import pprint

import pytest

import adijif


def test_ad9081_rx_solver():
    vcxo = 100000000

    sys = adijif.system("ad9081_rx", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.Debug_Solver = False
    # sys.fpga.request_device_clock = False

    sys.converter.clocking_option = "integrated_pll"

    # Get Converter clocking requirements
    sys.converter.sample_clock = 250e6
    sys.converter.decimation = 16
    sys.converter.L = 4
    sys.converter.M = 8
    sys.converter.N = 16
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 4
    # sys.converter.S = 1

    # sys._try_fpga_configs()
    cfg = sys.solve()

    # assert sys.fpga.configs[0]["qpll_0_cpll_1"].value[0] == 0  # QPLL
    assert cfg["fpga_AD9081"]["type"] == "qpll"


def test_ad9081_tx_solver():
    vcxo = 100000000

    sys = adijif.system("ad9081_tx", "hmc7044", "xilinx", vcxo)
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.Debug_Solver = False
    # sys.fpga.request_device_clock = False

    sys.converter.clocking_option = "integrated_pll"

    # Get Converter clocking requirements
    sys.converter.sample_clock = 250e6
    sys.converter.interpolation = 48
    sys.converter.L = 4
    sys.converter.M = 8
    sys.converter.N = 16
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 4
    # sys.converter.S = 1

    # sys._try_fpga_configs()
    cfg = sys.solve()
    pprint.pprint(cfg)

    assert cfg["fpga_AD9081"]["type"] == "qpll"


def test_ad9081_rxtx_solver():
    vcxo = 100000000

    sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    # sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo)
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.Debug_Solver = True
    # sys.fpga.request_device_clock = False

    sys.converter.dac.clocking_option = "integrated_pll"
    sys.converter.adc.clocking_option = "integrated_pll"
    sys.converter.clocking_option = "integrated_pll"

    # Get Converter clocking requirements
    sys.converter.dac.jesd_class = "jesd204b"
    sys.converter.dac.sample_clock = 250e6
    sys.converter.dac.interpolation = 48
    sys.converter.dac.L = 4
    sys.converter.dac.M = 8
    sys.converter.dac.N = 16
    sys.converter.dac.Np = 16
    sys.converter.dac.K = 32
    sys.converter.dac.F = 4
    print("S DAC:", sys.converter.dac.S)
    # sys.converter.S = 1

    # Get Converter clocking requirements
    sys.converter.adc.jesd_class = "jesd204b"
    sys.converter.adc.sample_clock = 250e6
    sys.converter.adc.decimation = 16
    sys.converter.adc.L = 4
    sys.converter.adc.M = 8
    sys.converter.adc.N = 16
    sys.converter.adc.Np = 16
    sys.converter.adc.K = 32
    sys.converter.adc.F = 4
    sys.converter.adc.HD = 0
    sys.converter.adc.HD = 0

    print("S ADC:", sys.converter.adc.S)
    # sys.converter.S = 1

    # sys._try_fpga_configs()
    o = sys.solve()

    # print(sys.solution)
    # print(dir(sys.solution))
    # sys.solution.print_solution()

    # pprint.pprint(o)

    assert o["fpga_AD9081"][0]["type"] == "qpll"
    assert o["fpga_AD9081"][1]["type"] == "qpll"
