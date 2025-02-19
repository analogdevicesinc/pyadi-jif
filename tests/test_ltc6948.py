# flake8: noqa
import pprint

import pytest

import adijif


def test_ltc6948_fraction_mode():
    ref_in = int(100e6)

    clk = adijif.ltc6948()
    clk.minimize_feedback_dividers = False

    clk.fractional_mode = True
    rf_out = 1921.65e6
    clk.r = 2
    clock_names = "CLK"
    clk.set_requested_clocks(ref_in, rf_out, clock_names, tolerance=0.00000001)

    clk.solve()

    o = clk.get_config()

    pprint.pprint(o)

    rf_out_est = o["output_clocks"][clock_names]["rate"]
    error = rf_out_est - rf_out
    print(f"Error: {error} Hz")

    assert abs(error + 3.5603840) < 1e-3
