# flake8: noqa
import pprint

import pytest

try:
    from gekko import GEKKO  # type: ignore
except ImportError:
    GEKKO = None

import adijif


def skip_solver(solver):
    if solver.lower() == "gekko" and GEKKO is None:
        pytest.skip("Gekko not available")


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_ad9545_validate_fail(solver):
    msg = r"Solution Not Found"

    skip_solver(solver)

    with pytest.raises(Exception, match=msg):
        clk = adijif.ad9545(solver=solver)

        clk.avoid_min_max_PLL_rates = True
        clk.minimize_input_dividers = True

        input_refs = [(0, 42345235)]
        output_clocks = [(0, 3525235234123)]

        input_refs = list(map(lambda x: (int(x[0]), int(x[1])), input_refs))
        output_clocks = list(map(lambda x: (int(x[0]), int(x[1])), output_clocks))

        clk.set_requested_clocks(input_refs, output_clocks)

        clk.solve()


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
@pytest.mark.parametrize("out_freq", [30720000, 25e6])
def test_ad9545_validate_pass(solver, out_freq):
    skip_solver(solver)
    clk = adijif.ad9545(solver=solver)

    clk.avoid_min_max_PLL_rates = True
    clk.minimize_input_dividers = True

    input_refs = [(0, 1), (1, 10e6)]
    output_clocks = [(0, int(out_freq))]

    input_refs = list(map(lambda x: (int(x[0]), int(x[1])), input_refs))
    output_clocks = list(map(lambda x: (int(x[0]), int(x[1])), output_clocks))

    clk.set_requested_clocks(input_refs, output_clocks)

    clk.solve()
    sol = clk.get_config()

    PLLs_used = [False, False]
    for out_clock in output_clocks:
        if out_clock[0] > 5:
            PLLs_used[1] = True
        else:
            PLLs_used[0] = True

    for in_ref in input_refs:
        for pll_number in range(0, 2):
            if PLLs_used[pll_number]:
                pll_rate = sol["PLL" + str(pll_number)]["rate_hz"]
                n_name = "n" + str(pll_number) + "_profile_" + str(in_ref[0])
                assert (
                    pll_rate
                    == (in_ref[1] // sol["r" + str(in_ref[0])])
                    * sol["PLL" + str(pll_number)][n_name]
                )

    for out_clock in output_clocks:
        if out_clock[0] > 5:
            pll_rate = sol["PLL1"]["rate_hz"]
        else:
            pll_rate = sol["PLL0"]["rate_hz"]

        assert out_clock[1] == pll_rate / sol["q" + str(out_clock[0])]


def test_ad9545_fail_no_solver():
    with pytest.raises(Exception, match=r"Unknown solver NAN"):
        clk = adijif.ad9545(solver="NAN")

        input_refs = [(0, 1), (1, 10e6)]
        output_clocks = [(0, 30720000)]

        input_refs = list(map(lambda x: (int(x[0]), int(x[1])), input_refs))
        output_clocks = list(map(lambda x: (int(x[0]), int(x[1])), output_clocks))

        clk.set_requested_clocks(input_refs, output_clocks)

        clk.solve()


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_ad9523_1_daq2_validate(solver):
    skip_solver(solver)
    vcxo = 125000000
    n2 = 24

    clk = adijif.ad9523_1(solver=solver)

    # Check config valid
    clk.n2 = n2
    clk.use_vcxo_double = False

    output_clocks = [1e9, 500e6, 7.8125e6]
    clock_names = ["ADC", "FPGA", "SYSREF"]

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    clk.solve()

    o = clk.get_config()

    assert sorted(o["out_dividers"]) == [1, 2, 128]
    assert o["m1"] == 3
    assert o["m1"] in clk.m1_available
    assert o["n2"] == n2
    assert o["n2"] in clk.n2_available
    assert o["r2"] == 1
    assert o["r2"] in clk.r2_available

    assert o["output_clocks"]["ADC"] == {"divider": 1, "rate": 1000000000.0}
    assert o["output_clocks"]["FPGA"] == {"divider": 2, "rate": 500000000.0}
    assert o["output_clocks"]["SYSREF"] == {"divider": 128, "rate": 7812500.0}


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_ad9523_1_daq2_validate_fail(solver):
    skip_solver(solver)
    msg = r"Solution Not Found"

    with pytest.raises(Exception, match=msg):
        vcxo = 125000000
        n2 = 12

        clk = adijif.ad9523_1(solver=solver)

        # Check config valid
        clk.n2 = n2
        # clk.r2 = 1
        clk.use_vcxo_double = False
        # clk.m = 3

        output_clocks = [1e9, 500e6, 7.8125e6]
        clock_names = ["ADC", "FPGA", "SYSREF"]

        clk.set_requested_clocks(vcxo, output_clocks, clock_names)

        o = clk.solve()

        print(o)

        assert sorted(o["out_dividers"]) == [
            2,
            4,
            256,
        ]  # This seems weird but its different per CPLEX version
        assert o["n2"] == n2


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_ad9523_1_daq2_variable_vcxo_validate(solver):
    skip_solver(solver)
    vcxo = adijif.types.range(100000000, 126000000, 1000000, "vcxo")
    n2 = 24

    clk = adijif.ad9523_1(solver=solver)

    # Check config valid
    clk.n2 = n2
    clk.use_vcxo_double = False

    output_clocks = [1e9, 500e6, 7.8125e6]
    clock_names = ["ADC", "FPGA", "SYSREF"]

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    clk.solve()

    o = clk.get_config()

    print(o)

    assert sorted(o["out_dividers"]) == [1, 2, 128]
    assert o["m1"] == 3
    assert o["m1"] in clk.m1_available
    assert o["n2"] == n2
    assert o["n2"] in clk.n2_available
    assert o["r2"] == 1
    assert o["r2"] in clk.r2_available
    assert o["output_clocks"]["ADC"]["rate"] == 1e9
    assert o["vcxo"] == 125000000


def test_ad9523_1_fail_no_solver():
    with pytest.raises(Exception, match=r"Unknown solver NAN"):
        clk = adijif.ad9523_1(solver="NAN")
        output_clocks = [1e9, 500e6, 7.8125e6]
        clock_names = ["ADC", "FPGA", "SYSREF"]
        clk.set_requested_clocks(vcxo, output_clocks, clock_names)
        clk.solve()


def test_ad9523_1_fail_no_solver2():
    with pytest.raises(Exception, match=r"Unknown solver NAN2"):
        vcxo = 125000000
        clk = adijif.ad9523_1()
        clk.solver = "NAN2"
        output_clocks = [1e9, 500e6, 7.8125e6]
        clock_names = ["ADC", "FPGA", "SYSREF"]
        clk.set_requested_clocks(vcxo, output_clocks, clock_names)
        clk.solve()


def test_ad9523_1_fail_no_solver3():
    with pytest.raises(Exception, match=r"Unknown solver NAN3"):
        vcxo = 125000000
        clk = adijif.ad9523_1()
        output_clocks = [1e9, 500e6, 7.8125e6]
        clock_names = ["ADC", "FPGA", "SYSREF"]
        clk.set_requested_clocks(vcxo, output_clocks, clock_names)
        clk.solver = "NAN3"
        clk.solve()


def test_system_fail_no_solver3():
    with pytest.raises(Exception, match=r"Unknown solver NAN4"):
        vcxo = 125000000
        sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver="NAN4")
        sys.solve()


