# flake8: noqa
from pprint import pprint

import pytest

import adijif as jif
import adijif.fpgas.xilinx.versal as versal


@pytest.mark.parametrize(
    "out_clock",
    [
        0.5e9,  # Low lane rate - RPLL range
        5e9,  # Mid lane rate - RPLL/LCPLL overlap
        10e9,  # Mid-high lane rate - LCPLL range
        24e9,  # High lane rate - LCPLL range
    ],
)
def test_versal_pll(out_clock):
    """Test Versal PLL configurations for various lane rates."""
    versal_plls = versal.Versal(transceiver_type="GTYE5", solver="CPLEX")
    # Force integer mode for consistent testing
    versal_plls.plls["RPLL"].force_integer_mode = True
    versal_plls.plls["LCPLL"].force_integer_mode = True

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
    config = versal_plls.add_constraints(cfg, in_clock, cnv)

    versal_plls.solve()

    cfg = versal_plls.get_config(config, cnv, in_clock)
    pprint(cfg)

    # Verify one of the 2 PLLs was selected (rpll or lcpll)
    assert cfg["type"] in ["rpll", "lcpll"]

    # Verify lane rate calculation
    if cfg["type"] == "rpll":
        # RPLL: f_VCO = f_REFCLK × (N / M)
        #       f_PLLCLKOUT = f_VCO (no CLKOUTRATE divider)
        #       f_Linerate = (f_PLLCLKOUT × 2) / D
        pll_out = in_clock * cfg["n"] / cfg["m"]
        lane_rate = pll_out * 2 / cfg["d"]
    else:  # lcpll
        # LCPLL: f_VCO = f_REFCLK × (N / M)
        #        f_PLLCLKOUT = f_VCO / LCPLL_CLKOUTRATE
        #        f_Linerate = (f_PLLCLKOUT × 2) / D
        pll_out = in_clock * cfg["n"] / (cfg["m"] * cfg["clkout_rate"])
        lane_rate = pll_out * 2 / cfg["d"]

    assert lane_rate == cnv.bit_clock


@pytest.mark.parametrize(
    "force_pll",
    [
        "rpll",
        "lcpll",
    ],
)
def test_versal_force_pll(force_pll):
    """Test force_rpll and force_lcpll flags work correctly."""
    versal_plls = versal.Versal(transceiver_type="GTYE5", solver="CPLEX")
    versal_plls.plls["RPLL"].force_integer_mode = True
    versal_plls.plls["LCPLL"].force_integer_mode = True

    # Set force flag for the desired PLL
    if force_pll == "rpll":
        versal_plls.force_rpll = True
        out_clock = int(2e9)  # Lane rate suitable for RPLL (4.0-8.0 GHz VCO)
    else:  # lcpll
        versal_plls.force_lcpll = True
        out_clock = int(12e9)  # Lane rate suitable for LCPLL (8.0-16.375 GHz VCO)

    in_clock = int(100e6)
    cnv = jif.ad9680()

    sample_rate = (
        out_clock * cnv.L / (cnv.Np * cnv.M * (cnv.encoding_d / cnv.encoding_n))
    )
    cnv.sample_clock = sample_rate

    assert cnv.bit_clock == out_clock

    cfg = {}
    config = versal_plls.add_constraints(cfg, in_clock, cnv)

    versal_plls.solve()

    cfg = versal_plls.get_config(config, cnv, in_clock)
    pprint(cfg)

    assert cfg["type"] == force_pll


def test_versal_gtyp_transceiver():
    """Test Versal GTYP transceiver type."""
    versal_plls = versal.Versal(transceiver_type="GTYP", solver="CPLEX")
    versal_plls.plls["RPLL"].force_integer_mode = True
    versal_plls.plls["LCPLL"].force_integer_mode = True

    in_clock = int(100e6)
    out_clock = int(15e9)
    cnv = jif.ad9680()

    sample_rate = (
        out_clock * cnv.L / (cnv.Np * cnv.M * (cnv.encoding_d / cnv.encoding_n))
    )
    cnv.sample_clock = sample_rate

    assert cnv.bit_clock == out_clock

    cfg = {}
    config = versal_plls.add_constraints(cfg, in_clock, cnv)

    versal_plls.solve()

    cfg = versal_plls.get_config(config, cnv, in_clock)
    pprint(cfg)

    # Just verify it solves successfully with GTYP
    assert cfg["type"] in ["rpll", "lcpll"]


@pytest.mark.parametrize(
    "out_clock",
    [
        10e9,
        20e9,
    ],
)
def test_versal_lcpll_fractional_mode(out_clock):
    """Test LCPLL fractional-N mode for various lane rates."""
    versal_plls = versal.Versal(transceiver_type="GTYE5", solver="CPLEX")
    versal_plls.force_lcpll = True
    # Don't force integer mode to allow fractional-N

    in_clock = int(100e6)
    out_clock = int(out_clock)
    cnv = jif.ad9680()

    sample_rate = (
        out_clock * cnv.L / (cnv.Np * cnv.M * (cnv.encoding_d / cnv.encoding_n))
    )
    cnv.sample_clock = sample_rate

    assert cnv.bit_clock == out_clock

    cfg = {}
    config = versal_plls.add_constraints(cfg, in_clock, cnv)

    versal_plls.solve()

    cfg = versal_plls.get_config(config, cnv, in_clock)
    pprint(cfg)

    assert cfg["type"] == "lcpll"

    # Check VCO range
    assert cfg["vco"] >= 8e9
    assert cfg["vco"] <= 16.375e9

    # Verify lane rate calculation
    pll_out = in_clock * cfg["n"] / (cfg["m"] * cfg["clkout_rate"])
    lane_rate = pll_out * 2 / cfg["d"]
    assert abs(lane_rate - cnv.bit_clock) < 1e3  # Allow small floating point error


def test_versal_rpll_fractional_mode():
    """Test RPLL fractional-N mode."""
    versal_plls = versal.Versal(transceiver_type="GTYE5", solver="CPLEX")
    versal_plls.force_rpll = True
    # Don't force integer mode to allow fractional-N

    in_clock = int(100e6)
    out_clock = int(4e9)  # 4 Gb/s lane rate
    cnv = jif.ad9680()

    sample_rate = (
        out_clock * cnv.L / (cnv.Np * cnv.M * (cnv.encoding_d / cnv.encoding_n))
    )
    cnv.sample_clock = sample_rate

    assert cnv.bit_clock == out_clock

    cfg = {}
    config = versal_plls.add_constraints(cfg, in_clock, cnv)

    versal_plls.solve()

    cfg = versal_plls.get_config(config, cnv, in_clock)
    pprint(cfg)

    assert cfg["type"] == "rpll"

    # Check VCO range
    assert cfg["vco"] >= 4e9
    assert cfg["vco"] <= 8e9

    # Verify lane rate calculation
    # RPLL has no CLKOUTRATE divider
    pll_out = in_clock * cfg["n"] / cfg["m"]
    lane_rate = pll_out * 2 / cfg["d"]
    assert abs(lane_rate - cnv.bit_clock) < 1e3  # Allow small floating point error
