#!/usr/bin/env python
# flake8: noqa
"""Tests for `adijif` package."""

import pytest

import adijif

# from adijif import adijif
# from adijif import cli

# from click.testing import CliRunner


@pytest.fixture
def response():
    """Sample pytest fixture.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get('https://github.com/audreyr/cookiecutter-pypackage')


def test_content(response):
    """Sample pytest test function with the pytest fixture as an argument."""
    # from bs4 import BeautifulSoup
    # assert 'GitHub' in BeautifulSoup(response.content).title.string


# def test_command_line_interface():
#     """Test the CLI."""
#     runner = CliRunner()
#     result = runner.invoke(cli.main)
#     assert result.exit_code == 0
#     assert "adijif.cli.main" in result.output
#     help_result = runner.invoke(cli.main, ["--help"])
#     assert help_result.exit_code == 0
#     assert "--help  Show this message and exit." in help_result.output


# def test_mxfe_config():
#     # RX
#     j = adijif.jesd()
#     j.sample_clock = 250e6
#     j.L = 4
#     j.M = 8
#     j.S = 1
#     j.N = 16
#     j.Np = 16
#     j.K = 32

#     assert j.bit_clock == 10000000000
#     assert j.multiframe_clock == 7812500


def test_adc_clk_solver():

    vcxo = 125000000
    sys = adijif.system("ad9680", "ad9523_1", "xilinx", vcxo)

    # Get Converter clocking requirements
    sys.converter.sample_clock = 1e9
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.F = 1
    sys.converter.HD = 1

    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32

    assert sys.converter.S == 1

    cnv_clocks = sys.converter.get_required_clocks()
    names = ["a", "b"]

    sys.clock.set_requested_clocks(vcxo, cnv_clocks, names)

    sys.model.options.SOLVER = 1  # APOPT solver
    sys.model.solve(disp=False)

    for c in sys.clock.config:
        vs = sys.clock.config[c]
        for v in vs:
            if len(vs) > 1:
                print(c, v[0])
            else:
                print(c, v)
    assert sys.clock.config["r2"].value[0] == 1
    assert sys.clock.config["m1"].value[0] == 3
    assert sys.clock.config["n2"].value[0] == 24
    assert sys.clock.config["out_dividers"][0][0] == 1  # Converter
    assert sys.clock.config["out_dividers"][1][0] == 32  # SYSREF


def test_fpga_solver():

    vcxo = 125000000
    sys = adijif.system("ad9680", "ad9523_1", "xilinx", vcxo)

    cnv_config = type("AD9680", (), {})()
    cnv_config.bit_clock = 10e9
    cnv_config.device_clock = 10e9 / 40

    sys.fpga.setup_by_dev_kit_name("zc706")
    required_clocks = sys.fpga.get_required_clocks(cnv_config)

    names = ["a"]
    sys.clock.set_requested_clocks(vcxo, required_clocks, names)

    sys.model.options.SOLVER = 1  # APOPT solver
    sys.model.solve(disp=True)

    clk_config = sys.clock.config
    print(clk_config)
    # divs = sys.clock.config["out_dividers"]
    assert clk_config["n2"][0] == 24
    assert clk_config["r2"][0] == 1
    assert clk_config["m1"][0] == 5
    assert sys.fpga.config["fpga_ref"].value[0] == 100e6
    assert sys.fpga.configs[0]["qpll_0_cpll_1"].value[0] == 0


def test_sys_solver():
    vcxo = 125000000

    sys = adijif.system("ad9680", "ad9523_1", "xilinx", vcxo)

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

    cnv_clocks = sys.converter.get_required_clocks()

    # Get FPGA clocking requirements
    sys.fpga.setup_by_dev_kit_name("zc706")
    fpga_dev_clock = sys.fpga.get_required_clocks(sys.converter)

    # Collect all requirements
    names = ["a", "b", "c"]
    sys.clock.set_requested_clocks(vcxo, fpga_dev_clock + cnv_clocks, names)

    sys.model.options.SOLVER = 1

    sys.model.solve(disp=False)

    clk_config = sys.clock.config
    print(clk_config)
    divs = sys.clock.config["out_dividers"]
    assert clk_config["n2"][0] == 24
    assert clk_config["r2"][0] == 1
    assert clk_config["m1"][0] == 3
    assert sys.fpga.config["fpga_ref"].value[0] == 100000000
    for div in divs:
        assert div[0] in [1, 4, 10, 32, 288]


def test_adrv9009_ad9528_solver_compact():
    vcxo = 122.88e6

    sys = adijif.system("adrv9009", "ad9528", "xilinx", vcxo)

    # Get Converter clocking requirements
    sys.converter.sample_clock = 122.88e6
    sys.converter.L = 2
    sys.converter.M = 4
    sys.converter.N = 14
    sys.converter.Np = 16

    sys.converter.K = 32
    sys.converter.F = 4
    assert sys.converter.S == 1
    sys.Debug_Solver = True

    assert 9830.4e6 / 2 == sys.converter.bit_clock
    assert sys.converter.multiframe_clock == 7.68e6 / 2  # LMFC
    assert sys.converter.device_clock == 9830.4e6 / 2 / 40

    # Set FPGA config
    sys.fpga.setup_by_dev_kit_name("zc706")

    # Set clock chip
    sys.clock.d = [*range(1, 257)]  # Limit output dividers

    sys.solve()

    clk_config = sys.clock.config
    print(clk_config)
    divs = sys.clock.config["out_dividers"]
    assert clk_config["r1"][0] == 2
    assert clk_config["n2"][0] == 12
    assert clk_config["m1"][0] == 5
    assert sys.fpga.config["fpga_ref"].value[0] == 67025454.0  # 98304000
    for div in divs:
        assert div[0] in [6, 11, 192]


def test_xilinx_solver():

    cnv_config = type("ADRV9009", (), {})()
    cnv_config.bit_clock = 122.88e6 * 40
    cnv_config.device_clock = cnv_config.bit_clock / 40

    fpga = adijif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")
    fpga.get_required_clocks(cnv_config)

    m = 1
    d = 1
    n1 = 5
    n2 = 2
    fpga_ref = 122.88e6 * 2
    vco = fpga_ref * n1 * n2 / m
    assert vco >= fpga.vco_min
    assert vco <= fpga.vco_max
    assert 2 * vco / d == cnv_config.bit_clock

    fpga.model.options.SOLVER = 1

    fpga.model.solve(disp=False)


def test_daq2_qpll_or_cpll():
    vcxo = 125000000

    sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo)

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
    sys.Debug_Solver = True

    # Get FPGA clocking requirements
    sys.fpga.setup_by_dev_kit_name("zc706")
    # sys.fpga.force_qpll = 1

    sys.solve()

    assert sys.fpga.configs[0]["qpll_0_cpll_1"].value[0] == 0


def test_daq2_cpll():
    vcxo = 125000000

    sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo)

    # Get Converter clocking requirements
    sys.converter.sample_clock = 1e9 / 2
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.converter.HD = 1

    sys.Debug_Solver = False

    # Get FPGA clocking requirements
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.force_cpll = 1  # Uncomment to pass?
    print(sys.converter.bit_clock / 1e9)

    sys.solve()

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
