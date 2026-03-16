import pytest
from adijif.converters.ad9152_dp import ad9152_dp

def test_ad9152_dp_initialization():
    dp = ad9152_dp()
    assert dp.interpolation == 1
    assert dp.interpolation_available == [1, 2, 4, 8]

def test_ad9152_dp_set_interpolation():
    dp = ad9152_dp()
    dp.interpolation = 4
    assert dp.interpolation == 4

def test_ad9152_dp_invalid_interpolation():
    dp = ad9152_dp()
    with pytest.raises(TypeError):
        dp.interpolation = 3

def test_ad9152_dp_get_config():
    dp = ad9152_dp()
    dp.interpolation = 2
    config = dp.get_config()
    assert config["interpolation"] == 2
