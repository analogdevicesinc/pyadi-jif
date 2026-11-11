"""Tests for ADC Nyquist helpers."""

import pytest

from adijif.freqplan.adc import (
    adc_spectrum,
    fold_to_first_nyquist,
    nyquist_zone,
    rf_to_nco,
    straddles_nyquist,
)
from adijif.freqplan.spectrum import spans_mhz


def test_zone_and_fold():
    assert nyquist_zone(7.8e9, 20e9) == 1
    assert nyquist_zone(12e9, 20e9) == 2
    assert fold_to_first_nyquist(12e9, 20e9) == 8e9
    assert rf_to_nco(12e9, 20e9) == (8e9, 2)
    with pytest.raises(ValueError):
        rf_to_nco(-1, 20e9)


def test_adc_first_zone():
    got = spans_mhz(adc_spectrum([("S1", 1.2e9, 0.4e9)], 20e9))
    assert got == [
        (-1400, -1000, "S1", True, False),
        (1000, 1400, "S1", False, False),
    ]


def test_adc_even_zone():
    got = spans_mhz(adc_spectrum([("S", 12e9, 0.4e9)], 20e9))
    assert got == [
        (-8200, -7800, "S", True, False),
        (7800, 8200, "S", False, False),
    ]


def test_straddle_detected():
    assert straddles_nyquist(10e9, 0.4e9, 20e9) is True
    assert straddles_nyquist(1.2e9, 0.4e9, 20e9) is False
    assert straddles_nyquist(1.0e9, 0.4e9, 20e9) is False
