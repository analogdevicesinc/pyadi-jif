import pprint

import pytest

import adijif


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_smoke_solver(solver):

    vcxo = 125000000
    sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver=solver)
    sys.fpga.setup_by_dev_kit_name("zc706")

    sys.converter.sample_clock = 1e9 / 2
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.converter.HD = 1

    sys.solve()


@pytest.mark.parametrize("solver", ["CPLEX"])
@pytest.mark.parametrize("converter", ["ad9680", "ad9144"])
@pytest.mark.parametrize("clockchip", ["ad9528", "hmc7044", "ad9523_1"])
@pytest.mark.parametrize("fpga_kit", ["zc706", "zcu102"])
def test_smoke_all_clocks(solver, converter, clockchip, fpga_kit):

    vcxo = 125000000
    sys = adijif.system(converter, clockchip, "xilinx", vcxo, solver=solver)
    sys.fpga.setup_by_dev_kit_name(fpga_kit)

    if converter == "ad9680":
        sys.converter.sample_clock = 1e9 / 2
        sys.converter.datapath_decimation = 1
        sys.converter.L = 4
        sys.converter.M = 2
        sys.converter.N = 14
        sys.converter.Np = 16
        sys.converter.K = 32
        sys.converter.F = 1
        sys.converter.HD = 1
    elif converter == "ad9144":
        sys.converter.sample_clock = 1e9
        # Mode 0
        sys.converter.datapath_interpolation = 1
        sys.converter.L = 8
        sys.converter.M = 4
        sys.converter.N = 16
        sys.converter.Np = 16
        sys.converter.K = 32
        sys.converter.F = 1
        sys.converter.HD = 1
        sys.converter.use_direct_clocking = False
    else:
        raise Exception("Unknown converter")

    sys.solve()


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
@pytest.mark.parametrize(
    "qpll, cpll, rate", [(0, 0, 1e9), (0, 1, 1e9 / 2), (1, 0, 1e9 / 2)]
)
@pytest.mark.parametrize("clock_chip", ["ad9523_1", "hmc7044", "ad9528"])
@pytest.mark.parametrize("fpga_kit", ["zc706", "zcu102"])
def test_ad9680_all_clk_chips_fpga_pll_modes_solver(
    qpll, cpll, rate, clock_chip, solver, fpga_kit
):

    if fpga_kit == "zcu102" and clock_chip == "hmc7044" and rate == 1e9:
        pytest.skip()

    vcxo = 125000000

    sys = adijif.system("ad9680", clock_chip, "xilinx", vcxo, solver=solver)

    # Get Converter clocking requirements
    sys.converter.sample_clock = rate
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.converter.HD = 1

    sys.fpga.setup_by_dev_kit_name(fpga_kit)
    sys.fpga.force_cpll = cpll
    sys.fpga.force_qpll = qpll
    sys.fpga.request_fpga_core_clock_ref = True

    try:
        o = sys.solve()
    except:
        sys.model = []
        del sys
        raise Exception("ERROR")
    sys.model = []
    del sys

    # Check
    if qpll:
        assert o["fpga_AD9680"]["type"] == "qpll"
    elif cpll:
        assert o["fpga_AD9680"]["type"] == "cpll"


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_daq2_split_rates_solver(solver):

    vcxo = 125000000
    sys = adijif.system(["ad9680", "ad9144"], "ad9523_1", "xilinx", vcxo, solver=solver)
    sys.fpga.setup_by_dev_kit_name("zc706")

    # Get Converter clocking requirements
    sys.converter[0].sample_clock = 1e9 / 2
    sys.converter[0].datapath_decimation = 1
    sys.converter[0].L = 4
    sys.converter[0].M = 2
    sys.converter[0].N = 14
    sys.converter[0].Np = 16
    sys.converter[0].K = 32
    sys.converter[0].F = 1
    sys.converter[0].HD = 1

    sys.converter[1].sample_clock = 1e9
    sys.converter[1].datapath_interpolation = 1
    sys.converter[1].L = 8
    sys.converter[1].M = 4
    sys.converter[1].N = 16
    sys.converter[1].Np = 16
    sys.converter[1].K = 32
    sys.converter[1].F = 1

    cfg = sys.solve()

    assert cfg["fpga_AD9680"]["type"] == "cpll"  # CPLL
    assert cfg["fpga_AD9144"]["type"] == "qpll"  # QPLL

    assert (
        cfg["fpga_AD9680"]["vco"] * 2 / cfg["fpga_AD9680"]["d"]
        == sys.converter[0].bit_clock
    )


def test_ad9680_clock_check1_solver():

    vcxo = 125000000
    sys = adijif.system("ad9680", "ad9523_1", "xilinx", vcxo)

    sys.fpga.request_fpga_core_clock_ref = True

    sys.converter.sample_clock = 1e9

    sys.fpga.setup_by_dev_kit_name("zc706")
    cfg = sys.solve()

    assert cfg["clock"]["n2"] == 48
    assert cfg["clock"]["r2"] == 2
    assert cfg["clock"]["m1"] == 3
    assert cfg["clock"]["output_clocks"]["AD9680_fpga_ref_clk"]["rate"] == 1e9 / 4
    assert cfg["fpga_AD9680"]["type"] == "qpll"


def test_ad9680_clock_check2_solver():

    vcxo = 125000000

    sys = adijif.system("ad9680", "ad9523_1", "xilinx", vcxo)

    sys.fpga.request_fpga_core_clock_ref = True

    # Get Converter clocking requirements
    sys.converter.sample_clock = 1e9
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.converter.HD = 1

    # Get FPGA clocking requirements
    sys.fpga.setup_by_dev_kit_name("zc706")

    cfg = sys.solve()

    clk_config = sys.clock.config
    print(clk_config)
    print(sys.converter.bit_clock / 40)
    divs = sys.clock.config["out_dividers"]
    assert clk_config["n2"][0] == 48
    assert clk_config["r2"][0] == 2
    assert clk_config["m1"][0] == 3
    assert cfg["clock"]["output_clocks"]["AD9680_fpga_ref_clk"]["rate"] == 250000000
    for div in divs:
        assert div[0] in [1, 4, 32]
