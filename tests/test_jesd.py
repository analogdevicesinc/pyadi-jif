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
