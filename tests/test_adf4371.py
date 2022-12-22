# flake8: noqa
import pprint

import pytest

import adijif


def test_adf4371_datasheet_example():

    pll = adijif.adf4371()
    pll._MOD2 = 1536
    pll.rf_div = 2
    pll._mode = "fractional"

    ref_in = int(122.88e6)
    output_clocks = int(2112.8e6)

    pll.set_requested_clocks(ref_in, output_clocks)

    pll.solve()

    o = pll.get_config()

    pprint.pprint(o)

    D = o["d"]
    R = o["r"]
    T = o["t"]
    INT = o["int"]
    FRAC1 = o["frac1"]
    FRAC2 = o["frac2"]
    MOD2 = o["MOD2"]
    rf_div = o["rf_div"]

    MOD1 = 2**25

    F_PFD = ref_in * (1 + D) / (R * (1 + T))
    vco = (INT + (FRAC1 + FRAC2 / MOD2) / MOD1) * F_PFD

    assert vco == 2112.8e6 * rf_div
    assert vco / rf_div == float(output_clocks)


def test_adf4371_ad9081_sys_example():

    vcxo = 100e6

    sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zcu102")
    sys.fpga.sys_clk_select = "GTH34_SYSCLK_QPLL0"  # Use faster QPLL
    sys.fpga.out_clk_select = (
        "XCVR_PROGDIV_CLK"  # force reference to be core clock rate
    )
    sys.converter.adc.sample_clock = 2900000000 / (8 * 6)
    sys.converter.dac.sample_clock = 5800000000 / (4 * 12)
    sys.converter.adc.decimation = 8 * 6
    sys.converter.dac.interpolation = 4 * 12

    sys.converter.clocking_option = "direct"
    sys.add_pll_inline("adf4371", sys.clock, sys.converter)

    mode_tx = "0"
    mode_rx = "1.0"

    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204c")
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204c")

    assert sys.converter.adc.M == 8
    assert sys.converter.adc.F == 12
    assert sys.converter.adc.K == 64
    assert sys.converter.adc.Np == 12
    assert sys.converter.adc.CS == 0
    assert sys.converter.adc.L == 1
    assert sys.converter.adc.S == 1

    sys.converter.adc._check_clock_relations()
    sys.converter.dac._check_clock_relations()

    cfg = sys.solve()

    # pprint.pprint(cfg)

    assert cfg["pll_adf4371"]["rf_out_frequency"] == sys.converter.dac.converter_clock
