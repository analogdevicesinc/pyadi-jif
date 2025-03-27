# flake8: noqa

import pytest

import adijif

from .common import skip_solver


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
@pytest.mark.parametrize("converter", ["adrv9009_rx", "adrv9009_tx"])
def test_adrv9009_rxtx_ad9528_solver_compact(solver, converter):
    skip_solver(solver)
    if solver == "gekko":
        pytest.xfail("gekko currently unsupported")

    vcxo = 122.88e6

    sys = adijif.system(converter, "ad9528", "xilinx", vcxo, solver=solver)

    # Get Converter clocking requirements
    sys.converter.sample_clock = 122.88e6

    if converter == "adrv9009_rx":
        sys.converter.decimation = 4
    else:
        sys.converter.interpolation = 4

    sys.converter.L = 2
    sys.converter.M = 4
    sys.converter.N = 16
    sys.converter.Np = 16

    sys.converter.K = 32
    sys.converter.F = 4
    assert sys.converter.S == 1
    # sys.Debug_Solver = True

    assert 9830.4e6 / 2 == sys.converter.bit_clock
    assert sys.converter.multiframe_clock == 7.68e6 / 2  # LMFC
    assert sys.converter.device_clock == 9830.4e6 / 2 / 40

    # Set FPGA config
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.out_clk_select = "XCVR_REFCLK"
    sys.fpga.force_qpll = True

    # Set clock chip
    sys.clock.d = [*range(1, 257)]  # Limit output dividers

    cfg = sys.solve()
    # print(cfg)
    from pprint import pprint

    pprint(cfg)

    ref = {
        "gekko": {"clock": {"r1": 1, "n2": 8, "m1": 4, "out_dividers": [1, 4, 8, 256]}},
        "CPLEX": {"clock": {"r1": 1, "n2": 6, "m1": 5, "out_dividers": [6, 192]}},
    }

    assert cfg["clock"]["r1"] == ref[solver]["clock"]["r1"]
    assert cfg["clock"]["n2"] == ref[solver]["clock"]["n2"]
    assert cfg["clock"]["m1"] == ref[solver]["clock"]["m1"]
    assert (
        cfg["clock"]["output_clocks"][f"{sys.fpga.name}_{converter.upper()}_ref_clk"][
            "rate"
        ]
        == 122880000.0
    )  # 98304000
    for div in cfg["clock"]["out_dividers"]:
        assert div in ref[solver]["clock"]["out_dividers"]


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_adrv9009_ad9528_solver_compact(solver):
    skip_solver(solver)
    vcxo = 122.88e6
    sys = adijif.system("adrv9009", "ad9528", "xilinx", vcxo, solver=solver)

    # Rx
    sys.converter.adc.sample_clock = 122.88e6
    sys.converter.adc.decimation = 4
    sys.converter.adc.L = 2
    sys.converter.adc.M = 4
    sys.converter.adc.N = 16
    sys.converter.adc.Np = 16

    sys.converter.adc.K = 32
    sys.converter.adc.F = 4
    assert sys.converter.adc.S == 1

    assert 9830.4e6 / 2 == sys.converter.adc.bit_clock
    assert sys.converter.adc.multiframe_clock == 7.68e6 / 2  # LMFC
    assert sys.converter.adc.device_clock == 9830.4e6 / 2 / 40

    # Tx
    sys.converter.dac.sample_clock = 122.88e6
    sys.converter.dac.interpolation = 4
    sys.converter.dac.L = 2
    sys.converter.dac.M = 4
    sys.converter.dac.N = 16
    sys.converter.dac.Np = 16

    sys.converter.dac.K = 32
    sys.converter.dac.F = 4
    assert sys.converter.dac.S == 1

    assert 9830.4e6 / 2 == sys.converter.dac.bit_clock
    assert sys.converter.dac.multiframe_clock == 7.68e6 / 2  # LMFC
    assert sys.converter.dac.device_clock == 9830.4e6 / 2 / 40

    # Set FPGA config
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.out_clk_select = "XCVR_REFCLK"
    sys.fpga.force_qpll = True

    # Set clock chip
    sys.clock.d = [*range(1, 257)]  # Limit output dividers

    if solver == "gekko":
        with pytest.raises(AssertionError):
            cfg = sys.solve()
        pytest.xfail("gekko currently unsupported")

    cfg = sys.solve()
    print(cfg)

    ref = {
        "gekko": {"clock": {"r1": 1, "n2": 8, "m1": 4, "out_dividers": [1, 8, 256]}},
        "CPLEX": {
            "clock": {
                "r1": 1,
                "n2": 6,
                "m1": 5,
                "out_dividers": [1, 6, 192],
            }
        },
    }

    assert cfg["clock"]["r1"] == ref[solver]["clock"]["r1"]
    assert cfg["clock"]["n2"] == ref[solver]["clock"]["n2"]
    assert cfg["clock"]["m1"] == ref[solver]["clock"]["m1"]

    output_clocks = cfg["clock"]["output_clocks"]
    assert output_clocks["zc706_adc_ref_clk"]["rate"] == 122880000.0
    assert output_clocks["zc706_dac_ref_clk"]["rate"] == 122880000.0

    for div in cfg["clock"]["out_dividers"]:
        assert div in ref[solver]["clock"]["out_dividers"]


@pytest.mark.parametrize("solver", ["gekko", "CPLEX"])
def test_adrv9009_ad9528_quick_config(solver):
    skip_solver(solver)
    vcxo = 122.88e6

    sys = adijif.system("adrv9009", "ad9528", "xilinx", vcxo, solver=solver)
    sys.converter.adc.sample_clock = 122.88e6
    sys.converter.dac.sample_clock = 122.88e6

    sys.converter.adc.decimation = 4
    sys.converter.dac.interpolation = 4

    mode_rx = "17"
    mode_tx = "6"
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204b")
    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204b")

    assert sys.converter.adc.L == 2
    assert sys.converter.adc.M == 4
    assert sys.converter.adc.N == 16
    assert sys.converter.adc.Np == 16

    assert sys.converter.dac.L == 2
    assert sys.converter.dac.M == 4
    assert sys.converter.dac.N == 16
    assert sys.converter.dac.Np == 16

    sys.converter.adc._check_clock_relations()
    sys.converter.dac._check_clock_relations()

    sys.fpga.setup_by_dev_kit_name("zc706")

    if solver == "gekko":
        with pytest.raises(AssertionError):
            cfg = sys.solve()
        pytest.xfail("gekko currently unsupported")

    cfg = sys.solve()
