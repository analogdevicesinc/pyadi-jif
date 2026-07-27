from __future__ import annotations

from pathlib import Path

import pytest

import adijif
from adijif.converters.ad9371_util import parse_ad9371_profile

from .common import skip_solver

PROFILES = Path(__file__).parent / "ad9371_profiles"
RX_JESD = {"M": 4, "L": 2, "S": 1, "Np": 16}
OBS_JESD = {"M": 2, "L": 2, "S": 1, "Np": 16}
TX_JESD = {"M": 4, "L": 4, "S": 1, "Np": 16}

EXPECTED = {
    "profile_TxBW100_ORxBW100_RxBW100.txt": (122_880_000, 10, 122_880_000, 4),
    "profile_TxBW100_ORxBW100_RxBW20.txt": (30_720_000, 40, 122_880_000, 4),
    "profile_TxBW100_ORxBW100_RxBW50.txt": (61_440_000, 20, 122_880_000, 4),
    "profile_TxBW200_ORxBW200_RxBW100.txt": (122_880_000, 10, 245_760_000, 2),
    "profile_TxBW50_ORxBW50_RxBW25.txt": (30_720_000, 40, 61_440_000, 8),
    "profile_TxBW50_ORxBW50_RxBW50.txt": (61_440_000, 20, 61_440_000, 8),
}


@pytest.mark.parametrize(("filename", "expected"), EXPECTED.items())
def test_parse_and_apply_canonical_ad9371_profiles(filename, expected):
    path = PROFILES / filename
    parsed = parse_ad9371_profile(path)
    assert parsed["profile"]["device"] == "AD9371"
    assert parsed["clocks"]["deviceClock_kHz"] == 122_880
    assert all(parsed[name] for name in ("rx", "obs", "tx"))

    model = adijif.ad9371()
    model.apply_profile_settings(
        str(path), rx_jesd=RX_JESD, tx_jesd=TX_JESD, obs_jesd=OBS_JESD
    )
    rx_rate, decimation, tx_rate, interpolation = expected
    assert model.adc.sample_clock == rx_rate
    assert model.adc.decimation == decimation
    assert model.dac.sample_clock == tx_rate
    assert model.dac.interpolation == interpolation
    assert model.obs.sample_clock == int(parsed["obs"]["iqRate_kHz"] * 1000)
    assert model.obs.decimation == int(
        parsed["obs"]["rxFirDecimation"]
        * parsed["obs"]["rxDec5Decimation"]
        * parsed["obs"]["rhb1Decimation"]
    )
    assert model.profile_device_clock == 122_880_000
    assert (model.adc.M, model.adc.L, model.adc.N, model.adc.Np, model.adc.CS) == (
        4,
        2,
        14,
        16,
        2,
    )
    assert (model.obs.M, model.obs.L, model.obs.N, model.obs.Np, model.obs.CS) == (
        2,
        2,
        14,
        16,
        2,
    )
    assert (model.dac.M, model.dac.L, model.dac.N, model.dac.Np, model.dac.CS) == (
        4,
        4,
        14,
        16,
        2,
    )
    model.adc.validate_config()
    model.obs.validate_config()
    model.dac.validate_config()


def test_ad9371_public_registration():
    assert adijif.AD9371 is adijif.ad9371
    assert adijif.AD9371_OBS is adijif.ad9371_obs
    assert adijif.AD9371_RX is adijif.ad9371_rx
    assert adijif.AD9371_TX is adijif.ad9371_tx
    assert adijif.registry.get_component_class("converter", "ad9371") is adijif.ad9371


def test_ad9371_profile_rejects_wrong_device(tmp_path):
    profile = tmp_path / "not-ad9371.txt"
    profile.write_text("<profile ADRV9009 version=0 name=test></profile>")
    with pytest.raises(ValueError, match="Not an AD9371 profile"):
        parse_ad9371_profile(profile)


def test_ad9371_profile_rejects_missing_section(tmp_path):
    profile = tmp_path / "incomplete.txt"
    profile.write_text(
        "<profile AD9371 version=0 name=test>"
        "<clocks><deviceClock_kHz=122880></clocks>"
        "<rx><iqRate_kHz=122880></rx>"
        "<tx><iqRate_kHz=122880></tx>"
        "</profile>"
    )
    with pytest.raises(ValueError, match="obs"):
        parse_ad9371_profile(profile)


def test_ad9371_profile_rejects_wrong_version(tmp_path):
    source = PROFILES / "profile_TxBW200_ORxBW200_RxBW100.txt"
    profile = tmp_path / "version.txt"
    profile.write_text(source.read_text().replace("version=0", "version=1", 1))
    with pytest.raises(ValueError, match="Unsupported AD9371 profile version"):
        parse_ad9371_profile(profile)


def test_ad9371_profile_rejects_missing_scalar_without_mutation(tmp_path):
    source = PROFILES / "profile_TxBW200_ORxBW200_RxBW100.txt"
    profile = tmp_path / "missing-scalar.txt"
    profile.write_text(source.read_text().replace("<txFirInterpolation=1>\n", "", 1))
    model = adijif.ad9371()
    before = (model.adc.sample_clock, model.obs.sample_clock, model.dac.sample_clock)
    with pytest.raises(ValueError, match="txFirInterpolation"):
        model.apply_profile_settings(str(profile))
    assert (model.adc.sample_clock, model.obs.sample_clock, model.dac.sample_clock) == before


def test_ad9371_defaults_are_mykonos_not_talise():
    model = adijif.ad9371()
    assert model._nested == ["adc", "obs", "dac"]
    assert model.adc.decimation == 10
    assert model.obs.decimation == 10
    assert model.dac.interpolation == 4
    for path in model._get_converters():
        assert (path.N, path.Np, path.CS, path.S, path.K) == (14, 16, 2, 1, 32)
        assert path.bit_clock_min == 614_400_000
        assert path.bit_clock_max == 6_144_000_000


def test_ad9371_profile_solve():
    skip_solver("CPLEX")
    system = adijif.system("ad9371", "ad9528", "xilinx", 122_880_000)
    system.converter.apply_profile_settings(
        str(PROFILES / "profile_TxBW200_ORxBW200_RxBW100.txt"),
        rx_jesd=RX_JESD,
        tx_jesd=TX_JESD,
    )
    system.fpga.setup_by_dev_kit_name("zc706")
    system.fpga.force_qpll = True
    config = system.solve()
    clocks = config["clock"]["output_clocks"]
    assert clocks["AD9371_ref_clk"]["rate"] == 122_880_000
    assert clocks["adc_sysref"]["rate"] == clocks["obs_sysref"]["rate"]
    assert clocks["obs_sysref"]["rate"] == clocks["dac_sysref"]["rate"]
    assert system.converter.adc.bit_clock == 4_915_200_000
    assert system.converter.obs.bit_clock == 4_915_200_000
    assert system.converter.dac.bit_clock == 4_915_200_000
