# flake8: noqa
import pprint

import pytest

import adijif


def test_adf4371_datasheet_example():

    pll = adijif.adf4371()
    pll._MOD2 = 1536
    pll.rf_div = 2
    pll._mode = "fractional"

    ref_in = int(122.88e6)
    output_clocks = int(2112.8e6)

    pll.set_requested_clocks(ref_in, output_clocks)

    pll.solve()

    o = pll.get_config()

    pprint.pprint(o)
