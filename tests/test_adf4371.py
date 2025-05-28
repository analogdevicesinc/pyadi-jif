# flake8: noqa
import pprint

import pytest

import adijif


def test_adf4371_datasheet_example():
    pll = adijif.adf4371()
    pll._MOD2 = 1536
    pll.rf_div = 2
    pll.mode = "fractional"

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

    assert int(vco) == int(2112.8e6 * rf_div)
    assert int(vco / rf_div) == int(output_clocks)


def test_adf4371_ad9081_sys_example():
    vcxo = 100e6
    cddc = 6
    fddc = 4

    sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zcu102")
    sys.fpga.ref_clock_constraint = "Unconstrained"
    sys.fpga.sys_clk_select = "XCVR_QPLL0"  # Use faster QPLL
    sys.fpga.out_clk_select = (
        "XCVR_PROGDIV_CLK"  # force reference to be core clock rate
    )
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

    pprint.pprint(cfg)
    print(sys.converter.dac.converter_clock)

    assert float(cfg["clock_ext_pll_adf4371"]["rf_out_frequency"]) == float(
        sys.converter.dac.converter_clock
    ), f"{cfg['clock_ext_pll_adf4371']['rf_out_frequency']} != {sys.converter.dac.converter_clock}"


@pytest.mark.parametrize(
    "mode",
    [
        "integer",
        "fractional",
        ["integer", "fractional"],
    ],
)
@pytest.mark.parametrize(
    "int_prescaler",
    ["4/5", "8/9", ["4/5", "8/9"]],
)
def test_adf4371_vary_modes(mode, int_prescaler):
    pll = adijif.adf4371()
    pll.mode = mode
    pll._prescaler = int_prescaler

    # ref_in = int(122.88e6*2)
    # output_clocks = int(2112.8e6)
    ref_in = int(10e6)
    output_clocks = int(100e6)

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

    assert int(vco) == int(output_clocks * rf_div)


def test_adf4371_touch_all_properties():
    pll = adijif.adf4371()

    # read/write all
    pll.mode = pll.mode
    pll._prescaler = pll._prescaler
    pll.d = pll.d
    pll.r = pll.r
    pll.t = pll.t
    pll.rf_div = pll.rf_div

    # Manually set
    pll.mode = ["integer", "fractional"]
    pll._prescaler = ["4/5", "8/9", ["4/5", "8/9"]]
    pll.d = 0
    pll.r = 32
    pll.t = 0
    pll.rf_div = 2

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

    assert rf_div == 2
    assert int(vco) == int(2112.8e6 * rf_div)
    assert int(vco / rf_div) == int(output_clocks)


def test_wrong_solver():
    msg = "Only CPLEX solver is implemented"
    with pytest.raises(Exception, match=msg):
        pll = adijif.adf4371(solver="gekko")
        pll._MOD2 = 1536
        pll.rf_div = 2
        pll.mode = "fractional"

        ref_in = int(122.88e6)
        output_clocks = int(2112.8e6)

        pll.set_requested_clocks(ref_in, output_clocks)

        pll.solve()


def test_clock_names_not_set():
    msg = "set_requested_clocks must be called before get_config"
    with pytest.raises(Exception, match=msg):
        pll = adijif.adf4371()
        pll._MOD2 = 1536
        pll.rf_div = 2
        pll.mode = "fractional"

        ref_in = int(122.88e6)
        output_clocks = int(2112.8e6)

        pll.set_requested_clocks(ref_in, output_clocks)

        pll.solve()

        pll._clk_names = None

        pll.get_config()
