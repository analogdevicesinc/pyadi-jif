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

    # sys.model.options.SOLVER = 1  # APOPT solver
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

    sys.fpga.request_fpga_core_clock_ref = True

    sys.converter.sample_clock = 1e9

    sys.fpga.setup_by_dev_kit_name("zc706")
    cfg = sys.solve()

    assert cfg["clock"]["n2"] == 48
    assert cfg["clock"]["r2"] == 2
    assert cfg["clock"]["m1"] == 3
    assert cfg["clock"]["output_clocks"]["AD9680_fpga_ref_clk"]["rate"] == 1e9 / 4
    assert cfg["fpga_AD9680"]["type"] == "qpll"


def test_sys_solver():
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

    # cnv_clocks = sys.converter.get_required_clocks()

    # Get FPGA clocking requirements
    sys.fpga.setup_by_dev_kit_name("zc706")
    # fpga_dev_clock = sys.fpga.get_required_clocks(sys.converter)

    # # Collect all requirements
    # names = ["a", "b", "c"]
    # sys.clock.set_requested_clocks(vcxo, fpga_dev_clock + cnv_clocks, names)

    # sys.model.options.SOLVER = 1

    # sys.model.solve(disp=False)
    cfg = sys.solve()

    clk_config = sys.clock.config
    print(clk_config)
    print(sys.converter.bit_clock / 40)
    divs = sys.clock.config["out_dividers"]
    assert clk_config["n2"][0] == 48
    assert clk_config["r2"][0] == 2
    assert clk_config["m1"][0] == 3
    # print(sys.fpga.config)
    print(cfg["clock"])
    assert cfg["clock"]["output_clocks"]["AD9680_fpga_ref_clk"]["rate"] == 250000000
    for div in divs:
        assert div[0] in [1, 4, 32]


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

    cfg = sys.solve()
    print(cfg)

    clk_config = sys.clock.config
    print(clk_config)
    divs = sys.clock.config["out_dividers"]
    assert clk_config["r1"][0] == 2
    assert clk_config["n2"][0] == 12
    assert clk_config["m1"][0] == 5
    assert (
        cfg["clock"]["output_clocks"]["ADRV9009_fpga_ref_clk"]["rate"] == 245760000.0
    )  # 98304000
    for div in divs:
        assert div[0] in [3, 12, 192]


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

    cfg = sys.solve()
    print(cfg)

    assert cfg["fpga_AD9680"]["type"] == "qpll"


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
