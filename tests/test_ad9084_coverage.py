"""Additional tests for adijif.converters.ad9084 to improve coverage."""

import os

import pytest

import adijif


def test_ad9084_apply_profile_settings():
    """Verify that a profile can be applied to AD9084."""
    # Arrange
    here = os.path.dirname(os.path.abspath(__file__))
    profile_path = os.path.join(
        here, "apollo_profiles", "ad9084_profiles", "id00_stock_mode.json"
    )
    conv = adijif.ad9084_rx(solver="CPLEX")

    # Act
    conv.apply_profile_settings(profile_path, bypass_version_check=True)

    # Assert
    assert conv.sample_clock == 2500000000.0  # From profile
    assert conv.L == 8  # From profile


def test_ad9084_get_config_integrated_pll():
    """Verify get_config with integrated_pll option."""
    # Arrange
    conv = adijif.ad9084_rx(solver="CPLEX")
    # Manually allow integrated_pll for testing purposes as it's currently limited in model
    conv.clocking_option_available = ["integrated_pll", "direct", "external"]
    conv.clocking_option = "integrated_pll"

    # Mock some solved config values
    conv.config["m_vco"] = 8
    conv.config["n_vco"] = 10
    conv.config["r"] = 1
    conv.config["d"] = 1

    # Act
    config = conv.get_config()

    # Assert
    assert config["clocking_option"] == "integrated_pll"
    assert "pll_config" in config
    assert config["pll_config"]["m_vco"] == 8


def test_ad9084_get_required_clocks_external():
    """Verify get_required_clocks with external option."""
    # Arrange
    conv = adijif.ad9084_rx(solver="CPLEX")
    # Manually allow external for testing purposes
    conv.clocking_option_available = ["integrated_pll", "direct", "external"]
    conv.clocking_option = "external"

    # Act
    res = conv.get_required_clocks()

    # Assert
    assert len(res) == 2
    assert res[0] == []  # converter clock is empty for external


def test_ad9084_decimation_setter_should_raise():
    """Verify that decimation cannot be set directly."""
    # Arrange
    conv = adijif.ad9084_rx()

    # Act & Assert
    with pytest.raises(Exception, match="Decimation is not writable"):
        conv.decimation = 4


def test_ad9088_rx_initialization():
    """Verify AD9088_RX initializes correctly."""
    # Arrange & Act
    conv = adijif.ad9088_rx()

    # Assert
    assert conv.name == "AD9088_RX"
    assert conv.converter_clock_max == 8e9
    assert conv.sample_clock == 1e9


def test_ad9084_core_get_required_clock_names_9088():
    """Verify clock names for AD9088 flavor."""
    # Arrange
    conv = adijif.ad9088_rx()

    # Act
    names = conv.get_required_clock_names()

    # Assert
    assert "AD9088_ref_clk" in names
