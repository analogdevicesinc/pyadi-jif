"""Additional tests for LTC clock chips to improve coverage."""

import pytest

import adijif


def test_ltc6953_m_setter_range():
    """Verify m setter with a list of values."""
    clk = adijif.ltc6953()
    clk.m = [1, 2, 4, 8]
    # In ltc6953.py, setter sets self._d
    assert clk._d == [1, 2, 4, 8]


def test_ltc6953_m_setter_invalid_should_raise():
    """Verify m setter raises on out-of-range value."""
    clk = adijif.ltc6953()
    with pytest.raises(Exception, match="invalid for d"):
        clk.m = 9999


def test_ltc6953_set_requested_clocks_size_mismatch_should_raise():
    """Verify set_requested_clocks raises on list size mismatch."""
    clk = adijif.ltc6953()
    with pytest.raises(Exception, match="not the same size"):
        clk.set_requested_clocks(1e9, [500e6], ["CLK1", "CLK2"])


def test_ltc6953_solve_range_input():
    """Verify solving with range input reference."""
    clk = adijif.ltc6953(solver="CPLEX")
    # adijif.types.range requires ints
    vcxo = adijif.types.range(int(100e6), int(200e6), int(1e6), "vcxo")
    clk.set_requested_clocks(vcxo, [50e6], ["CLK1"])

    clk.solve()
    config = clk.get_config()
    assert "input_ref" in config
    assert config["output_clocks"]["CLK1"]["divider"] in [2, 3, 4]


def test_ltc6953_solve_arb_source_input():
    """Verify solving with arb_source input reference."""
    clk = adijif.ltc6953(solver="CPLEX")
    vcxo = adijif.types.arb_source("vcxo", 1)
    clk.set_requested_clocks(vcxo, [100e6], ["CLK1"])

    # Manually add constraint for arb_source since it's free
    clk._add_equation(vcxo(clk.model) == 500e6)

    clk.solve()
    config = clk.get_config()
    assert config["input_ref"] == 500e6
    assert config["output_clocks"]["CLK1"]["divider"] == 5


def test_ltc6952_m_setter():
    """Verify LTC6952 m setter."""
    clk = adijif.ltc6952()
    clk.m = 2
    assert clk.m == 2


def test_ltc6952_solve_smoke():
    """Verify LTC6952 solve."""
    clk = adijif.ltc6952(solver="CPLEX")
    clk.set_requested_clocks(125e6, [125e6, 62.5e6], ["C1", "C2"])

    # Set some properties to exercise them
    clk.vco_min = 1e9
    clk.vco_max = 4e9
    clk.minimize_feedback_dividers = True
    clk.n2 = [*range(8, 4000)]
    clk.r2 = 1

    clk.solve()
    config = clk.get_config()
    assert config is not None
    assert "VCO" in config
    assert config["VCO"] >= 1e9
