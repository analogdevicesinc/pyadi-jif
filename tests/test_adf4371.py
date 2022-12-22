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

    D = o['d']
    R = o['r']
    T = o['t']
    INT = o['int']
    FRAC1 = o['frac1']
    FRAC2 = o['frac2']
    MOD2 = o['MOD2']
    rf_div = o['rf_div']

    MOD1 = 2**25

    F_PFD = ref_in * (1+D)/(R*(1+T))
    vco = (INT + (FRAC1 + FRAC2/MOD2)/MOD1) * F_PFD

    assert vco == 2112.8e6 * rf_div
    assert vco / rf_div == float(output_clocks)
