"""Tests for AD9088_TX transmit model."""

import pytest

import adijif
from adijif.converters.ad9084 import ad9084_tx, ad9088_tx
from adijif.converters.ad9084_util import _load_tx_config_modes

# ── Instantiation ────────────────────────────────────────────────────────────


def test_ad9088_tx_instantiation():
    """Verify AD9088_TX instantiates with expected defaults."""
    tx = ad9088_tx(solver="CPLEX")
    assert tx.name == "AD9088_TX"
    assert tx.converter_type == "dac"
    assert tx.jesd_class == "jesd204c"


def test_ad9088_tx_inherits_ad9084_tx():
    """Verify AD9088_TX is a subclass of AD9084_TX."""
    tx = ad9088_tx(solver="CPLEX")
    assert isinstance(tx, ad9084_tx)


def test_ad9088_tx_via_system():
    """Verify AD9088_TX can be created through the system factory."""
    sys = adijif.system(
        "ad9088_tx", "hmc7044", "xilinx", 125000000, solver="CPLEX"
    )
    assert sys.converter.name == "AD9088_TX"


def test_ad9088_tx_clock_limits():
    """Verify converter clock limits reflect AD9088 (lower than AD9084)."""
    tx = ad9088_tx(solver="CPLEX")
    assert tx.converter_clock_min == 5e9
    assert tx.converter_clock_max == 16e9


def test_ad9088_tx_clock_limits_differ_from_ad9084_tx():
    """Verify AD9088_TX has tighter clock limits than AD9084_TX."""
    tx84 = ad9084_tx(solver="CPLEX")
    tx88 = ad9088_tx(solver="CPLEX")
    assert tx88.converter_clock_min < tx84.converter_clock_min
    assert tx88.converter_clock_max < tx84.converter_clock_max


# ── Quick configuration modes ────────────────────────────────────────────────


def test_ad9088_tx_quick_config_modes_loaded():
    """Verify TX quick configuration modes are loaded for both JESD classes."""
    modes = ad9088_tx.quick_configuration_modes
    assert "jesd204b" in modes
    assert "jesd204c" in modes
    assert len(modes["jesd204c"]) > 0
    assert len(modes["jesd204b"]) > 0


def test_ad9088_tx_has_more_modes_than_ad9084_tx():
    """Verify AD9088_TX has more modes than AD9084_TX (8T8R configuration)."""
    modes_88 = ad9088_tx.quick_configuration_modes["jesd204c"]
    modes_84 = ad9084_tx.quick_configuration_modes["jesd204c"]
    assert len(modes_88) > len(modes_84)


def test_ad9088_tx_mode_0_exists():
    """Verify mode 0 exists in AD9088_TX (unlike AD9084_TX which starts at 2)."""
    modes = ad9088_tx.quick_configuration_modes["jesd204c"]
    assert "0" in modes


def test_ad9088_tx_mode_0_fields():
    """Verify mode 0 has expected JESD parameter values."""
    mode = ad9088_tx.quick_configuration_modes["jesd204c"]["0"]
    assert mode["L"] == 1
    assert mode["M"] == 16
    assert mode["F"] == 32
    assert mode["Np"] == 16
    assert mode["S"] == 1


def test_ad9088_tx_quick_config_mode_fields():
    """Verify every mode contains the required JESD parameter fields."""
    required = {"L", "M", "F", "S", "HD", "Np", "jesd_class"}
    modes = ad9088_tx.quick_configuration_modes["jesd204c"]
    for mode_key, cfg in modes.items():
        assert required.issubset(cfg.keys()), (
            f"Mode {mode_key} missing fields: {required - cfg.keys()}"
        )


def test_ad9088_tx_set_mode_45():
    """Verify mode 45 (L=8, M=8) can be set without error."""
    tx = ad9088_tx(solver="CPLEX")
    tx.set_quick_configuration_mode("45", "jesd204c")
    assert tx.L == 8
    assert tx.M == 8
    assert tx.F == 2
    assert tx.Np == 16
    assert tx.jesd_class == "jesd204c"


