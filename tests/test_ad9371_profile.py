# flake8: noqa

import os

import pytest

import adijif
from adijif.converters.ad9371_profile import (
    apply_settings,
    parse_profile,
)

PROFILE_DIR = os.path.join(os.path.dirname(__file__), "profiles", "ad9371")
PROFILE_RX100 = os.path.join(PROFILE_DIR, "profile_TxBW100_ORxBW100_RxBW100.txt")
PROFILE_RX20 = os.path.join(PROFILE_DIR, "profile_TxBW100_ORxBW100_RxBW20.txt")
PROFILE_TX50 = os.path.join(PROFILE_DIR, "profile_TxBW50_ORxBW50_RxBW25.txt")


def test_parse_profile_header():
    parsed = parse_profile(PROFILE_RX100)
    assert parsed["part"] == "AD9371"
    assert parsed["version"] == 0
    assert "Rx 100" in parsed["name"]


def test_parse_profile_sections_present():
    parsed = parse_profile(PROFILE_RX100)
    for section in ("clocks", "rx", "obs", "tx"):
        assert section in parsed, f"missing section {section}"


def test_parse_profile_clocks():
    parsed = parse_profile(PROFILE_RX100)
    clocks = parsed["clocks"]
    assert clocks["deviceClock_kHz"] == 122880
    assert clocks["clkPllVcoFreq_kHz"] == 9830400
    assert clocks["clkPllVcoDiv"] == 2
    assert clocks["clkPllHsDiv"] == 4


def test_parse_profile_skips_filter_blocks():
    """Filter coefficients and ADC profile arrays must not pollute the dict."""
    parsed = parse_profile(PROFILE_RX100)
    for section in ("rx", "obs", "tx"):
        for key in parsed[section]:
            assert "filter" not in key.lower()
            assert "profile" not in key.lower()


def test_parse_profile_coerces_float():
    """dacDiv is 2.5 in the TX section — must round-trip as a float."""
    parsed = parse_profile(PROFILE_RX100)
    assert isinstance(parsed["tx"]["dacDiv"], float)
    assert parsed["tx"]["dacDiv"] == 2.5


def test_parse_profile_text_input():
    """parse_profile accepts profile text directly, not just a path."""
    with open(PROFILE_RX100) as f:
        text = f.read()
    parsed = parse_profile(text)
    assert parsed["part"] == "AD9371"
    assert parsed["rx"]["iqRate_kHz"] == 122880


def test_parse_profile_rejects_wrong_part():
    fake = "<profile ADRV9009 version=0 name=X>\n<clocks>\n</clocks>\n</profile>"
    with pytest.raises(ValueError, match="not AD9371"):
        parse_profile(fake)


def test_parse_profile_rejects_missing_header():
    with pytest.raises(ValueError, match="missing"):
        parse_profile("not a profile")


def test_apply_to_ad9371_rx():
    rx = adijif.ad9371_rx()
    rx.apply_profile_settings(PROFILE_RX100)
    assert rx.sample_clock == 122_880_000
    # rxFirDecimation=2 * rxDec5Decimation=5 * rhb1Decimation=1
    assert rx.decimation == 10


def test_apply_to_ad9371_tx():
    tx = adijif.ad9371_tx()
    tx.apply_profile_settings(PROFILE_RX100)
    assert tx.sample_clock == 122_880_000
    # txFirInterpolation=1 * thb1=2 * thb2=2 * txInputHb=1
    assert tx.interpolation == 4


def test_apply_low_rate_rx_profile():
    """RxBW20 profile drives RX at 30.72 MHz with decimation 40."""
    rx = adijif.ad9371_rx()
    rx.apply_profile_settings(PROFILE_RX20)
    assert rx.sample_clock == 30_720_000
    assert rx.decimation == 40


def test_apply_to_combined_ad9371():
    xc = adijif.ad9371()
    xc.apply_profile_settings(PROFILE_TX50)
    assert xc.adc.sample_clock == 30_720_000
    assert xc.adc.decimation == 40
    assert xc.dac.sample_clock == 61_440_000
    # txFirInterpolation=2 * thb1=2 * thb2=2 * txInputHb=1
    assert xc.dac.interpolation == 8


def test_apply_settings_rejects_unknown_converter_type():
    """apply_settings must refuse anything that isn't an AD9371 converter."""

    class Dummy:
        converter_type = "mystery"

    parsed = parse_profile(PROFILE_RX100)
    with pytest.raises(ValueError, match="converter_type"):
        apply_settings(Dummy(), parsed)


def test_solve_after_profile_apply():
    """After applying a profile, JESD mode + solve should succeed end-to-end."""
    sys = adijif.system("ad9371_rx", "ad9528", "xilinx", 122.88e6, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_RX100)
    # M=4, L=2, S=1, Np=16 keeps lane rate at 4.9152 GHz, under AD9371's cap
    sys.converter.set_quick_configuration_mode("17", "jesd204b")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.out_clk_select = "XCVR_REFCLK"
    sys.fpga.force_qpll = True
    sys.clock.d = list(range(1, 257))
    cfg = sys.solve()
    assert cfg["clock"]["r1"] == 1
    assert cfg["clock"]["n2"] == 6
