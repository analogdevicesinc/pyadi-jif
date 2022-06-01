"""Tests for JESD mode automatic solver feature."""

# import numpy as np
from pprint import pprint

import pytest

import adijif


def test_ad9680_vs_manual():
    # Compare selecting AD9680 automatic JESD mode select vs manual
    vcxo = 125000000

    sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo)

    # This case needs to be removed since 136 and 137 reduce to the same lane
    # rate, so either are valid
    del sys.converter.quick_configuration_modes["jesd204b"]["137"]

    # Get Converter clocking requirements
    sys.converter.sample_clock = 1e9
    sys.converter.decimation = 1
    sys.converter.jesd_solve_mode = "auto"
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.force_qpll = 1
    cfg_auto = sys.solve()
    del sys

    sys2 = adijif.system("ad9680", "hmc7044", "xilinx", vcxo)

    # Get Converter clocking requirements
    sys2.converter.sample_clock = 1e9
    sys2.converter.decimation = 1
    sys2.fpga.setup_by_dev_kit_name("zc706")
    sys2.fpga.force_qpll = 1
    sys2.converter.set_quick_configuration_mode(str(0x88))
    sys2.converter.K = 32
    cfg_ref = sys2.solve()

    pprint(cfg_auto)
    pprint(cfg_ref)

    assert cfg_auto == cfg_ref


def test_ad9081_rx_vs_manual():
    print(adijif.ad9081_rx.quick_configuration_modes.keys())
    # Compare selecting AD9680 automatic JESD mode select vs manual
    vcxo = int(100e6)

    sys = adijif.system("ad9081_rx", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zcu102")
    sys.fpga.sys_clk_select = "GTH34_SYSCLK_QPLL0"  # Use faster QPLL
    # sys.Debug_Solver = True
    sys.converter.clocking_option = "integrated_pll"
    sys.fpga.out_clk_select = "XCVR_REFCLK"  # force reference to be core clock rate
    sys.converter.sample_clock = 2900000000 / (8 * 6)
    sys.converter.decimation = 8 * 6

    # This case needs to be removed since 136 and 137 reduce to the same lane
    # rate, so either are valid
    qcm = sys.converter.quick_configuration_modes.copy()
    del sys.converter.quick_configuration_modes["jesd204b"]
    sys.converter.available_jesd_modes = ["jesd204c"]
    # sys.

    sys.converter.jesd_solve_mode = "auto"
    sys.fpga.force_qpll = 1
    cfg_auto = sys.solve()
    assert cfg_auto
    del sys
    print(adijif.ad9081_rx.quick_configuration_modes.keys())
    adijif.ad9081_rx.quick_configuration_modes = qcm

    ###########################################################################

    sys = adijif.system("ad9081_rx", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zcu102")
    sys.fpga.sys_clk_select = "GTH34_SYSCLK_QPLL0"  # Use faster QPLL
    sys.Debug_Solver = True
    sys.converter.clocking_option = "integrated_pll"
    sys.fpga.out_clk_select = "XCVR_REFCLK"  # force reference to be core clock rate
    sys.converter.sample_clock = 2900000000 / (8 * 6)
    sys.converter.decimation = 8 * 6

    sys.converter.jesd_solve_mode = "manual"
    sys.converter.set_quick_configuration_mode("1.0", "jesd204c")
    sys.fpga.force_qpll = 1
    cfg_ref = sys.solve()
    assert cfg_ref
    del sys

    # # Get Converter clocking requirements
    # sys2.converter.sample_clock = 1e9
    # sys2.converter.decimation = 1
    # sys2.fpga.setup_by_dev_kit_name("zc706")
    # sys2.fpga.force_qpll = 1
    # sys2.converter.set_quick_configuration_mode("1.0")
    # sys2.converter.K = 32
    # cfg_ref = sys2.solve()

    pprint(cfg_auto)
    pprint(cfg_ref)

    assert cfg_auto == cfg_ref
