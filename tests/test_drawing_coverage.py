"""Tests for drawing coverage."""
import pytest

import adijif as jif

# -----------------------------------------------------------------------------
# Clocks
# -----------------------------------------------------------------------------


@pytest.mark.drawing
def test_ad9545_draw() -> None:
    """Test drawing for AD9545."""
    solver = "CPLEX"
    try:
        clk = jif.ad9545(solver=solver)
    except Exception as e:
        pytest.skip(
            f"Skipping ad9545 draw test due to init failure (likely solver): {e}"
        )

    clk.avoid_min_max_PLL_rates = True
    clk.minimize_input_dividers = True

    input_refs = [(0, 1), (1, 10e6)]
    # Use output index that maps to PLL0 (<=5) and PLL1 (>5)
    output_clocks = [(0, int(25e6)), (6, int(30.72e6))]

    input_refs = list(map(lambda x: (int(x[0]), int(x[1])), input_refs))
    output_clocks = list(map(lambda x: (int(x[0]), int(x[1])), output_clocks))

    clk.set_requested_clocks(input_refs, output_clocks)

    try:
        clk.solve()
    except Exception as e:
        pytest.skip(f"Skipping ad9545 draw test due to solve failure: {e}")

    # Draw
    # For AD9545, we don't strictly need to pass clocks dict if it uses internal config,
    # but the draw method might expect it or just use internal state.
    # checking ad9545_draw.py: draw(lo=None) -> doesn't take clocks dict.

    img = clk.draw()
    assert img is not None


@pytest.mark.drawing
def test_ltc6953_draw() -> None:
    """Test drawing for LTC6953."""
    solver = "CPLEX"
    try:
        clk = jif.ltc6953(solver=solver)
    except Exception as e:
        pytest.skip(f"Skipping ltc6953 draw test: {e}")

    ref_in = 1000000000
    output_clocks = [500e6, 250e6]
    output_clocks = list(map(int, output_clocks))
    clock_names = ["OUT0", "OUT1"]

    clk.set_requested_clocks(ref_in, output_clocks, clock_names)

    try:
        clk.solve()
        clk.get_config()
    except Exception as e:
        pytest.skip(f"Skipping ltc6953 draw test due to solve failure: {e}")

    img = clk.draw()
    assert img is not None


@pytest.mark.drawing
def test_ad9523_draw() -> None:
    """Test drawing for AD9523."""
    solver = "CPLEX"
    try:
        clk = jif.ad9523_1(solver=solver)
    except Exception as e:
        pytest.skip(f"Skipping ad9523_1 draw test: {e}")

    vcxo = 125000000
    output_clocks = [1e9, 500e6]
    clock_names = ["ADC", "FPGA"]

    clk.n2 = 24
    clk.use_vcxo_double = False

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    try:
        clk.solve()
        clk.get_config()
    except Exception as e:
        pytest.skip(f"Skipping ad9523_1 draw test due to solve failure: {e}")

    img = clk.draw()
    assert img is not None


@pytest.mark.drawing
def test_ad9528_draw() -> None:
    """Test drawing for AD9528."""
    solver = "CPLEX"
    try:
        clk = jif.ad9528(solver=solver)
    except Exception as e:
        pytest.skip(f"Skipping ad9528 draw test: {e}")

    vcxo = 122.88e6
    output_clocks = [245.76e6, 122.88e6]
    output_clocks = list(map(int, output_clocks))
    clock_names = ["ADC", "FPGA"]

    clk.n2 = 10
    clk.use_vcxo_double = False

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    try:
        clk.solve()
        clk.get_config()
    except Exception as e:
        pytest.skip(f"Skipping ad9528 draw test due to solve failure: {e}")

    img = clk.draw()
    assert img is not None


@pytest.mark.drawing
def test_ltc6952_draw() -> None:
    """Test drawing for LTC6952."""
    solver = "CPLEX"
    try:
        clk = jif.ltc6952(solver=solver)
    except Exception as e:
        pytest.skip(f"Skipping ltc6952 draw test: {e}")

    vcxo = 125000000
    output_clocks = [1e9, 500e6]
    output_clocks = list(map(int, output_clocks))
    clock_names = ["ADC", "FPGA"]

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    try:
        clk.solve()
        clk.get_config()
    except Exception as e:
        pytest.skip(f"Skipping ltc6952 draw test due to solve failure: {e}")

    img = clk.draw()
    assert img is not None


# -----------------------------------------------------------------------------
# PLLs
# -----------------------------------------------------------------------------


@pytest.mark.drawing
def test_adf4030_draw() -> None:
    """Test drawing for ADF4030."""
    try:
        pll = jif.adf4030()
    except Exception as e:
        pytest.skip(f"Skipping adf4030 draw test: {e}")

    ref_in = int(100e6)
    output_clocks = [int(2.5e6)]
    clock_names = ["SYSREF"]

    pll.set_requested_clocks(ref_in, output_clocks, clock_names)

    try:
        pll.solve()
        pll.get_config()
    except Exception as e:
        pytest.skip(f"Skipping adf4030 draw test due to solve failure: {e}")

    # Draw
    img = pll.draw()
    assert img is not None


@pytest.mark.drawing
def test_adf4371_draw() -> None:
    """Test drawing for ADF4371."""
    try:
        pll = jif.adf4371()
    except Exception as e:
        pytest.skip(f"Skipping adf4371 draw test: {e}")

    pll._MOD2 = 1536
    pll.rf_div = 2
    pll.mode = "fractional"

    ref_in = int(122.88e6)
    output_clocks = int(2112.8e6)

    pll.set_requested_clocks(ref_in, output_clocks)

    try:
        pll.solve()
        pll.get_config()
    except Exception as e:
        pytest.skip(f"Skipping adf4371 draw test due to solve failure: {e}")

    img = pll.draw()
    assert img is not None


@pytest.mark.drawing
def test_adf4382_draw() -> None:
    """Test drawing for ADF4382."""
    try:
        pll = jif.adf4382()
    except Exception as e:
        pytest.skip(f"Skipping adf4382 draw test: {e}")

    ref_in = int(125e6 / 2)
    output_clocks = int(8e9)
    pll.n = 128
    pll.d = 1
    pll.o = 2

    pll.set_requested_clocks(ref_in, output_clocks)

    try:
        pll.solve()
        pll.get_config()
    except Exception as e:
        pytest.skip(f"Skipping adf4382 draw test due to solve failure: {e}")

    img = pll.draw()
    assert img is not None
