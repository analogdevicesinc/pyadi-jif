"""Additional tests for adijif.converters.converter to improve coverage."""

import pytest

from adijif.converters.converter import converter


class MockConverter(converter):
    """Minimal implementation of converter for testing base class methods."""

    name = "MockConv"
    converter_type = "adc"
    clocking_option_available = ["direct"]
    quick_configuration_modes = {
        "jesd204b": {
            "1": {"L": 1, "M": 1, "F": 2, "S": 1, "K": 32, "N": 16, "Np": 16}
        }
    }
    converter_clock_min = 1e6
    converter_clock_max = 1e9
    sample_clock_max = 1e9
    device_clock_available = None
    device_clock_ranges = None
    available_jesd_modes = ["jesd204b"]
    L_available = [1, 99]
    M_available = [1]
    F_available = [2]
    S_available = [1]
    K_available = [32]
    N_available = [16]
    Np_available = [16]

    def _check_valid_internal_configuration(self) -> None:
        pass

    def get_required_clocks(self):
        return []

    def get_required_clock_names(self):
        return []

    def get_config(self, solution=None):
        return {}


def test_converter_draw_unknown_type_should_raise():
    """Verify draw raises on unknown converter type."""
    conv = MockConverter()
    conv.converter_type = "invalid"
    with pytest.raises(Exception, match="Unknown converter type"):
        conv.draw(clocks={})


def test_converter_set_quick_config_invalid_class_should_raise():
    """Verify set_quick_configuration_mode raises on invalid jesd_class."""
    conv = MockConverter()
    with pytest.raises(Exception, match="not available for JESD class"):
        conv.set_quick_configuration_mode("1", jesd_class="invalid")


def test_converter_set_quick_config_invalid_mode_should_raise():
    """Verify set_quick_configuration_mode raises on invalid mode."""
    conv = MockConverter()
    with pytest.raises(Exception, match="not among configurations"):
        conv.set_quick_configuration_mode("99", jesd_class="jesd204b")


def test_converter_check_valid_jesd_mode_invalid_should_raise():
    """Verify _check_valid_jesd_mode raises on invalid current config."""
    conv = MockConverter()
    conv.L = 99  # Not in the mock mode
    with pytest.raises(Exception, match="Invalid JESD configuration"):
        conv._check_valid_jesd_mode()


def test_converter_str_representation():
    """Verify __str__ representation."""
    conv = MockConverter()
    assert str(conv) == "MockConv data converter model"


def test_converter_get_current_jesd_mode_settings():
    """Verify get_current_jesd_mode_settings."""
    conv = MockConverter()
    conv.set_quick_configuration_mode("1")
    settings = conv.get_current_jesd_mode_settings()
    assert settings["L"] == 1
    assert settings["M"] == 1


def test_converter_draw_adc_no_clocks_should_raise():
    """Verify draw_adc raises when required clocks are missing."""
    conv = MockConverter()
    with pytest.raises(Exception, match="No clock found for mockconv_ref_clk"):
        conv.draw_adc(clocks={})


def test_converter_draw_adc_missing_sysref_should_raise():
    """Verify draw_adc raises when sysref clock is missing."""
    conv = MockConverter()
    clocks = {"mockconv_ref_clk": 1e9}
    with pytest.raises(Exception, match="No clock found for mockconv_sysref"):
        conv.draw_adc(clocks=clocks)


def test_converter_draw_dac_no_clocks_should_raise():
    """Verify draw_dac raises when required clocks are missing."""
    conv = MockConverter()
    conv.converter_type = "dac"
    with pytest.raises(Exception, match="No clock found for mockconv_ref_clk"):
        conv.draw_dac(clocks={})


def test_converter_draw_dac_missing_sysref_should_raise():
    """Verify draw_dac raises when sysref clock is missing."""
    conv = MockConverter()
    conv.converter_type = "dac"
    clocks = {"mockconv_ref_clk": 1e9}
    with pytest.raises(Exception, match="No clock found for mockconv_sysref"):
        conv.draw_dac(clocks=clocks)
