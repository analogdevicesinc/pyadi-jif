# flake8: noqa
import pprint

import adijif as jif


def test_adf4030_sysref_example():
    ref_in = int(100e6)

    sync = jif.adf4030()

    output_clocks = [
        2.5e6,
    ]
    output_clocks = list(map(int, output_clocks))  # force to be ints
    clock_names = [
        "SYSREF",
    ]

    sync.set_requested_clocks(ref_in, output_clocks, clock_names)

    sync.solve()

    o = sync.get_config()

    pprint.pprint(o)

    assert o["output_clocks"]["SYSREF"]["rate"] == output_clocks[0]
    assert o["output_clocks"]["SYSREF"]["divider"] == 992


def test_adf4030_system():
    vcxo = 100e6

    import adijif

    sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zcu102")
    sys.fpga.ref_clock_constraint = "Unconstrained"
    sys.fpga.sys_clk_select = "SYSCLK_QPLL0"  # Use faster QPLL
    sys.fpga.out_clk_select = (
        "XCVR_PROGDIV_CLK"  # force reference to be core clock rate
    )
    cddc = 6
    fddc = 4
    sys.converter.adc.sample_clock = 2900000000 / (cddc * fddc)
    sys.converter.dac.sample_clock = 5800000000 / (cddc * fddc)
    # sys.converter.adc.decimation = 8 * 6
    # sys.converter.dac.interpolation = 4 * 12
    sys.converter.adc.datapath.cddc_decimations = [cddc] * 4
    sys.converter.adc.datapath.fddc_decimations = [fddc] * 8
    sys.converter.adc.datapath.fddc_enabled = [True] * 8
    sys.converter.dac.datapath.cduc_interpolation = cddc
    sys.converter.dac.datapath.fduc_interpolation = fddc
    sys.converter.dac.datapath.fduc_enabled = [True] * 8
    assert sys.converter.dac.interpolation == cddc * fddc

    # sys.converter.clocking_option = "direct"
    # sys.add_pll_inline("adf4371", sys.clock, sys.converter)
    sys.add_pll_sysref("adf4030", vcxo, sys.converter, sys.fpga)

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

    pprint.pprint(cfg)
    print(sys.converter.dac.converter_clock)
