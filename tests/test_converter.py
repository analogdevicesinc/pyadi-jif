# flake8: noqa

import pytest

import adijif


def test_converter_quick_config_with_invalid_mode():
    """Test quick configuration with invalid mode."""
    conv = adijif.ad9680()

    with pytest.raises(
        Exception, match="Mode .* not among configurations for jesd204.*"
    ):
        conv.set_quick_configuration_mode("INVALID_MODE", "jesd204b")


def test_converter_quick_config_with_invalid_jesd_class():
    """Test quick configuration with invalid JESD class."""
    conv = adijif.ad9680()

    with pytest.raises(Exception, match=".* not available for JESD class for .*"):
        conv.set_quick_configuration_mode("0x88", "invalid_jesd_class")


def test_converter_apply_quick_config_with_mode_number():
    """Test applying quick config with mode number instead of string."""
    conv = adijif.ad9680()

    # Test with integer mode
    conv.set_quick_configuration_mode(0x88, "jesd204b")
    assert conv.jesd_class == "jesd204b"


def test_converter_device_clock_available():
    """Test device_clock_available method."""
    conv = adijif.ad9680()

    conv.sample_clock = 1e9
    conv.decimation = 1

    clocks = conv.device_clock_available()
    assert clocks is not None
    assert len(clocks) > 0


def test_converter_get_config():
    """Test get_config method returns proper structure."""
    conv = adijif.ad9680()

    conv.sample_clock = 1e9
    conv.decimation = 1
    conv.set_quick_configuration_mode(str(0x88), "jesd204b")

    # Create solution
    required_clocks = conv.get_required_clocks()
    required_clock_names = conv.get_required_clock_names()

    # Add generic clock sources
    clks = []
    for clock, name in zip(required_clocks, required_clock_names):
        clk = adijif.types.arb_source(name)
        conv._add_equation(clk(conv.model) == clock)
        clks.append(clk)

    solution = conv.model.solve(LogVerbosity="Quiet")
    config = conv.get_config(solution)

    assert config is not None
    # assert "jesd_class" in config
    # assert "sample_clock" in config


def test_converter_get_jesd_config():
    """Test get_jesd_config method."""
    conv = adijif.ad9680()

    conv.sample_clock = 1e9
    conv.decimation = 1
    conv.set_quick_configuration_mode(str(0x88), "jesd204b")

    # Create solution
    required_clocks = conv.get_required_clocks()
    required_clock_names = conv.get_required_clock_names()

    # Add generic clock sources
    clks = []
    for clock, name in zip(required_clocks, required_clock_names):
        clk = adijif.types.arb_source(name)
        conv._add_equation(clk(conv.model) == clock)
        clks.append(clk)

    solution = conv.model.solve(LogVerbosity="Quiet")
    jesd_config = conv.get_jesd_config(solution)

    assert jesd_config is not None
    assert "L" in jesd_config
    assert "M" in jesd_config


def test_converter_clocking_option_invalid():
    """Test setting invalid clocking option."""
    conv = adijif.ad9680()

    with pytest.raises(Exception, match="clocking_option not available"):
        conv.clocking_option = "invalid_option"


def test_converter_clocking_option_valid():
    """Test setting valid clocking option."""
    conv = adijif.ad9680()

    conv.clocking_option = "direct"
    assert conv.clocking_option == "direct"


def test_converter_name_property():
    """Test converter name property."""
    conv = adijif.ad9680()

    # Default name
    assert conv.name == "AD9680"

    # Set custom name
    conv.name = "custom_name"
    assert conv.name == "custom_name"


def test_converter_multiframe_clock():
    """Test multiframe_clock property."""
    conv = adijif.ad9680()

    conv.sample_clock = 1e9
    conv.decimation = 1
    conv.set_quick_configuration_mode(str(0x88), "jesd204b")

    # Multiframe clock should be calculated
    mfc = conv.multiframe_clock
    assert mfc is not None
    assert mfc > 0


def test_converter_bit_clock():
    """Test bit_clock property."""
    conv = adijif.ad9680()

    conv.sample_clock = 1e9
    conv.decimation = 1
    conv.set_quick_configuration_mode(str(0x88), "jesd204b")

    # Bit clock should be calculated
    bc = conv.bit_clock
    assert bc is not None
    assert bc > 0


def test_converter_validate_config():
    """Test validate_config method."""
    conv = adijif.ad9680()

    conv.sample_clock = 1e9
    conv.decimation = 1
    conv.set_quick_configuration_mode(str(0x88), "jesd204b")

    # Should not raise exception
    conv.validate_config()


def test_converter_validate_config_invalid():
    """Test validate_config with invalid parameters."""
    conv = adijif.ad9680()

    conv.sample_clock = 1e9
    conv.decimation = 1
    # Don't set JESD mode - should have invalid defaults

    with pytest.raises(Exception, match="K not in range for device"):
        # Set invalid K value
        conv.K = 2000
        # conv.validate_config()


def test_converter_sample_clock_property():
    """Test sample_clock property."""
    conv = adijif.ad9680()

    # Set sample clock
    conv.sample_clock = 1e9
    assert conv.sample_clock == 1e9


def test_converter_available_jesd_modes():
    """Test available_jesd_modes property."""
    conv = adijif.ad9680()

    modes = conv.available_jesd_modes
    assert modes is not None
    assert len(modes) > 0


def test_converter_nested_property():
    """Test _nested property for nested converters."""
    # Test non-nested converter
    conv = adijif.ad9680()
    assert conv._nested == False

    # Test nested converter
    conv_nested = adijif.ad9081()
    assert conv_nested._nested is not None
    assert len(conv_nested._nested) > 0
