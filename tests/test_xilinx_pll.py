# flake8: noqa
from pprint import pprint

import pytest

import adijif as jif
import adijif.fpgas.xilinx.sevenseries as xp
import adijif.fpgas.xilinx.ultrascaleplus as us


@pytest.mark.parametrize("pll, out_clock", [("cpll", 0.5e9), ("qpll", 10e9)])
def test_7s_pll(pll, out_clock):
    ss_plls = xp.SevenSeries(transceiver_type="GTXE2", solver="CPLEX")

    in_clock = int(100e6)
    out_clock = int(out_clock)
    cnv = jif.ad9680()

    # Change sample rate to get to the desired bit clock
    # sample_rate * cnv.Np * cnv.M * (cnv.encoding_d / cnv.encoding_n) / cnv.L = bit_clock
    sample_rate = (
        out_clock * cnv.L / (cnv.Np * cnv.M * (cnv.encoding_d / cnv.encoding_n))
    )
    cnv.sample_clock = sample_rate

    assert cnv.bit_clock == out_clock

    cfg = {}
    config = ss_plls.add_constraints(cfg, in_clock, cnv)

    print(ss_plls.model.export_model())

    ss_plls.solve()
    print(ss_plls.solution.print_solution())

    cfg = ss_plls.get_config(config, cnv, in_clock)
    pprint(cfg)

    if cfg["type"] == "cpll":
        pll_out = (in_clock * cfg["n1"] * cfg["n2"]) / cfg["m"]
        lane_rate = pll_out * 2 / cfg["d"]
    else:
        pll_out = in_clock * cfg["n"] / (cfg["m"] * 2)
        lane_rate = pll_out * 2 / cfg["d"]

    assert lane_rate == cnv.bit_clock

    assert cfg["type"] == pll


@pytest.mark.parametrize(
    "pll, out_clock",
    [
        ("cpll", 0.5e9),
        ("qpll", 14e9),
        ("qpll", 32e9),
        ("qpll1", 9e9),
    ],  # No frac mode
)
def test_us_pll(pll, out_clock):
    us_plls = us.UltraScalePlus(transceiver_type="GTYE4", solver="CPLEX")
    us_plls.plls["QPLL"].force_integer_mode = True
    us_plls.plls["QPLL1"].force_integer_mode = True

    in_clock = int(100e6)
    out_clock = int(out_clock)
    cnv = jif.ad9680()

    # Change sample rate to get to the desired bit clock
    # sample_rate * cnv.Np * cnv.M * (cnv.encoding_d / cnv.encoding_n) / cnv.L = bit_clock
    sample_rate = (
        out_clock * cnv.L / (cnv.Np * cnv.M * (cnv.encoding_d / cnv.encoding_n))
    )
    cnv.sample_clock = sample_rate

    assert cnv.bit_clock == out_clock

    cfg = {}
    config = us_plls.add_constraints(cfg, in_clock, cnv)

    print(us_plls.model.export_model())

    us_plls.solve()
    print(us_plls.solution.print_solution())

    cfg = us_plls.get_config(config, cnv, in_clock)
    pprint(cfg)

    if cfg["type"] == "cpll":
        pll_out = (in_clock * cfg["n1"] * cfg["n2"]) / cfg["m"]
        lane_rate = pll_out * 2 / cfg["d"]
    else:
        pll_out = in_clock * cfg["n"] / (cfg["m"] * cfg["clkout_rate"])
        lane_rate = pll_out * 2 / cfg["d"]

    assert lane_rate == cnv.bit_clock

    assert cfg["type"] == pll