def test_ltc6953_validate():
    ref_in = adijif.types.range(1000000000, 4500000000, 1000000, "ref_in")

    clk = adijif.ltc6953(solver="CPLEX")

    output_clocks = [1e9, 500e6, 7.8125e6]
    print(output_clocks)
    output_clocks = list(map(int, output_clocks))  # force to be ints
    clock_names = ["ADC", "FPGA", "SYSREF"]

    clk.set_requested_clocks(ref_in, output_clocks, clock_names)

    clk.solve()

    o = clk.get_config()

    assert sorted(o["out_dividers"]) == [2, 4, 256]
    assert o["input_ref"] == 2000000000


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_ad9528_validate(solver):
    skip_solver(solver)
    n2 = 10
    vcxo = 122.88e6

    clk = adijif.ad9528(solver=solver)

    clk.n2 = n2
    clk.use_vcxo_double = False

    output_clocks = [245.76e6, 245.76e6]
    output_clocks = list(map(int, output_clocks))
    clock_names = ["ADC", "FPGA"]

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    clk.solve()
    o = clk.get_config()

    assert sorted(o["out_dividers"]) == [5, 5]
    assert o["m1"] == 3
    assert o["m1"] in clk.m1_available
    assert o["n2"] == n2
    assert o["n2"] in clk.n2_available
    assert o["output_clocks"]["ADC"]["rate"] == 245.76e6
    assert o["output_clocks"]["FPGA"]["rate"] == 245.76e6
    assert o["vcxo"] == vcxo
    assert o["vco"] == 3686400000.0


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_ad9528_sysref(solver):
    skip_solver(solver)
    n2 = 10
    vcxo = 122.88e6

    clk = adijif.ad9528(solver=solver)

    clk.n2 = n2
    clk.k = [*range(500, 600)]  # FIXME gekko fails to find a solution without this.
    clk.use_vcxo_double = False

    clk.sysref = 120e3

    output_clocks = [245.76e6, 245.76e6]
    output_clocks = list(map(int, output_clocks))
    clock_names = ["ADC", "FPGA"]

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    clk.solve()
    o = clk.get_config()

    assert o["k"] == 512
    assert o["sysref"] == 120e3


