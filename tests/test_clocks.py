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
