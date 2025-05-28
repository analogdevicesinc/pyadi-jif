# flake8: noqa
import pprint

import pytest

import adijif


def test_adf4382_integer_datasheet_example():

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
    pll.mode = "integer"

    output_clocks = int(20e9)

    pll.set_requested_clocks(ref_in, output_clocks)

    pll.solve()

    cfg = pll.get_config()
    pprint.pprint(cfg)

    assert (
        output_clocks == cfg["rf_out_frequency"]
    ), "Output frequency does not match requested"


def test_adf4382_frac_datasheet_org():
    ref_in = int(250e6)

    pll = adijif.adf4382()
    pll.mode = "fractional"
    pll.require_phase_sync = False
    pll.d = 1
    pll.o = 1
    pll.r = 1
    pll.n = 80

    # val1 = (17716740 + 1500000/15625000)/ 33554432

    # Since the values are a bit arbitrary, we can just set a few of them to the
    # values in the datasheet
    pll._frac1_min_max = [17716740, 17716740]
    pll._frac2_min_max = [1500000, 1500000]

    output_clocks = int(20.132e9)

    pll.set_requested_clocks(ref_in, output_clocks)

    pll.solve()

    cfg = pll.get_config()
    pprint.pprint(cfg)

    n = cfg["n_int"] + (cfg["n_frac1w"] + cfg["n_frac2w"] / cfg["MOD2"]) / pll._MOD1
    rf_out = ref_in * cfg["d"] * n / cfg["r"]
    print(f"RF Out: {rf_out}")

    # Verify with high precision
    import mpmath as mp

    mp.mp.dps = 50
    frac1 = mp.mpf(cfg["n_frac1w"])
    frac2 = mp.mpf(cfg["n_frac2w"])
    MOD2 = mp.mpf(cfg["MOD2"])
    MOD1 = mp.mpf(33554432)
    n_int = mp.mpf(cfg["n_int"])
    rf_out_hp = ref_in * cfg["d"] * (n_int + (frac1 + frac2 / MOD2) / MOD1) / cfg["r"]
    print(f"RF Out HP: {rf_out_hp}")
    assert rf_out_hp == pytest.approx(rf_out, rel=1e-6)

    assert (
        output_clocks == cfg["rf_out_frequency"]
    ), "Output frequency does not match requested"
    assert cfg["n_frac1w"] == 17716740, "Fractional part 1 does not match datasheet"
    assert cfg["n_frac2w"] == 1500000, "Fractional part 2 does not match datasheet"
    assert cfg["MOD2"] == 15625000, "MOD2 does not match datasheet"


def test_adf4382_frac_datasheet_auto():
    ref_in = int(250e6)

    pll = adijif.adf4382()
    pll.mode = ["fractional", "integer"]

    output_clocks = int(20.132e9)
    pll.set_requested_clocks(ref_in, output_clocks)

    pll.solve()

    cfg = pll.get_config()
    pprint.pprint(cfg)

    n = cfg["n_int"] + (cfg["n_frac1w"] + cfg["n_frac2w"] / cfg["MOD2"]) / pll._MOD1
    rf_out = ref_in * cfg["d"] * n / cfg["r"]
    print(f"RF Out: {rf_out}")

    # Verify with high precision
    import mpmath as mp

    mp.mp.dps = 50
    frac1 = mp.mpf(cfg["n_frac1w"])
    frac2 = mp.mpf(cfg["n_frac2w"])
    MOD2 = mp.mpf(cfg["MOD2"])
    MOD1 = mp.mpf(33554432)
    n_int = mp.mpf(cfg["n_int"])
    rf_out_hp = ref_in * cfg["d"] * (n_int + (frac1 + frac2 / MOD2) / MOD1) / cfg["r"]
    print(f"RF Out HP: {rf_out_hp}")
    assert rf_out_hp == pytest.approx(rf_out, rel=1e-6)

    assert (
        output_clocks == cfg["rf_out_frequency"]
    ), "Output frequency does not match requested"
