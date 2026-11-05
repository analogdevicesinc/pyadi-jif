"""Tests for frequency-plan spectrum primitives."""

from adijif.freqplan.spectrum import (
    Span,
    ddc_stage,
    duc_stage,
    spans_mhz,
    wrap_frequency,
    wrap_spans,
)


def test_wrap_frequency() -> None:
    """Wrap into [-fs/2, fs/2)."""
    assert wrap_frequency(7e9, 10e9) == -3e9
    assert wrap_frequency(5e9, 10e9) == -5e9


def test_wrap_splits_span() -> None:
    """A span crossing the edge is split."""
    out = wrap_spans([Span(4e9, 6e9, "S")], 10e9)
    assert spans_mhz(out) == [
        (-5000, -4000, "S", False, False),
        (4000, 5000, "S", False, False),
    ]


def test_ddc_passband() -> None:
    """In-band span passes untouched after NCO shift."""
    out = ddc_stage([Span(1.0e9, 1.4e9, "S1")], 20e9, 1.2e9, 4, 0.8)
    assert spans_mhz(out) == [(-200, 200, "S1", False, False)]


def test_ddc_transition_folds_to_guard() -> None:
    """Transition band is attenuated and folds at the output rate."""
    out = ddc_stage([Span(2.2e9, 2.6e9, "S")], 20e9, 0, 4, 0.8)
    assert spans_mhz(out) == [
        (-2500, -2400, "S", False, True),
        (2200, 2500, "S", False, True),
    ]


def test_ddc_rejects_stopband() -> None:
    """Stopband content is removed."""
    assert ddc_stage([Span(3.5e9, 4.0e9, "S")], 20e9, 0, 4, 0.8) == []


def test_ddc_dec1_no_filter() -> None:
    """Decimation 1 applies no filter."""
    span = Span(3.5e9, 4.0e9, "S")
    assert ddc_stage([span], 20e9, 0, 1, 0.8) == [span]


def test_duc_rejects_images() -> None:
    """Images outside the stopband edge are rejected."""
    out = duc_stage([Span(-0.1e9, 0.1e9, "S")], 1e9, 2, 0, 0.8)
    assert spans_mhz(out) == [(-100, 100, "S", False, False)]


def test_duc_transition_and_image() -> None:
    """Transition band and its image are attenuated."""
    out = duc_stage([Span(0.35e9, 0.45e9, "S")], 1e9, 2, 0, 0.8)
    assert spans_mhz(out) == [
        (-600, -550, "S", False, True),
        (350, 400, "S", False, False),
        (400, 450, "S", False, True),
    ]


def test_duc_nco_shift() -> None:
    """NCO shifts the interpolated span."""
    out = duc_stage([Span(-0.2e9, 0.2e9, "S")], 2.5e9, 2, 0.5e9, 0.8)
    assert spans_mhz(out) == [(300, 700, "S", False, False)]
