import pytest
from adijif.converters.ad9152 import ad9152

def test_ad9152_pll_vco_range_div4():
    converter = ad9152()
    converter.sample_clock = 2e9
    converter.interpolation = 1
    converter.clocking_option = "integrated_pll"
    # dac_clk = 2e9, lo_div = 4, vco = 8e9 (Within 6.75e9 to 12.3e9)
    converter._pll_config()
    assert converter.config["lo_div_mode_p2"] == 4

def test_ad9152_pll_vco_range_div8():
    converter = ad9152()
    converter.sample_clock = 1e9
    converter.interpolation = 1
    converter.clocking_option = "integrated_pll"
    # dac_clk = 1e9, lo_div = 8, vco = 8e9 (Within 6.75e9 to 12.3e9)
    converter._pll_config()
    assert converter.config["lo_div_mode_p2"] == 8

def test_ad9152_pll_vco_range_div16():
    converter = ad9152()
    converter.sample_clock = 500e6
    converter.interpolation = 1
    converter.clocking_option = "integrated_pll"
    # dac_clk = 500e6, lo_div = 16, vco = 8e9 (Within 6.75e9 to 12.3e9)
    converter._pll_config()
    assert converter.config["lo_div_mode_p2"] == 16

def test_ad9152_pll_vco_out_of_range():
    converter = ad9152()
    converter.sample_clock = 1.6e9
    converter.interpolation = 1
    converter.clocking_option = "integrated_pll"
    # dac_clk = 1.6e9. 
    # If lo_div=4, vco=6.4e9 (Too slow, min 6.75e9)
    # If lo_div=8, vco=12.8e9 (Too fast, max 12.3e9)
    with pytest.raises(Exception, match="DAC Clock and VCO range mismatch"):
        converter._pll_config()
