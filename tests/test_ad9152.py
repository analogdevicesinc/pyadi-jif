"""Tests for the AD9152 DAC converter model."""

import pytest

import adijif


def test_ad9152_initialization_should_have_correct_defaults():
    """Verify AD9152 initializes with expected default properties."""
    # Arrange & Act
    conv = adijif.ad9152()

    # Assert
    assert conv.name == "AD9152"
    assert conv.converter_clock_max == 2.25e9
    assert conv.sample_clock_max == 2.25e9
    assert "jesd204b" in conv.quick_configuration_modes


def test_ad9152_interpolation_property_should_proxy_to_datapath():
    """Verify interpolation getter and setter correctly update the datapath."""
    # Arrange
    conv = adijif.ad9152()
    test_value = 4

    # Act
    conv.interpolation = test_value

    # Assert
    assert conv.interpolation == test_value
    assert conv.datapath.interpolation == test_value


def test_ad9152_get_required_clock_names_should_return_documented_list():
    """Verify required clock names match documentation."""
    # Arrange
    conv = adijif.ad9152()

    # Act
    names = conv.get_required_clock_names()

    # Assert
    assert names == ["ad9152_ref_clk", "ad9152_sysref"]


@pytest.mark.parametrize(
    "sample_rate, interpolation, expected_lo_div",
    [
        (500e6, 4, 4),  # dac_clk = 2.0 GHz -> div 4 (2**(1+1)=4)
        (300e6, 4, 8),  # dac_clk = 1.2 GHz -> div 8 (2**(2+1)=8)
        (150e6, 4, 16),  # dac_clk = 0.6 GHz -> div 16 (2**(3+1)=16)
    ],
)
def test_ad9152_pll_config_should_set_correct_lo_div(
    sample_rate: float, interpolation: int, expected_lo_div: int
):
    """Verify internal PLL configuration for different DAC clock ranges."""
    # Arrange
    conv = adijif.ad9152(solver="CPLEX")
    conv.sample_clock = sample_rate
    conv.interpolation = interpolation

    # Act
    conv._pll_config()

    # Assert
    # We check the intermediate value if possible or just that it didn't raise
    assert conv.config["lo_div_mode_p2"] == expected_lo_div


def test_ad9152_pll_config_should_raise_on_invalid_dac_clock():
    """Verify error handling for out-of-range DAC clock frequencies."""
    # Arrange
    conv = adijif.ad9152(solver="CPLEX")

    # Act & Assert: Too fast
    conv.sample_clock = 2.5e9
    conv.interpolation = 1
    with pytest.raises(Exception, match="DAC Clock too fast"):
        conv._pll_config()

    # Act & Assert: No match (gap between 1537.5 and 1687.5)
    conv.sample_clock = 1600e6
    conv.interpolation = 1
    with pytest.raises(Exception, match="DAC Clock and VCO range mismatch"):
        conv._pll_config()


def test_ad9152_solve_should_determine_ref_clk():
    """Verify that AD9152 can solve for its required reference clock."""
    # Arrange
    conv = adijif.ad9152(solver="CPLEX")
    conv.clocking_option = "integrated_pll"
    conv.sample_clock = 500e6
    conv.interpolation = 4
    conv.set_quick_configuration_mode("4", "jesd204b")

    # Act
    required_clocks = conv.get_required_clocks()
    required_clock_names = conv.get_required_clock_names()

    # Add generic clock sources to satisfy the model
    clks = []
    for clock, name in zip(required_clocks, required_clock_names, strict=False):
        clk = adijif.types.arb_source(name)
        conv._add_equation(clk(conv.model) == clock)
        clks.append(clk)

    solution = conv.model.solve(LogVerbosity="Quiet")
    config = conv.get_config(solution)

    # Assert
    assert config is not None
    assert "ref_div_factor" in config
    assert "BCount" in config
    assert "lo_div_mode" in config
    assert config["lo_div_mode"] == 2.0  # log2(4) = 2
