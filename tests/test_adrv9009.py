# flake8: noqa

import pytest

import adijif


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
