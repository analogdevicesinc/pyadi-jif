import pytest
from adijif.converters.ad9152 import ad9152

def test_ad9152_initialization():
    converter = ad9152()
    assert converter.name == "AD9152"
    assert converter.converter_type == "DAC"
    assert converter.sample_clock == 1e9
    assert converter.interpolation == 1

def test_ad9152_jesd_modes():
    converter = ad9152()
    assert "jesd204b" in converter.available_jesd_modes
    # AD9152 specific modes (0, 1, 2, 3, 4, 5, 6, 7, 9, 10)
    assert "9" in converter.quick_configuration_modes["jesd204b"]

def test_ad9152_clock_constraints():
    converter = ad9152()
    assert converter.converter_clock_max == 2.25e9
    assert converter.sample_clock_max == 2.25e9

def test_ad9152_get_required_clock_names():
    converter = ad9152()
    names = converter.get_required_clock_names()
    assert "ad9152_ref_clk" in names
    assert "ad9152_sysref" in names

def test_ad9152_validate_config():
    converter = ad9152()
    converter.sample_clock = 1e9
    converter.interpolation = 1
    converter.set_quick_configuration_mode("4")
    # Should not raise exception
    converter.validate_config()