# Tests for arb_source support
def test_ad9523_1_arb_source_vcxo():
    """Test AD9523-1 with arb_source vcxo."""
    vcxo = adijif.types.arb_source(
        "vcxo", a_min=100000000, a_max=150000000, b_min=1, b_max=1
    )
    n2 = 24

    clk = adijif.ad9523_1(solver="CPLEX")

    clk.n2 = n2
    clk.use_vcxo_double = False

    output_clocks = [1e9, 500e6, 7.8125e6]
    clock_names = ["ADC", "FPGA", "SYSREF"]

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    clk.solve()

    o = clk.get_config()

    assert sorted(o["out_dividers"]) == [1, 2, 128]
    assert o["n2"] == n2
    assert o["vcxo"] == 125000000  # Should find optimal vcxo


def test_ad9528_arb_source_vcxo():
    """Test AD9528 with arb_source vcxo."""
    vcxo = adijif.types.arb_source(
        "vcxo", a_min=100000000, a_max=150000000, b_min=1, b_max=1
    )

    clk = adijif.ad9528(solver="CPLEX")

    clk.use_vcxo_double = False

    output_clocks = [245.76e6, 245.76e6]
    output_clocks = list(map(int, output_clocks))
    clock_names = ["ADC", "FPGA"]

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    clk.solve()
    o = clk.get_config()

    assert isinstance(o["vcxo"], (int, float))
    assert 100000000 <= o["vcxo"] <= 150000000


def test_hmc7044_arb_source_vcxo():
    """Test HMC7044 with arb_source vcxo."""
    vcxo = adijif.types.arb_source(
        "vcxo", a_min=100000000, a_max=150000000, b_min=1, b_max=1
    )

    clk = adijif.hmc7044(solver="CPLEX")

    clk.use_vcxo_double = True

    output_clocks = [245.76e6, 245.76e6]
    output_clocks = list(map(int, output_clocks))
    clock_names = ["ADC", "FPGA"]

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    clk.solve()
    o = clk.get_config()

    assert isinstance(o["vcxo"], (int, float))
    assert 100000000 <= o["vcxo"] <= 150000000


