"""Tests for AD9084_TX transmit model."""

import pytest

import adijif
from adijif.converters.ad9084 import ad9084_tx
from adijif.converters.ad9084_util import _load_tx_config_modes

# ── Instantiation ────────────────────────────────────────────────────────────


def test_ad9084_tx_instantiation():
    """Verify AD9084_TX instantiates with expected defaults."""
    tx = ad9084_tx(solver="CPLEX")
    assert tx.name == "AD9084_TX"
    assert tx.converter_type == "dac"
    assert tx.jesd_class == "jesd204c"


def test_ad9084_tx_via_system():
    """Verify AD9084_TX can be created through the system factory."""
    sys = adijif.system(
        "ad9084_tx", "hmc7044", "xilinx", 125000000, solver="CPLEX"
    )
    assert sys.converter.name == "AD9084_TX"


def test_ad9084_tx_clock_limits():
    """Verify converter clock limits are set correctly."""
    tx = ad9084_tx(solver="CPLEX")
    assert tx.converter_clock_min == 8e9
    assert tx.converter_clock_max == 28e9


# ── Quick configuration modes ────────────────────────────────────────────────


def test_ad9084_tx_quick_config_modes_loaded():
    """Verify TX quick configuration modes are loaded for both JESD classes."""
    modes = ad9084_tx.quick_configuration_modes
    assert "jesd204b" in modes
    assert "jesd204c" in modes
    assert len(modes["jesd204c"]) > 0
    assert len(modes["jesd204b"]) > 0


def test_ad9084_tx_quick_config_mode_fields():
    """Verify each TX mode contains the required JESD parameter fields."""
    required = {"L", "M", "F", "S", "HD", "Np", "jesd_class"}
    modes = ad9084_tx.quick_configuration_modes["jesd204c"]
    for mode_key, cfg in modes.items():
        assert required.issubset(cfg.keys()), (
            f"Mode {mode_key} missing fields: {required - cfg.keys()}"
        )


def test_ad9084_tx_mode_47_stock_config():
    """Verify mode 47 matches the stock profile (L=8, M=4, F=1, Np=16)."""
    tx = ad9084_tx(solver="CPLEX")
    tx.set_quick_configuration_mode("47", "jesd204c")
    assert tx.L == 8
    assert tx.M == 4
    assert tx.F == 1
    assert tx.Np == 16
    assert tx.jesd_class == "jesd204c"


def test_ad9084_tx_set_quick_config_mode_jesd204b():
    """Verify a JESD204B mode can be set without error."""
    tx = ad9084_tx(solver="CPLEX")
    first_b_mode = next(iter(tx.quick_configuration_modes["jesd204b"]))
    tx.set_quick_configuration_mode(first_b_mode, "jesd204b")
    assert tx.jesd_class == "jesd204b"


def test_ad9084_tx_set_invalid_mode_raises():
    """Verify setting a non-existent mode raises an exception."""
    tx = ad9084_tx(solver="CPLEX")
    with pytest.raises(Exception, match="Mode"):
        tx.set_quick_configuration_mode("999", "jesd204c")


def test_ad9084_tx_set_invalid_jesd_class_raises():
    """Verify setting an unsupported JESD class raises an exception."""
    tx = ad9084_tx(solver="CPLEX")
    with pytest.raises(Exception, match="jesd204d"):
        tx.set_quick_configuration_mode("47", "jesd204d")


# ── Mode loader ──────────────────────────────────────────────────────────────


def test_load_tx_config_modes_ad9084():
    """Verify _load_tx_config_modes returns valid data for AD9084."""
    modes = _load_tx_config_modes(part="AD9084")
    assert "jesd204c" in modes
    assert len(modes["jesd204c"]) > 0


def test_load_tx_config_modes_ad9088():
    """Verify _load_tx_config_modes returns valid data for AD9088."""
    modes = _load_tx_config_modes(part="AD9088")
    assert "jesd204c" in modes
    assert len(modes["jesd204c"]) > 0


def test_load_tx_config_modes_unsupported_part():
    """Verify _load_tx_config_modes raises for an unsupported part name."""
    with pytest.raises(AssertionError):
        _load_tx_config_modes(part="AD9999")


def test_load_tx_config_modes_204b_mirrors_204c():
    """Verify jesd204b modes are a copy of 204c modes with class field updated."""
    modes = _load_tx_config_modes(part="AD9084")
    b_modes = modes["jesd204b"]
    c_modes = modes["jesd204c"]
    assert b_modes.keys() == c_modes.keys()
    for key in c_modes:
        assert b_modes[key]["L"] == c_modes[key]["L"]
        assert b_modes[key]["M"] == c_modes[key]["M"]
        assert b_modes[key]["jesd_class"] == "jesd204b"
        assert c_modes[key]["jesd_class"] == "jesd204c"


# ── Datapath ─────────────────────────────────────────────────────────────────


def test_ad9084_tx_datapath_defaults():
    """Verify TX datapath has expected default structure."""
    tx = ad9084_tx(solver="CPLEX")
    dp = tx.datapath
    assert len(dp.cduc_enabled) == 4
    assert len(dp.fduc_enabled) == 8
    assert dp.cduc_interpolation == 1
    assert dp.fduc_interpolation == 1


def test_ad9084_tx_datapath_get_config():
    """Verify TX datapath get_config returns the expected keys."""
    tx = ad9084_tx(solver="CPLEX")
    cfg = tx.datapath.get_config()
    assert "cduc" in cfg
    assert "fduc" in cfg
    assert "interpolation" in cfg["cduc"]
    assert "interpolation" in cfg["fduc"]


def test_ad9084_tx_datapath_set_cduc_interpolation():
    """Verify CDUC interpolation can be set."""
    tx = ad9084_tx(solver="CPLEX")
    tx.datapath.cduc_interpolation = 4
    assert tx.datapath.cduc_interpolation == 4


def test_ad9084_tx_datapath_overall_interpolation_cduc_only():
    """Verify interpolation_overall returns CDUC value when no FDUC enabled."""
    tx = ad9084_tx(solver="CPLEX")
    tx.datapath.cduc_interpolation = 6
    tx.datapath.fduc_enabled = [False] * 8
    assert tx.datapath.interpolation_overall == 6


# ── Sample clock ─────────────────────────────────────────────────────────────


def test_ad9084_tx_sample_clock_setter():
    """Verify sample clock can be assigned."""
    sys = adijif.system(
        "ad9084_tx", "hmc7044", "xilinx", 125000000, solver="CPLEX"
    )
    sys.converter.sample_clock = 1e9
    assert sys.converter.sample_clock == 1e9


# ── Clock names ──────────────────────────────────────────────────────────────


def test_ad9084_tx_required_clock_names():
    """Verify required clock names include ref_clk and sysref."""
    tx = ad9084_tx(solver="CPLEX")
    names = tx.get_required_clock_names()
    assert len(names) == 2
    assert any("ref_clk" in n for n in names)
    assert any("sysref" in n for n in names)
    assert all("AD9084" in n for n in names)


# ── supported_parts registry ─────────────────────────────────────────────────


def test_ad9084_tx_in_supported_parts():
    """Verify ad9084_tx is listed in the supported_parts registry."""
    from adijif import converters

    assert "ad9084_tx" in converters.supported_parts
