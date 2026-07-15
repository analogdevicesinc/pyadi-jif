import os

import pytest

import adijif
from adijif.converters.adrv9009_util import parse_adrv9009_profile

from .common import skip_solver

PROFILES_DIR = os.path.join(os.path.dirname(__file__), "adrv9009_profiles")


def test_adrv9009_profile_parser():
    # Test that the utility function parses all 4 profiles correctly
    for filename in os.listdir(PROFILES_DIR):
        if not filename.endswith(".txt"):
            continue
        path = os.path.join(PROFILES_DIR, filename)
        data = parse_adrv9009_profile(path)
        assert "clocks" in data
        assert "rx" in data
        assert "tx" in data

        # Check that clocks and rx/tx dictionaries have correct keys parsed
        assert "deviceClock_kHz" in data["clocks"]

        rx_data = data["rx"]
        assert "rxOutputRate_kHz" in rx_data
        assert "rxFirDecimation" in rx_data
        assert "rxDec5Decimation" in rx_data
        assert "rhb1Decimation" in rx_data

        tx_data = data["tx"]
        assert "txInputRate_kHz" in tx_data
        assert "txFirInterpolation" in tx_data
        assert "thb1Interpolation" in tx_data
        assert "thb2Interpolation" in tx_data
        assert "thb3Interpolation" in tx_data
        assert "txInt5Interpolation" in tx_data


def test_adrv9009_rx_apply_profile_settings():
    rx = adijif.adrv9009_rx()
    profile_path = os.path.join(
        PROFILES_DIR,
        "Tx_BW100_IR122p88_Rx_BW100_OR122p88_ORx_BW100_OR122p88_DC245p76.txt",
    )

    # Apply settings and check
    rx.apply_profile_settings(
        profile_path, jesd={"M": 4, "L": 2, "S": 1, "Np": 16}
    )
    assert rx.decimation == 16
    assert rx.sample_clock == 122880000
    assert rx.M == 4
    assert rx.L == 2
    assert rx.S == 1
    assert rx.Np == 16


def test_adrv9009_tx_apply_profile_settings():
    tx = adijif.adrv9009_tx()
    profile_path = os.path.join(
        PROFILES_DIR,
        "Tx_BW100_IR122p88_Rx_BW100_OR122p88_ORx_BW100_OR122p88_DC245p76.txt",
    )

    # Apply settings and check
    tx.apply_profile_settings(
        profile_path, jesd={"M": 4, "L": 4, "S": 1, "Np": 16}
    )
    assert tx.interpolation == 16
    assert tx.sample_clock == 122880000
    assert tx.M == 4
    assert tx.L == 4
    assert tx.S == 1
    assert tx.Np == 16


def test_adrv9009_combined_apply_profile_settings():
    conv = adijif.adrv9009()
    profile_path = os.path.join(
        PROFILES_DIR,
        "Tx_BW200_IR245p76_Rx_BW100_OR122p88_ORx_BW200_OR245p76_DC245p76.txt",
    )

    conv.apply_profile_settings(
        profile_path,
        rx_jesd={"M": 4, "L": 2, "S": 1, "Np": 16},
        tx_jesd={"M": 4, "L": 4, "S": 1, "Np": 16},
    )

    # Rx path check: Total decimation should be 2 * 4 * 2 = 16. OutputRate: 122.88 MHz.
    assert conv.adc.decimation == 16
    assert conv.adc.sample_clock == 122880000
    assert conv.adc.M == 4
    assert conv.adc.L == 2
    assert conv.adc.Np == 16

    # Tx path check: Total interpolation should be 1 * 2 * 2 * 2 * 1 = 8. InputRate: 245.76 MHz.
    assert conv.dac.interpolation == 8
    assert conv.dac.sample_clock == 245760000
    assert conv.dac.M == 4
    assert conv.dac.L == 4
    assert conv.dac.Np == 16


def test_adrv9009_profile_errors(tmp_path):
    rx = adijif.adrv9009_rx()

    # Missing path raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        rx.apply_profile_settings("non_existent_file.txt")

    # File without rx tag raises ValueError
    bad_profile = tmp_path / "bad_profile.txt"
    bad_profile.write_text("<profile><tx><txInputRate_kHz=100></tx></profile>")
    with pytest.raises(ValueError, match="No RX section found in profile"):
        rx.apply_profile_settings(str(bad_profile))

    tx = adijif.adrv9009_tx()
    bad_profile_tx = tmp_path / "bad_profile_tx.txt"
    bad_profile_tx.write_text(
        "<profile><rx><rxOutputRate_kHz=100></rx></profile>"
    )
    with pytest.raises(ValueError, match="No TX section found in profile"):
        tx.apply_profile_settings(str(bad_profile_tx))


@pytest.mark.parametrize("solver", ["CPLEX"])
def test_adrv9009_profile_solve(solver):
    skip_solver(solver)

    vcxo = 122.88e6
    sys = adijif.system(
        "adrv9009", "ad9528", "xilinx", vcxo=vcxo, solver=solver
    )

    profile_path = os.path.join(
        PROFILES_DIR,
        "Tx_BW200_IR245p76_Rx_BW200_OR245p76_ORx_BW200_OR245p76_DC245p76.txt",
    )
    sys.converter.apply_profile_settings(
        profile_path,
        rx_jesd={"M": 4, "L": 2, "S": 1, "Np": 16},
        tx_jesd={"M": 4, "L": 4, "S": 1, "Np": 16},
    )

    sys.fpga.setup_by_dev_kit_name("zcu102")
    sys.fpga.force_qpll = True

    config = sys.solve()
    assert config is not None
