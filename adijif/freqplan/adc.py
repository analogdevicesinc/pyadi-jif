"""ADC sampling and Nyquist-zone helpers for frequency planning."""

from __future__ import annotations

from .spectrum import TOL_HZ, Span, wrap_spans


def nyquist_zone(f_hz: float, fs: float) -> int:
    """Return the 1-based Nyquist zone containing a frequency.

    Args:
        f_hz: Frequency in Hz.
        fs: Sample rate in Hz.

    Returns:
        The Nyquist zone number (1 is DC to fs/2).
    """
    return int(f_hz // (fs / 2)) + 1


def fold_to_first_nyquist(f_hz: float, fs: float) -> float:
    """Fold a frequency into the first Nyquist zone.

    Args:
        f_hz: Frequency in Hz.
        fs: Sample rate in Hz.

    Returns:
        The aliased frequency in [0, fs/2] Hz.
    """
    half = fs / 2
    k = int(f_hz // half)
    if k % 2 == 0:
        return f_hz - k * half
    return (k + 1) * half - f_hz


def rf_to_nco(f_rf_hz: float, fs: float) -> tuple[float, int]:
    """Convert an RF frequency to a folded NCO frequency and zone.

    Args:
        f_rf_hz: RF frequency in Hz.
        fs: ADC sample rate in Hz.

    Returns:
        Tuple of (folded NCO frequency in Hz, Nyquist zone).

    Raises:
        ValueError: If ``f_rf_hz`` is negative.
    """
    if f_rf_hz < 0:
        raise ValueError(f"RF frequency must be >= 0, got {f_rf_hz}")
    return fold_to_first_nyquist(f_rf_hz, fs), nyquist_zone(f_rf_hz, fs)


def adc_spectrum(
    bands: list[tuple[str, float, float]], fs: float
) -> list[Span]:
    """Build the complex ADC output spectrum in [-fs/2, fs/2).

    Each band contributes its positive band and its negative-frequency
    mirror; pieces at or below 0 Hz are flagged as images.

    Args:
        bands: ``(name, center_hz, bw_hz)`` tuples.
        fs: ADC sample rate in Hz.

    Returns:
        Wrapped spans.
    """
    spans: list[Span] = []
    for name, center, bw in bands:
        for c in (center, -center):
            wrapped = wrap_spans([Span(c - bw / 2, c + bw / 2, name)], fs)
            spans.extend(
                Span(sp.lo, sp.hi, sp.signal, image=sp.hi <= 0)
                for sp in wrapped
            )
    return spans


def straddles_nyquist(center_hz: float, bw_hz: float, fs: float) -> bool:
    """Check whether a band crosses a Nyquist zone boundary.

    A band edge exactly on a boundary is not considered straddling.

    Args:
        center_hz: Band center in Hz.
        bw_hz: Band width in Hz.
        fs: ADC sample rate in Hz.

    Returns:
        True if the band edges lie in different Nyquist zones.
    """
    lo = center_hz - bw_hz / 2
    hi = center_hz + bw_hz / 2
    return nyquist_zone(lo + TOL_HZ, fs) != nyquist_zone(hi - TOL_HZ, fs)
