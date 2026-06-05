# flake8: noqa

import pytest

import adijif

from .common import skip_solver


def test_adrv9371_registered():
    """ADRV9371 classes are exported and listed as supported converter parts."""
    assert hasattr(adijif, "adrv9371")
    assert hasattr(adijif, "adrv9371_rx")
    assert hasattr(adijif, "adrv9371_tx")
    assert "adrv9371_rx" in adijif.converters.supported_parts
    assert "adrv9371_tx" in adijif.converters.supported_parts


@pytest.mark.parametrize("converter", ["adrv9371_rx", "adrv9371_tx"])
def test_adrv9371_lane_rate_math(converter):
    """Lane rate = sample_clock * M * Np * (10/8) / L."""
    conv = getattr(adijif, converter)()
    conv.sample_clock = 245.76e6
    # Mode 3 -> M=2, L=2, Np=16
    conv.set_quick_configuration_mode("3", "jesd204b")
    assert conv.M == 2
    assert conv.L == 2
    assert conv.Np == 16
    expected = 245.76e6 * conv.M * conv.Np * (10 / 8) / conv.L
    assert conv.bit_clock == expected
    assert conv.bit_clock == 4.9152e9


@pytest.mark.parametrize("solver", ["CPLEX"])
@pytest.mark.parametrize("converter", ["adrv9371_rx", "adrv9371_tx"])
def test_adrv9371_singleton_solve(solver, converter):
    skip_solver(solver)

    vcxo = 122.88e6
    sys = adijif.system(converter, "ad9528", "xilinx", vcxo, solver=solver)
    sys.converter.sample_clock = 245.76e6

    if converter == "adrv9371_rx":
        sys.converter.decimation = 4
    else:
        sys.converter.interpolation = 4

    sys.converter.set_quick_configuration_mode("3", "jesd204b")
    assert sys.converter.bit_clock == 4.9152e9
    assert sys.converter.device_clock == 4.9152e9 / 40

    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.clock.d = [*range(1, 257)]

    cfg = sys.solve()

    ref_name = f"{sys.fpga.name}_{converter.upper()}_ref_clk"
    assert cfg["clock"]["output_clocks"][ref_name]["rate"] == 122880000.0


@pytest.mark.parametrize("solver", ["CPLEX"])
def test_adrv9371_combined_solve(solver):
    skip_solver(solver)

    vcxo = 122.88e6
    sys = adijif.system("adrv9371", "ad9528", "xilinx", vcxo, solver=solver)

    # Rx
    sys.converter.adc.sample_clock = 245.76e6
    sys.converter.adc.decimation = 4
    sys.converter.adc.set_quick_configuration_mode("3", "jesd204b")
    assert sys.converter.adc.bit_clock == 4.9152e9

    # Tx
    sys.converter.dac.sample_clock = 245.76e6
    sys.converter.dac.interpolation = 4
    sys.converter.dac.set_quick_configuration_mode("3", "jesd204b")
    assert sys.converter.dac.bit_clock == 4.9152e9

    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.clock.d = [*range(1, 257)]

    cfg = sys.solve()

    output_clocks = cfg["clock"]["output_clocks"]
    assert output_clocks["zc706_adc_ref_clk"]["rate"] == 122880000.0
    assert output_clocks["zc706_dac_ref_clk"]["rate"] == 122880000.0


@pytest.mark.parametrize("solver", ["CPLEX"])
def test_adrv9371_quick_config(solver):
    skip_solver(solver)

    sys = adijif.system("adrv9371", "ad9528", "xilinx", 122.88e6, solver=solver)
    sys.converter.adc.sample_clock = 245.76e6
    sys.converter.dac.sample_clock = 245.76e6
    sys.converter.adc.decimation = 4
    sys.converter.dac.interpolation = 4

    sys.converter.adc.set_quick_configuration_mode("3", "jesd204b")
    sys.converter.dac.set_quick_configuration_mode("3", "jesd204b")

    assert sys.converter.adc.L == 2
    assert sys.converter.adc.M == 2
    assert sys.converter.adc.Np == 16

    sys.converter.adc._check_clock_relations()
    sys.converter.dac._check_clock_relations()
