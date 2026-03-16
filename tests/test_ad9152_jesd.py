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

def test_ad9152_jesd_mode_11_unique():
    converter = ad9152()
    # Mode 11 should exist for AD9152 but not for AD9144 (base class)
    converter.set_quick_configuration_mode("11")
    assert converter.L == 2
    assert converter.M == 1
    assert converter.S == 2
    assert converter.F == 2

def test_ad9152_jesd_mode_12_unique():
    converter = ad9152()
    # Mode 12 should exist for AD9152
    converter.set_quick_configuration_mode("12")
    assert converter.L == 1
    assert converter.M == 1
    assert converter.S == 2
    assert converter.F == 4
