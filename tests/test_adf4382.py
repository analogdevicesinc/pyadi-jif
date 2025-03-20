# flake8: noqa
import pprint

import pytest

import adijif


def test_adf4382_datasheet_example():

    # Reference example from AD9084 system
    ######################
    pll = adijif.adf4382()

    ref_in = int(125e6 / 2)
    output_clocks = int(8e9)
    pll.n = 128
    pll.d = 1
    pll.o = 2

    # adf4382 spi3.0: VCO=16000000000 PFD=62500000 RFout_div=2 N=128 FRAC1=0 FRAC2=0 MOD2=0
    o = 2  #
    n = 128  #
    d = 1  # 1
    r = 1
    vco_ref = ref_in * d * n * o / r
    pfd_ref = ref_in * d / r

    pll.set_requested_clocks(ref_in, output_clocks)

    pll.solve()

    cfg = pll.get_config()

    pprint.pprint(cfg)

    pfd = ref_in * cfg["d"] / cfg["r"]
    vco = pfd * cfg["n"] * cfg["o"]
    rf_out = vco / cfg["o"]

    print(f"PFD: {pfd}")
    print(f"VCO: {vco}")
    print(f"RF Out: {rf_out}")

    assert rf_out == output_clocks, "Output frequency does not match requested"
    assert cfg["o"] == o, "Output divider does not match datasheet example"
    assert cfg["n"] == n, "N divider does not match datasheet example"
    assert cfg["d"] == d, "D divider does not match datasheet example"
    assert cfg["r"] == r, "R divider does not match datasheet example"
    assert vco == vco_ref, "VCO frequency does not match datasheet example"
    assert pfd == pfd_ref, "PFD frequency does not match datasheet example"


@pytest.mark.parametrize(
    "ref_in", [int(125e6), int(125e6 / 2), int(125e6 / 4), int(125e6 / 8)]
)
def test_adf4382_auto_20g(ref_in):
    pll = adijif.adf4382()

    output_clocks = int(20e9)

    pll.set_requested_clocks(ref_in, output_clocks)

    pll.solve()

    cfg = pll.get_config()
    pprint.pprint(cfg)

    assert (
        output_clocks == cfg["rf_out_frequency"]
    ), "Output frequency does not match requested"