def test_ltc6953_arb_source_input_ref():
    """Test LTC6953 with arb_source input_ref."""
    input_ref = adijif.types.arb_source(
        "ref_in", a_min=1000000000, a_max=2000000000, b_min=1, b_max=1
    )

    clk = adijif.ltc6953(solver="CPLEX")

    output_clocks = [1e9, 500e6]
    output_clocks = list(map(int, output_clocks))
    clock_names = ["ADC", "FPGA"]

    clk.set_requested_clocks(input_ref, output_clocks, clock_names)

    clk.solve()

    o = clk.get_config()

    assert isinstance(o["input_ref"], (int, float))
    assert 1000000000 <= o["input_ref"] <= 2000000000


def test_system_with_arb_source_vcxo():
    """Test system class with arb_source vcxo."""
    vcxo = adijif.types.arb_source(
        "vcxo", a_min=90000000, a_max=110000000, b_min=1, b_max=1
    )

    sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.force_qpll = True

    sys.converter.sample_clock = 1e9
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.converter.HD = 0

    cfg = sys.solve()

    assert "vcxo" in cfg["clock"]
    assert isinstance(cfg["clock"]["vcxo"], (int, float))
    assert 90000000 <= cfg["clock"]["vcxo"] <= 110000000


def test_system_with_range_vcxo():
    """Test system class with range vcxo."""
    vcxo = adijif.types.range(90000000, 110000000, 5000000, "vcxo")

    sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.force_qpll = True

    sys.converter.sample_clock = 1e9
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.converter.HD = 0

    cfg = sys.solve()

    assert "vcxo" in cfg["clock"]
    assert isinstance(cfg["clock"]["vcxo"], (int, float))
    assert 90000000 <= cfg["clock"]["vcxo"] <= 110000000


def test_arb_source_with_gekko_error():
    """Test that arb_source with GEKKO raises helpful error."""
    vcxo = adijif.types.arb_source(
        "vcxo", a_min=100000000, a_max=150000000, b_min=1, b_max=1
    )

    msg = r"arb_source type requires CPLEX solver"

    with pytest.raises(Exception, match=msg):
        sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver="gekko")


def test_ltc6952_object_creation():
    """Test LTC6952 object creation."""
    clk = adijif.ltc6952(solver="CPLEX")
    assert clk is not None
    assert hasattr(clk, "set_requested_clocks")


def test_ltc6953_with_range_input():
    """Test LTC6953 with range input reference."""
    ref_in = adijif.types.range(1000000000, 4500000000, 100000000, "ref_in")

    clk = adijif.ltc6953(solver="CPLEX")

    output_clocks = [2e9, 1e9, 500e6]
    output_clocks = list(map(int, output_clocks))
    clock_names = ["ADC", "FPGA", "SYSREF"]

    clk.set_requested_clocks(ref_in, output_clocks, clock_names)

    clk.solve()

    o = clk.get_config()

    assert o is not None
    assert "out_dividers" in o
    assert "input_ref" in o


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_hmc7044_basic(solver):
    """Test HMC7044 basic configuration."""
    skip_solver(solver)

    vcxo = 122.88e6

    clk = adijif.hmc7044(solver=solver)

    output_clocks = [245.76e6, 245.76e6, 7.68e6]
    output_clocks = list(map(int, output_clocks))
    clock_names = ["ADC", "FPGA", "SYSREF"]

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    clk.solve()
    o = clk.get_config()

    assert o is not None
    assert "vcxo" in o
    assert o["vcxo"] == vcxo


def test_ad9523_1_vcxo_double_attribute():
    """Test AD9523-1 VCXO doubler attribute setting."""
    clk = adijif.ad9523_1(solver="CPLEX")

    # Test that attribute can be set
    clk.use_vcxo_double = True
    assert clk.use_vcxo_double is True


def test_ad9528_vcxo_double_attribute():
    """Test AD9528 VCXO doubler attribute setting."""
    clk = adijif.ad9528(solver="CPLEX")

    # Test that attribute can be set
    clk.use_vcxo_double = True
    assert clk.use_vcxo_double is True
