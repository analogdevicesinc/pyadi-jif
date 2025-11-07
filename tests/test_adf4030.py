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


def test_adf4030_chained_clocks():
    import adijif

    L = 2  # max_available_lanes_per_ad9084_side
    M = 4  # Converters used to AD9084 side
    Np = 16  # Bits per sample

    vcxo = int(400e6)
    cddc_dec = 4
    fddc_dec = 8
    converter_rate = int(12.8e9)

    sys = adijif.system("ad9084_rx", "ltc6952", "xilinx", vcxo, solver="CPLEX")

    sys.fpga.setup_by_dev_kit_name("vcu118")
    sys.converter.sample_clock = converter_rate / (cddc_dec * fddc_dec)
    sys.converter.datapath.cddc_decimations = [cddc_dec] * 4
    sys.converter.datapath.fddc_decimations = [fddc_dec] * 8
    sys.converter.datapath.fddc_enabled = [True] * 8

    sys.converter.clocking_option = "direct"
    sys.add_pll_inline("adf4382", vcxo, sys.converter)
    # IMPLEMENTATION HERE
    sys.add_pll_sysref("adf4030", sys.clock, sys.converter, sys.fpga)

    sys.clock.minimize_feedback_dividers = False

    mode_rx = adijif.utils.get_jesd_mode_from_params(
        sys.converter, M=M, L=L, Np=Np, jesd_class="jesd204c"
    )
    print(f"RX JESD Mode: {mode_rx}")
    assert mode_rx
    mode_rx = mode_rx[0]["mode"]

    sys.converter.set_quick_configuration_mode(mode_rx, "jesd204c")

    print(f"Lane rate: {sys.converter.bit_clock/1e9} Gbps")
    print(f"Needed Core clock: {sys.converter.bit_clock/66} MHz")

    assert sys.converter.bit_clock == int(13.2e9)

    cfg = sys.solve()

    pprint.pprint(cfg)
    # 'clock_ext_pll_sysref_adf4030': {'n': 155,
    #                               'out_dividers': [4030],
    #                               'output_clocks': {'AD9084_RX_sysref': {'divider': 4030,
    #                                                                      'rate': 591715.976331361}},
    #                               'r': 13,
    #                               'vco': 2384615384.6153846},

    # Verify sysref is within LMFC
    mfc = sys.converter.multiframe_clock
    estimate = cfg["clock_ext_pll_sysref_adf4030"]["output_clocks"]["AD9084_RX_sysref"][
        "rate"
    ]
    for lmfc_div in range(1, 21):
        sysref_rate = mfc / lmfc_div
        if sysref_rate == estimate:
            print(f"Found sysref match: {sysref_rate} with divisor {lmfc_div}")
            return


def test_adf4030_with_arb_source():
    """Test ADF4030 with arb_source input_ref."""
    input_ref = jif.types.arb_source(
        "ref_in", a_min=90000000, a_max=110000000, b_min=1, b_max=1
    )

    sync = jif.adf4030(solver="CPLEX")

    output_clocks = [2.5e6]
    output_clocks = list(map(int, output_clocks))
    clock_names = ["SYSREF"]

    sync.set_requested_clocks(input_ref, output_clocks, clock_names)

    sync.solve()

    o = sync.get_config()

    assert o["output_clocks"]["SYSREF"]["rate"] == output_clocks[0]
    assert isinstance(o["vco"], (int, float))


def test_adf4030_with_range():
    """Test ADF4030 with range input_ref."""
    input_ref = jif.types.range(90000000, 110000000, 5000000, "ref_in")

    sync = jif.adf4030(solver="CPLEX")

    output_clocks = [2.5e6]
    output_clocks = list(map(int, output_clocks))
    clock_names = ["SYSREF"]

    sync.set_requested_clocks(input_ref, output_clocks, clock_names)

    sync.solve()

    o = sync.get_config()

    assert o["output_clocks"]["SYSREF"]["rate"] == output_clocks[0]
    assert isinstance(o["vco"], (int, float))
