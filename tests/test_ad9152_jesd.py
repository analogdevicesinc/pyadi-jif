import pytest
from adijif.converters.ad9152 import ad9152

def test_ad9152_jesd_mode_4():
    converter = ad9152()
    converter.set_quick_configuration_mode("4")
    assert converter.L == 4
    assert converter.M == 2
    assert converter.S == 1
    assert converter.F == 1

def test_ad9152_jesd_mode_9():
    converter = ad9152()
    converter.set_quick_configuration_mode("9")
    assert converter.L == 2
    assert converter.M == 1
    assert converter.S == 1
    assert converter.F == 1

def test_ad9152_jesd_invalid_modes():
    converter = ad9152()
    # Modes 11 and 12 should not exist for AD9152
    with pytest.raises(Exception, match="Mode 11 not among configurations"):
        converter.set_quick_configuration_mode("11")
    with pytest.raises(Exception, match="Mode 12 not among configurations"):
        converter.set_quick_configuration_mode("12")
