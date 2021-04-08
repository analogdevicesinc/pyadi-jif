# flake8: noqa
import pprint

import pytest

import adijif


def print_sys(sys):
    print("----- Clock config:")
    for c in sys.clock.config:
        vs = sys.clock.config[c]
        if not isinstance(vs, list) and not isinstance(vs, dict):
            print(c, vs.value)
            continue
        for v in vs:
            if len(vs) > 1:
                print(c, v[0])
            else:
                print(c, v)

    print("----- FPGA config:")
    for c in sys.fpga.config:
        vs = sys.fpga.config[c]
        if not isinstance(vs, list) and not isinstance(vs, dict):
            print(c, vs.value)
            continue
        for v in vs:
            if len(vs) > 1:
                print(c, v[0])
            else:
                print(c, v)

    print("----- Converter config:")
    for c in sys.converter.config:
        vs = sys.converter.config[c]
        if not isinstance(vs, list) and not isinstance(vs, dict):
            print(c, vs.value)
            continue
        for v in vs:
            if len(vs) > 1:
                print(c, v[0])
            else:
                print(c, v)


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_fpga_cpll_solver(solver):

    vcxo = 125000000
    sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver=solver)
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.force_cpll = 1

    sys.converter.sample_clock = 1e9 / 2
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.converter.HD = 1

    if 0:
        # cnv_config = type("AD9680", (), {})()
        # cnv_config.bit_clock = 10e9/2
        required_clocks = sys.fpga.get_required_clocks(sys.converter)
        sys.clock.set_requested_clocks(vcxo, [required_clocks])

        sys.model.options.SOLVER = 1  # APOPT solver
        sys.model.solve(disp=False)
    else:
        sys.solve()

    # print_sys(sys)


def test_fpga_cpll_cplex_solver():

    vcxo = 125000000
    sys = adijif.system("ad9680", "ad9523_1", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.force_cpll = 1

    sys.converter.sample_clock = 1e9 / 2
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.converter.HD = 1

    if 0:
        # cnv_config = type("AD9680", (), {})()
        # cnv_config.bit_clock = 10e9/2
        required_clocks = sys.fpga.get_required_clocks(sys.converter)
        sys.clock.set_requested_clocks(vcxo, [required_clocks])

        sys.model.options.SOLVER = 1  # APOPT solver
        sys.model.solve(disp=False)
    else:
        o = sys.solve()

    print(o)


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
@pytest.mark.parametrize(
    "qpll, cpll, rate", [(0, 0, 1e9), (0, 1, 1e9 / 2), (1, 0, 1e9 / 2)]
)
@pytest.mark.parametrize("clock_chip", ["ad9523_1", "hmc7044", "ad9528"])
def test_ad9680_all_clk_chips_solver(qpll, cpll, rate, clock_chip, solver):

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

    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.force_cpll = cpll
    sys.fpga.force_qpll = qpll

    o = sys.solve()

    if qpll:
        assert o["fpga"]["type"] == "qpll"
        # assert sys.fpga.configs[0]["qpll_0_cpll_1"] == 0
    elif cpll:
        assert o["fpga"]["type"] == "cpll"
        # assert sys.fpga.configs[0]["qpll_0_cpll_1"] == 1

    # print_sys(sys)


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_ad9144_solver(solver):

    vcxo = 125000000
    sys = adijif.system("ad9144", "hmc7044", "xilinx", vcxo, solver=solver)
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.Debug_Solver = 1
    # sys.fpga.force_cpll = 1

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

    assert sys.converter.S == 1
    assert sys.converter.bit_clock == 10e9

    if 0:
        # cnv_config = type("AD9680", (), {})()
        # cnv_config.bit_clock = 10e9/2
        required_clocks = sys.fpga.get_required_clocks(sys.converter)
        sys.clock.set_requested_clocks(vcxo, [required_clocks])

        sys.model.options.SOLVER = 1  # APOPT solver
        sys.model.solve(disp=False)
    else:
        sys.solve()

    # print_sys(sys)


def test_daq2_split_rates_solver():
    vcxo = 125000000

    sys = adijif.system(["ad9680", "ad9144"], "ad9523_1", "xilinx", vcxo)
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.Debug_Solver = False
    # sys.fpga.request_device_clock = False

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

    # sys._try_fpga_configs()
    sys.solve()

    assert sys.fpga.configs[0]["qpll_0_cpll_1"].value[0] == 1  # CPLL
    assert sys.fpga.configs[1]["qpll_0_cpll_1"].value[0] == 0  # QPLL

    assert (
        sys.fpga.configs[0]["vco_select"].value[0]
        * 2
        / sys.fpga.configs[0]["d_select"].value[0]
        == sys.converter[0].bit_clock
    )

    print("----- FPGA config:")
    for c in sys.fpga.config:
        vs = sys.fpga.config[c]
        if not isinstance(vs, list) and not isinstance(vs, dict):
            print(c, vs.value)
            continue
        for v in vs:
            if len(vs) > 1:
                print(c, v[0])
            else:
                print(c, v)

    for conf in sys.fpga.configs:
        print("----- FPGA config:")
        for c in conf:
            vs = conf[c]
            if not isinstance(vs, list) and not isinstance(vs, dict):
                print(c, vs.value)
                continue
            for v in vs:
                if len(vs) > 1:
                    print(c, v[0])
                else:
                    print(c, v)
