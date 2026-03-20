"""Tests for the brute-force Xilinx PLL calculation methods."""

import pytest

from adijif.fpgas.xilinx.bf import xilinx_bf


class MockXilinxBF(xilinx_bf):
    """Subclass to provide required attributes for brute-force methods."""

    vco_min = 1.6e9
    vco_max = 3.3e9
    ref_clock_min = 60e6
    ref_clock_max = 670e6
    vco0_min = 6.5e9
    vco0_max = 9.3e9
    vco1_min = 9.3e9
    vco1_max = 13.1e9
    N = [16, 20, 32, 40, 64, 66, 80, 100]
    transciever_type = "GTX2"


def test_determine_cpll_should_find_valid_config():
    """Verify CPLL configuration discovery for valid inputs."""
    # Arrange
    bf = MockXilinxBF()
    bit_clock = 10e9
    fpga_ref_clock = 125e6

    # Act
    # bit_clock = (VCO * 2) / D  => VCO = bit_clock * D / 2
    # If D=8, VCO = 10e9 * 8 / 2 = 40 GHz (too high)
    # If D=4, VCO = 10e9 * 4 / 2 = 20 GHz (too high)
    # The code loop:
    # vco = fpga_ref_clock * n1 * n2 / m
    # if fpga_ref_clock / m / d == bit_clock / (2 * n1 * n2)
    
    # Try simple case: bit_clock=2.5e9, ref=125e6
    # 125e6 * 5 * 4 / 1 = 2.5 GHz (in range 1.6-3.3)
    # n1 is outer loop [5, 4], n2 is inner loop [5, 4, 3, 2, 1]
    # Match for n1=5, n2=4 will be found first.
    
    res = bf.determine_cpll(2500000000, 125000000)

    # Assert
    assert res["type"] == "CPLL"
    assert res["m"] == 1
    assert res["d"] == 2
    assert res["n1"] == 5
    assert res["n2"] == 4


def test_determine_cpll_should_raise_on_invalid_inputs():
    """Verify CPLL discovery fails when no valid configuration exists."""
    # Arrange
    bf = MockXilinxBF()

    # Act & Assert
    with pytest.raises(Exception, match="No valid CPLL configuration found"):
        bf.determine_cpll(int(100e9), int(125e6))


def test_determine_qpll_should_find_valid_config():
    """Verify QPLL configuration discovery for valid inputs."""
    # Arrange
    bf = MockXilinxBF()
    # vco = fpga_ref * n / m
    # band 0: 6.5 - 9.3 GHz
    # 125e6 * 64 / 1 = 8.0 GHz (Band 0)
    # Match condition: fpga_ref / m / d == bit_clock / n
    # 125e6 / 1 / 1 == bit_clock / 64 => bit_clock = 8.0 GHz
    
    res = bf.determine_qpll(8000000000, 125000000)

    # Assert
    assert res["type"] == "QPLL"
    assert res["band"] == 0
    assert res["n"] == 64
    assert res["m"] == 1
    assert res["d"] == 1


def test_determine_qpll_should_raise_on_out_of_range_ref_clock():
    """Verify QPLL discovery fails when reference clock is out of range."""
    # Arrange
    bf = MockXilinxBF()

    # Act & Assert
    with pytest.raises(Exception, match="fpga_ref_clock not within range"):
        bf.determine_qpll(8e9, 10e6)


def test_determine_qpll_gty4_full_rate():
    """Verify QPLL discovery for GTY4 transceivers."""
    # Arrange
    bf = MockXilinxBF()
    bf.transciever_type = "GTY4"
    # Match condition 2: fpga_ref / m / d == bit_clock / 2 / n
    # 125e6 / 1 / 1 == bit_clock / 2 / 64 => bit_clock = 16.0 GHz
    
    res = bf.determine_qpll(16000000000, 125000000)

    # Assert
    assert res["type"] == "QPLL"
    assert res["qty4_full_rate"] == 1
