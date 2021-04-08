# flake8: noqa
import pprint

import pytest
from gekko import GEKKO  # type: ignore

import adijif


def test_ad9523_1_daq2_validate():

    vcxo = 125000000
    n2 = 24

    clk = adijif.ad9523_1()

    # Check config valid
    clk.n2 = n2
    clk.use_vcxo_double = False

    output_clocks = [1e9, 500e6, 7.8125e6]
    clock_names = ["ADC", "FPGA", "SYSREF"]

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    clk.solve()

    o = clk.get_config()

    # print(o)

    assert sorted(o["out_dividers"]) == [1, 2, 128]
    assert o["m1"] == 3
    assert o["m1"] in clk.m1_available
    assert o["n2"] == n2
    assert o["n2"] in clk.n2_available
    assert o["r2"] == 1
    assert o["r2"] in clk.r2_available


def test_ad9523_1_daq2_cplex_validate():

    vcxo = 125000000
    n2 = 24

    clk = adijif.ad9523_1(solver="CPLEX")
    # clk = adijif.ad9523_1()

    # Check config valid
    clk.n2 = n2
    clk.use_vcxo_double = False

    output_clocks = [1e9, 500e6, 7.8125e6]
    clock_names = ["ADC", "FPGA", "SYSREF"]

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    clk.solve()

    o = clk.get_config()

    pprint.pprint(o)

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


def test_ad9523_1_daq2_validate_fail():

    with pytest.raises(Exception, match=r"Solution Not Found"):
        vcxo = 125000000
        n2 = 12

        clk = adijif.ad9523_1()

        # Check config valid
        clk.n2 = n2
        # clk.r2 = 1
        clk.use_vcxo_double = False
        # clk.m = 3

        output_clocks = [1e9, 500e6, 7.8125e6]
        clock_names = ["ADC", "FPGA", "SYSREF"]

        clk.set_requested_clocks(vcxo, output_clocks, clock_names)

        clk.model.options.SOLVER = 1  # APOPT solver
        clk.model.solve(disp=False)

        o = clk.get_config()

        print(o)

        assert sorted(o["out_dividers"]) == [1, 2, 128]
        assert o["n2"] == n2


def test_ad9523_1_daq2_validate_fail_cplex():

    with pytest.raises(Exception, match=r"Solution Not Found"):
        vcxo = 125000000
        n2 = 12

        clk = adijif.ad9523_1(solver="CPLEX")

        # Check config valid
        clk.n2 = n2
        # clk.r2 = 1
        clk.use_vcxo_double = False
        # clk.m = 3

        output_clocks = [1e9, 500e6, 7.8125e6]
        clock_names = ["ADC", "FPGA", "SYSREF"]

        clk.set_requested_clocks(vcxo, output_clocks, clock_names)

        clk.solve()

        # o = clk.get_config()

        # print(o)

        # assert sorted(o["out_dividers"]) == [1, 2, 128]
        # assert o["n2"] == n2


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_ad9523_1_daq2_variable_vcxo_validate(solver):

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
