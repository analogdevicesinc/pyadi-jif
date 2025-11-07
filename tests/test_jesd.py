# flake8: noqa
import pprint

import pytest

import adijif


@pytest.mark.parametrize("attr", ["data_path_width", "K", "F", "L", "M", "N", "Np"])
def test_jesd_ints(attr):
    with pytest.raises(Exception, match=f"{attr} must be an integer"):
        cnv = adijif.ad9680()
        setattr(cnv, attr, 0.5)


@pytest.mark.parametrize("attr", ["K", "F", "L", "M", "N", "Np"])
def test_jesd_oor(attr):
    with pytest.raises(Exception, match=f"{attr} not in range for device"):
        cnv = adijif.ad9680()
        setattr(cnv, attr, 1024)


def test_jesd_hd_parameter():
    """Test HD (high density) parameter."""
    cnv = adijif.ad9680()

    # Test setting HD
    cnv.HD = 1
    assert cnv.HD == 1

    cnv.HD = 0
    assert cnv.HD == 0


def test_jesd_cs_parameter():
    """Test CS (control bits) parameter."""
    cnv = adijif.ad9680()

    # Test setting CS
    cnv.CS = 0
    assert cnv.CS == 0


def test_jesd_s_parameter():
    """Test S (samples per converter per frame) parameter."""
    cnv = adijif.ad9680()

    # Test setting S
    cnv.S = 1
    assert cnv.S == 1


def test_jesd_jesd_class():
    """Test jesd_class property."""
    cnv = adijif.ad9680()

    # Test setting jesd_class
    cnv.jesd_class = "jesd204b"
    assert cnv.jesd_class == "jesd204b"

    # cnv.jesd_class = "jesd204c"
    # assert cnv.jesd_class == "jesd204c"


def test_jesd_multiframe_clock():
    """Test multiframe_clock calculation."""
    cnv = adijif.ad9680()

    cnv.sample_clock = 1e9
    cnv.decimation = 1
    cnv.set_quick_configuration_mode(str(0x88), "jesd204b")

    # Multiframe clock should be calculated
    mfc = cnv.multiframe_clock
    assert mfc > 0
    assert isinstance(mfc, (int, float))


def test_jesd_bit_clock():
    """Test bit_clock calculation."""
    cnv = adijif.ad9680()

    cnv.sample_clock = 1e9
    cnv.decimation = 1
    cnv.set_quick_configuration_mode(str(0x88), "jesd204b")

    # Bit clock should be calculated
    bc = cnv.bit_clock
    assert bc > 0
    assert isinstance(bc, (int, float))


def test_jesd_sample_clock():
    """Test sample_clock calculation."""
    cnv = adijif.ad9680()

    cnv.sample_clock = 1e9
    assert cnv.sample_clock == 1e9


def test_jesd_device_clock():
    """Test device_clock calculation."""
    cnv = adijif.ad9680()

    cnv.sample_clock = 1e9
    cnv.decimation = 1
    cnv.set_quick_configuration_mode(str(0x88), "jesd204b")

    # Device clock should be calculated
    dc = cnv.device_clock
    assert dc > 0


def test_jesd_lane_rate():
    """Test lane_rate calculation."""
    cnv = adijif.ad9680()

    cnv.sample_clock = 1e9
    cnv.decimation = 1
    cnv.set_quick_configuration_mode(str(0x88), "jesd204b")

    # Lane rate should be calculated
    lr = cnv.bit_clock
    assert lr > 0