def test_ad9088_tx_set_mode_jesd204b():
    """Verify a JESD204B mode can be set without error."""
    tx = ad9088_tx(solver="CPLEX")
    first_b_mode = next(iter(tx.quick_configuration_modes["jesd204b"]))
    tx.set_quick_configuration_mode(first_b_mode, "jesd204b")
    assert tx.jesd_class == "jesd204b"


def test_ad9088_tx_set_invalid_mode_raises():
    """Verify setting a non-existent mode raises an exception."""
    tx = ad9088_tx(solver="CPLEX")
    with pytest.raises(Exception, match="Mode"):
        tx.set_quick_configuration_mode("9999", "jesd204c")


def test_ad9088_tx_set_invalid_jesd_class_raises():
    """Verify setting an unsupported JESD class raises an exception."""
    tx = ad9088_tx(solver="CPLEX")
    with pytest.raises(Exception, match="jesd204d"):
        tx.set_quick_configuration_mode("45", "jesd204d")


# ── Mode loader (8T8R) ───────────────────────────────────────────────────────


def test_load_tx_config_modes_ad9088_204b_mirrors_204c():
    """Verify jesd204b modes mirror jesd204c modes with class field updated."""
    modes = _load_tx_config_modes(part="AD9088")
    b_modes = modes["jesd204b"]
    c_modes = modes["jesd204c"]
    assert b_modes.keys() == c_modes.keys()
    for key in c_modes:
        assert b_modes[key]["L"] == c_modes[key]["L"]
        assert b_modes[key]["M"] == c_modes[key]["M"]
        assert b_modes[key]["jesd_class"] == "jesd204b"
        assert c_modes[key]["jesd_class"] == "jesd204c"


def test_ad9088_tx_modes_differ_from_ad9084_tx_modes():
    """Verify AD9088_TX uses the 8T8R column, giving a different mode set."""
    keys_88 = set(ad9088_tx.quick_configuration_modes["jesd204c"].keys())
    keys_84 = set(ad9084_tx.quick_configuration_modes["jesd204c"].keys())
    # AD9088 is 8T8R, AD9084 is 4T4R — their valid mode sets differ
    assert keys_88 != keys_84


# ── Clock names ──────────────────────────────────────────────────────────────


def test_ad9088_tx_required_clock_names():
    """Verify required clock names reference AD9088, not AD9084."""
    tx = ad9088_tx(solver="CPLEX")
    names = tx.get_required_clock_names()
    assert len(names) == 2
    assert all("AD9088" in n for n in names)
    assert any("ref_clk" in n for n in names)
    assert any("sysref" in n for n in names)


def test_ad9088_tx_clock_names_differ_from_ad9084_tx():
    """Verify AD9088_TX and AD9084_TX return different clock name prefixes."""
    names_88 = ad9088_tx(solver="CPLEX").get_required_clock_names()
    names_84 = ad9084_tx(solver="CPLEX").get_required_clock_names()
    assert names_88 != names_84
    assert all("AD9084" not in n for n in names_88)


# ── Sample clock ─────────────────────────────────────────────────────────────


def test_ad9088_tx_sample_clock_setter():
    """Verify sample clock can be assigned."""
    sys = adijif.system(
        "ad9088_tx", "hmc7044", "xilinx", 125000000, solver="CPLEX"
    )
    sys.converter.sample_clock = 0.5e9
    assert sys.converter.sample_clock == 0.5e9


def test_ad9088_tx_sample_clock_limits():
    """Verify sample clock limits are set for AD9088."""
    tx = ad9088_tx(solver="CPLEX")
    assert tx.sample_clock_max == 16e9
    assert tx.sample_clock_min == pytest.approx(5e9 / (12 * 64))


# ── supported_parts registry ─────────────────────────────────────────────────


def test_ad9088_tx_in_supported_parts():
    """Verify ad9088_tx is listed in the supported_parts registry."""
    from adijif import converters

    assert "ad9088_tx" in converters.supported_parts
