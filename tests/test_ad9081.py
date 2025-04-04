# flake8: noqa
import pprint

import pytest

import adijif


@pytest.mark.parametrize("part", ["ad9081_rx", "ad9082_rx"])
def test_ad9081_core_rx_solver(part):
    vcxo = 100000000

    sys = adijif.system(part, "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.Debug_Solver = False
    # sys.fpga.request_device_clock = False
    sys.fpga.force_qpll = True

    sys.converter.clocking_option = "integrated_pll"

    # Get Converter clocking requirements
    sys.converter.sample_clock = 250e6
    # sys.converter.decimation = 16
    sys.converter.datapath.cddc_decimations = [4, 4, 4, 4]
    sys.converter.datapath.fddc_decimations = [4, 4, 4, 4, 4, 4, 4, 4]
    sys.converter.datapath.fddc_enabled = [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]
    assert sys.converter.decimation == 16
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
    assert cfg["fpga_AD9081_RX"]["type"] == "qpll"


@pytest.mark.parametrize("part", ["ad9081_tx", "ad9082_tx"])
def test_ad9081_core_tx_solver(part):
    vcxo = 100000000

    sys = adijif.system(part, "hmc7044", "xilinx", vcxo)
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.Debug_Solver = False
    # sys.fpga.request_device_clock = False

    sys.converter.clocking_option = "integrated_pll"

    # Get Converter clocking requirements
    sys.converter.sample_clock = 250e6
    # sys.converter.interpolation = 48
    sys.converter.datapath.cduc_interpolation = 12
    sys.converter.datapath.fduc_interpolation = 4
    sys.converter.datapath.fduc_enabled = [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]
    assert sys.converter.interpolation == 48
    mode = adijif.utils.get_jesd_mode_from_params(
        sys.converter, L=4, M=8, Np=16, K=32, F=4
    )
    assert len(mode) == 1
    print(mode)
    jmode = mode[0]["mode"]
    jclass = mode[0]["jesd_class"]
    sys.converter.set_quick_configuration_mode(jmode, jclass)
    assert sys.converter.L == 4
    assert sys.converter.M == 8
    assert sys.converter.Np == 16
    assert sys.converter.K == 32
    assert sys.converter.F == 4
    assert sys.converter.S == 1

    # sys._try_fpga_configs()
    cfg = sys.solve()
    # pprint.pprint(cfg)

    assert cfg["fpga_AD9081_TX"]["type"] == "qpll"


@pytest.mark.parametrize("part", ["ad9081", "ad9082"])
def test_ad9081_core_rxtx_solver(part):
    vcxo = 100000000

    sys = adijif.system(part, "hmc7044", "xilinx", vcxo, solver="CPLEX")
    # sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo)
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.Debug_Solver = True
    # sys.fpga.request_device_clock = False
    sys.fpga.force_qpll = True

    sys.converter.dac.clocking_option = "integrated_pll"
    sys.converter.adc.clocking_option = "integrated_pll"
    sys.converter.clocking_option = "integrated_pll"

    # Get Converter clocking requirements
    sys.converter.dac.jesd_class = "jesd204b"
    sys.converter.dac.sample_clock = 250e6
    # sys.converter.dac.interpolation = 48
    sys.converter.dac.datapath.cduc_interpolation = 12
    sys.converter.dac.datapath.fduc_interpolation = 4
    sys.converter.dac.datapath.fduc_enabled = [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]
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
    # sys.converter.adc.decimation = 16
    sys.converter.adc.datapath.cddc_decimations = [4, 4, 4, 4]
    sys.converter.adc.datapath.fddc_decimations = [4, 4, 4, 4, 4, 4, 4, 4]
    sys.converter.adc.datapath.fddc_enabled = [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]
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

    # sys.converter.adc.decimation = 16
    # sys.converter.dac.interpolation = 48
    sys.converter.adc.datapath.cddc_decimations = [4, 4, 4, 4]
    sys.converter.dac.datapath.cduc_interpolation = 8
    sys.converter.adc.datapath.fddc_decimations = [4, 4, 4, 4, 4, 4, 4, 4]
    sys.converter.adc.datapath.fddc_enabled = [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]
    sys.converter.dac.datapath.fduc_interpolation = 6
    sys.converter.dac.datapath.fduc_enabled = [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]

    assert sys.converter.adc.decimation == 16
    assert sys.converter.dac.interpolation == 48

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

    # sys.converter.adc.decimation = 4 * 8
    # sys.converter.dac.interpolation = 4 * 8
    sys.converter.adc.datapath.cddc_decimations = [4, 4, 4, 4]
    sys.converter.dac.datapath.cduc_interpolation = 4
    sys.converter.adc.datapath.fddc_decimations = [8, 8, 8, 8, 8, 8, 8, 8]
    sys.converter.dac.datapath.fduc_interpolation = 8
    sys.converter.adc.datapath.fddc_enabled = [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]
    sys.converter.dac.datapath.fduc_enabled = [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]

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

    # pprint.pprint(cfg)

    print("Mode passed: ", mode_tx, sys.converter.adc.decimation)


def test_ad9081_np16_verify_no_extra_link_clock():
    vcxo = 100e6

    sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zcu102")
    # sys.fpga.sys_clk_select = "GTH34_SYSCLK_QPLL0"  # Use faster QPLL
    sys.Debug_Solver = False
    sys.converter.clocking_option = "integrated_pll"
    # sys.fpga.out_clk_select = "XCVR_REFCLK"  # force reference to be core clock rate
    sys.converter.adc.sample_clock = 4000000000 / (4 * 8)
    sys.converter.dac.sample_clock = 4000000000 / (4 * 8)

    # sys.converter.adc.decimation = 4 * 8
    # sys.converter.dac.interpolation = 4 * 8
    sys.converter.adc.datapath.cddc_decimations = [4, 4, 4, 4]
    sys.converter.dac.datapath.cduc_interpolation = 4
    sys.converter.adc.datapath.fddc_decimations = [8, 8, 8, 8, 8, 8, 8, 8]
    sys.converter.dac.datapath.fduc_interpolation = 8
    sys.converter.adc.datapath.fddc_enabled = [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]
    sys.converter.dac.datapath.fduc_enabled = [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]

    mode_tx = "5"
    mode_rx = "6.0"

    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204b")
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204b")
    assert sys.converter.adc.Np == 16
    assert sys.converter.dac.Np == 16

    sys.converter.adc._check_clock_relations()
    sys.converter.dac._check_clock_relations()

    cfg = sys.solve()

    assert cfg["jesd_dac"]["bit_clock"] == 5e9
    assert cfg["jesd_adc"]["bit_clock"] == 5e9

    # cfg["fpga_dac"]["d"] = 1
    # cfg["fpga_adc"]["d"] = 2

    # pprint.pprint(cfg)

    assert cfg["fpga_dac"]["device_clock_source"] == "external"
    assert cfg["fpga_adc"]["device_clock_source"] == "external"


def test_ad9081_np12_verify_extra_link_clock():
    # Reference https://github.com/analogdevicesinc/linux/blob/master/arch/microblaze/boot/dts/vcu118_quad_ad9081_204c_txmode_23_rxmode_25_revc.dts
    vcxo = 100e6

    sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("vcu118")
    sys.Debug_Solver = False
    sys.converter.clocking_option = "integrated_pll"
    sys.converter.adc.sample_clock = 4000000000 / (2 * 1)
    sys.converter.dac.sample_clock = 12000000000 / (6 * 1)
    sys.fpga.out_clk_select = (
        "XCVR_PROGDIV_CLK"  # force reference to be core clock rate
    )

    # sys.converter.adc.decimation = 2 * 1
    # sys.converter.dac.interpolation = 6 * 1
    sys.converter.adc.datapath.cddc_decimations = [2, 2, 2, 2]
    sys.converter.dac.datapath.cduc_interpolation = 6
    sys.converter.adc.datapath.fddc_decimations = [1, 1, 1, 1, 1, 1, 1, 1]
    sys.converter.dac.datapath.fduc_interpolation = 1

    mode_tx = "23"
    mode_rx = "25.0"

    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204c")
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204c")

    sys.converter.adc._check_clock_relations()
    sys.converter.dac._check_clock_relations()

    assert sys.converter.dac.M == 4
    assert sys.converter.dac.F == 3
    assert sys.converter.dac.K == 256
    assert sys.converter.dac.Np == 12
    assert sys.converter.dac.CS == 0
    assert sys.converter.dac.L == 4
    assert sys.converter.dac.S == 2
    assert sys.converter.dac.HD == 0

    assert sys.converter.adc.M == 4
    assert sys.converter.adc.F == 3
    assert sys.converter.adc.K == 256
    assert sys.converter.adc.Np == 12
    assert sys.converter.adc.CS == 0
    assert sys.converter.adc.L == 4
    assert sys.converter.adc.S == 2
    assert sys.converter.adc.HD == 0

    cfg = sys.solve()
    pprint.pprint(cfg)

    assert cfg["fpga_dac"]["device_clock_source"] == "external"
    assert cfg["fpga_adc"]["device_clock_source"] == "external"

    assert cfg["jesd_dac"]["bit_clock"] == 24750000000
    assert cfg["jesd_adc"]["bit_clock"] == 24750000000

    assert cfg["fpga_adc"]["out_clk_select"] == "XCVR_PROGDIV_CLK"

    if cfg["fpga_adc"]["sys_clk_select"] in ["CPLL", "QPLL", "QPLL0", "QPLL1"]:
        in_clock_rate = cfg["fpga_adc"]["bit_clock"]
    elif cfg["fpga_adc"]["sys_clk_select"] == "XCVR_PROGDIV_CLK":
        in_clock_rate = cfg["fpga_adc"]["bit_clock"] / 66
    assert (
        cfg["jesd_adc"]["bit_clock"] / cfg["fpga_adc"]["progdiv"]
        == cfg["jesd_adc"]["bit_clock"] / 66
    )

    assert (
        cfg["fpga_adc"]["transport_samples_per_clock"]
        * cfg["clock"]["output_clocks"]["vcu118_adc_device_clk"]["rate"]
        == sys.converter.adc.sample_clock
    )


def test_ad9081_zc706_gtx_gap():
    # Determine AD9081+ZCU102 Configuration For RX and TX contrained together

    import pprint

    import adijif

    vcxo = 100e6

    sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.ref_clock_constraint = "Unconstrained"
    # sys.fpga.sys_clk_select = "GTH34_SYSCLK_QPLL0"  # Use faster QPLL
    # sys.fpga.sys_clk_select = "CPLL"  # Use faster QPLL

    sys.converter.clocking_option = "integrated_pll"
    # sys.fpga.out_clk_select = "XCVR_PROGDIV_CLK"  # force reference to be core clock rate
    # sys.converter.adc.sample_clock = 4000000000 / (4 * 4)
    # sys.converter.dac.sample_clock = 12000000000 / (8 * 6)
    sys.converter.adc.sample_clock = 4000000000 * (232 / 250) / (4 * 4)
    sys.converter.dac.sample_clock = 12000000000 * (232 / 250) / (8 * 6)
    # sys.converter.adc.sample_clock = 4000000000 * (0.1) / (4 * 4)
    # sys.converter.dac.sample_clock = 12000000000 * (0.1) / (8 * 6)

    sys.converter.adc.datapath.cddc_decimations = [4] * 4
    sys.converter.adc.datapath.fddc_decimations = [4] * 8
    sys.converter.adc.datapath.fddc_enabled = [True] * 8
    sys.converter.dac.datapath.cduc_interpolation = 8
    sys.converter.dac.datapath.fduc_interpolation = 6
    sys.converter.dac.datapath.fduc_enabled = [True] * 8

    mode_tx = "9"
    mode_rx = "10.0"  # why are these requiredmM, is it possible to find the mode based on JSED parameters?

    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204b")
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204b")

    """
    assert sys.converter.adc.M == 8
    assert sys.converter.adc.F == 4
    assert sys.converter.adc.K == 32
    assert sys.converter.adc.Np == 16
    assert sys.converter.adc.CS == 0
    assert sys.converter.adc.L == 4
    assert sys.converter.adc.S == 1
    """
    print(sys.converter.adc.bit_clock)
    print(sys.converter.dac.bit_clock)

    sys.converter.adc._check_clock_relations()
    sys.converter.dac._check_clock_relations()

    with pytest.raises(Exception, match=".*No solution found.*"):
        cfg = sys.solve()
