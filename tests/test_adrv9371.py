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


@pytest.mark.parametrize(
    "part, M, L, S, expected_F",
    [
        ("adrv9371_rx", 4, 2, 1, 4),  # zc706 main-Rx framing (M=4 L=2 -> F=4)
        ("adrv9371_tx", 4, 4, 1, 2),  # zc706 Tx framing       (M=4 L=4 -> F=2)
    ],
)
def test_adrv9371_zc706_m4_modes(part, M, L, S, expected_F):
    """Native AD9371 exposes the M=4 (two complex I/Q channels) zc706 modes.

    These are the modes the Kuiper ``zynq-zc706-adv7511-adrv937x`` reference
    actually boots (validated on the ``bq`` board) and that pyadi-dt selects
    when generating the ADRV9371 device tree.
    """
    conv = getattr(adijif, part)()
    modes = adijif.utils.get_jesd_mode_from_params(conv, M=M, L=L, S=S, Np=16)
    assert len(modes) == 1, modes
    settings = modes[0]["settings"]
    assert settings["F"] == expected_F
    assert settings["M"] == M and settings["L"] == L and settings["Np"] == 16


def test_adrv9371_zc706_reference_framing():
    """ADRV9371 reproduces the zc706 reference framing (Rx M4/L2, Tx M4/L4).

    These are the exact M/L/F the Kuiper ``zynq-zc706-adv7511-adrv937x`` device
    tree carries (validated on the ``bq`` board), and what pyadi-dt selects via
    ``get_jesd_mode_from_params`` when generating the ADRV9371 device tree. This
    checks framing + lane-rate math only; closing a full FPGA system solve at the
    measured rates is covered by the hardware test (it needs the live sample
    rates, which differ between the Rx and Tx paths).
    """
    rx = adijif.adrv9371_rx()
    rx.sample_clock = 122.88e6
    rx.set_quick_configuration_mode(
        adijif.utils.get_jesd_mode_from_params(rx, M=4, L=2, S=1, Np=16)[0][
            "mode"
        ],
        "jesd204b",
    )
    assert (rx.M, rx.L, rx.F, rx.Np) == (4, 2, 4, 16)
    # Lane rate = sample * M * Np * (10/8) / L
    assert rx.bit_clock == 4.9152e9
    assert rx.bit_clock <= 6.144e9  # AD9371 JESD204B max lane rate

    tx = adijif.adrv9371_tx()
    tx.sample_clock = 245.76e6
    tx.set_quick_configuration_mode(
        adijif.utils.get_jesd_mode_from_params(tx, M=4, L=4, S=1, Np=16)[0][
            "mode"
        ],
        "jesd204b",
    )
    assert (tx.M, tx.L, tx.F, tx.Np) == (4, 4, 2, 16)
    assert tx.bit_clock == 4.9152e9
    assert tx.bit_clock <= 6.144e9
