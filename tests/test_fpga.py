# flake8: noqa
import pprint

import pytest

import adijif


def test_jesd_unknown_dev():
    name = "zcu103"
    with pytest.raises(Exception, match=f"No boardname found in library for {name}"):
        f = adijif.xilinx()
        f.setup_by_dev_kit_name(name)


def test_jesd_wrong_order():
    msg = (
        "get_required_clocks must be run to generated"
        + " dependent clocks before names are available"
    )
    with pytest.raises(Exception, match=msg):
        f = adijif.xilinx()
        f.ref_clock_min = 60000000
        f.ref_clock_max = 670000000
        cn = f.get_required_clock_names()


def test_ref_clock_not_set():
    msg = "ref_clock_min or ref_clock_max not set"
    with pytest.raises(Exception, match=msg):
        f = adijif.xilinx()
        cn = f.get_required_clocks([], [])
