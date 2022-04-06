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
    assert cfg["fpga_AD9081_RX"]["type"] == "qpll1"


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
    mode = adijif.utils.get_jesd_mode_from_params(
        sys.converter, L=4, M=8, Np=16, K=32, F=4
    )
    assert len(mode) == 1
    print(mode)
    sys.converter.set_quick_configuration_mode(mode[0]["mode"], mode[0]["jesd_mode"])
    assert sys.converter.L == 4
    assert sys.converter.M == 8
    assert sys.converter.Np == 16
    assert sys.converter.K == 32
    assert sys.converter.F == 4
    assert sys.converter.S == 1

    # sys._try_fpga_configs()
    cfg = sys.solve()
    pprint.pprint(cfg)

    assert cfg["fpga_AD9081_TX"]["type"] == "qpll1"


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

    pprint.pprint(o)

    assert o["fpga_adc"]["type"] == "qpll"
    assert o["fpga_dac"]["type"] == "qpll"


def test_ad9081_rxtx_zcu102_default_config():
    vcxo = 100e6

    sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.Debug_Solver = False
    sys.converter.clocking_option = "integrated_pll"
    sys.fpga.out_clk_select = "XCVR_REFCLK"  # force reference to be core clock rate
    sys.converter.adc.sample_clock = 4000000000 // (4 * 4)
    sys.converter.dac.sample_clock = 12000000000 // (8 * 6)

    sys.converter.adc.decimation = 16
    sys.converter.dac.interpolation = 48

    mode_tx = "9"
    mode_rx = "10.0"

    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204b")
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204b")

    assert sys.converter.adc.M == 8
    assert sys.converter.adc.F == 4
    assert sys.converter.adc.K == 32
    assert sys.converter.adc.Np == 16
    assert sys.converter.adc.CS == 0
    assert sys.converter.adc.L == 4
    assert sys.converter.adc.S == 1
    # assert sys.converter.adc.HD == 1

    sys.converter.adc._check_clock_relations()
    sys.converter.dac._check_clock_relations()

    cfg = sys.solve()

    print("Mode passed: ", mode_tx, sys.converter.adc.decimation)


def test_ad9081_rxtx_zcu102_lowrate_config():
    vcxo = 100e6

    sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zcu102")
    # sys.fpga.sys_clk_select = "GTH34_SYSCLK_QPLL0"  # Use faster QPLL
    sys.Debug_Solver = False
    sys.converter.clocking_option = "integrated_pll"
    # sys.fpga.out_clk_select = "XCVR_REFCLK"  # force reference to be core clock rate
    sys.converter.adc.sample_clock = 4000000000 / (4 * 8)
    sys.converter.dac.sample_clock = 4000000000 / (4 * 8)

    sys.converter.adc.decimation = 4 * 8
    sys.converter.dac.interpolation = 4 * 8

    mode_tx = "5"
    mode_rx = "6.0"

    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204b")
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204b")
    # sys.converter._skip_clock_validation = True  # slightly too slow for low rate
    # sys.converter._skip_clock_validation = True  # slightly too slow for low rate

    sys.converter.adc._check_clock_relations()
    sys.converter.dac._check_clock_relations()

    cfg = sys.solve()

    assert cfg["jesd_dac"]["bit_clock"] == 5e9
    assert cfg["jesd_adc"]["bit_clock"] == 5e9

    # cfg["fpga_dac"]["d"] = 1
    # cfg["fpga_adc"]["d"] = 2

    pprint.pprint(cfg)

    print("Mode passed: ", mode_tx, sys.converter.adc.decimation)
