"""Spectrum span primitives and ideal DDC/DUC stages for frequency planning."""

from __future__ import annotations

from dataclasses import dataclass, replace

TOL_HZ = 1e-3


@dataclass(frozen=True)
class Span:
    """A band of spectrum occupied by a signal.

    Attributes:
        lo: Lower edge in Hz.
        hi: Upper edge in Hz (``lo == hi`` is a CW tone).
        signal: Name of the originating signal.
        image: True if this span is an image/alias.
        attenuated: True if the span lies in a filter transition band.
    """

    lo: float
    hi: float
    signal: str
    image: bool = False
    attenuated: bool = False


def wrap_frequency(f: float, fs: float) -> float:
    """Wrap a frequency into [-fs/2, fs/2).

    Args:
        f: Frequency in Hz.
        fs: Sample rate in Hz.

    Returns:
        The wrapped frequency in Hz.
    """
    return (f + fs / 2) % fs - fs / 2


def wrap_spans(spans: list[Span], fs: float) -> list[Span]:
    """Move spans into [-fs/2, fs/2), splitting at the edge if needed.

    Assumes each span is narrower than ``fs``.

    Args:
        spans: Spans in Hz.
        fs: Sample rate in Hz.

    Returns:
        Wrapped spans.
    """
    half = fs / 2
    out: list[Span] = []
    for sp in spans:
        width = sp.hi - sp.lo
        lo = wrap_frequency(sp.lo, fs)
        hi = lo + width
        if hi <= half + TOL_HZ:
            out.append(replace(sp, lo=lo, hi=min(hi, half)))
            continue
        out.append(replace(sp, lo=lo, hi=half))
        rest = hi - fs
        if rest - (-half) >= TOL_HZ:
            out.append(replace(sp, lo=-half, hi=rest))
    return out


def shift_spans(spans: list[Span], df: float) -> list[Span]:
    """Shift spans by ``df`` Hz without wrapping.

    Args:
        spans: Spans in Hz.
        df: Frequency offset in Hz.

    Returns:
        Shifted spans.
    """
    return [replace(sp, lo=sp.lo + df, hi=sp.hi + df) for sp in spans]


def _filter_spans(spans: list[Span], p: float, s: float) -> list[Span]:
    """Apply an ideal filter: clip to |f| < s, mark |f| > p attenuated."""
    out: list[Span] = []
    for sp in spans:
        cw = sp.hi - sp.lo < TOL_HZ and sp.hi == sp.lo
        lo = max(sp.lo, -s)
        hi = min(sp.hi, s)
        if cw:
            if -s < sp.lo < s:
                att = sp.attenuated or abs(sp.lo) > p
                out.append(replace(sp, attenuated=att))
            continue
        edges = [lo, *[e for e in (-p, p) if lo < e < hi], hi]
        for a, b in zip(edges[:-1], edges[1:], strict=True):
            if b - a < TOL_HZ:
                continue
            att = sp.attenuated or abs((a + b) / 2) > p
            out.append(replace(sp, lo=a, hi=b, attenuated=att))
    return out


def ddc_stage(
    spans: list[Span],
    fs_in: float,
    nco_hz: float,
    decimation: int,
    alpha: float,
) -> list[Span]:
    """Model an ideal brick-wall DDC (NCO shift then decimating filter).

    Args:
        spans: Input spans in Hz, within the ``fs_in`` Nyquist zone.
        fs_in: Input sample rate in Hz.
        nco_hz: NCO frequency in Hz (spans shift by minus this value).
        decimation: Decimation ratio; 1 applies no filter.
        alpha: Passband fraction of the output Nyquist band.

    Returns:
        Spans at the output rate.
    """
    out = wrap_spans(shift_spans(spans, -nco_hz), fs_in)
    if decimation == 1:
        return out
    fs_out = fs_in / decimation
    p = alpha * fs_out / 2
    s = fs_out - p
    return wrap_spans(_filter_spans(out, p, s), fs_out)


def duc_stage(
    spans: list[Span],
    fs_in: float,
    interpolation: int,
    nco_hz: float,
    alpha: float,
) -> list[Span]:
    """Model an ideal brick-wall DUC (interpolating filter then NCO shift).

    Args:
        spans: Input spans in Hz, within the ``fs_in`` Nyquist zone.
        fs_in: Input sample rate in Hz.
        interpolation: Interpolation ratio; 1 applies no filter.
        nco_hz: NCO frequency in Hz (spans shift by plus this value).
        alpha: Passband fraction of the input Nyquist band.

    Returns:
        Spans at the output rate ``fs_in * interpolation``.
    """
    if interpolation == 1:
        return wrap_spans(shift_spans(spans, nco_hz), fs_in)
    fs_out = fs_in * interpolation
    p = alpha * fs_in / 2
    s = fs_in - p
    kept: list[Span] = []
    for k in range(-interpolation, interpolation + 1):
        kept.extend(_filter_spans(shift_spans(spans, k * fs_in), p, s))
    return wrap_spans(shift_spans(kept, nco_hz), fs_out)


def spans_mhz(
    spans: list[Span],
) -> list[tuple[float, float, str, bool, bool]]:
    """Return sorted, rounded ``(lo_MHz, hi_MHz, signal, image, att)`` tuples.

    Args:
        spans: Spans in Hz.

    Returns:
        Sorted tuples with edges in MHz rounded to 3 decimals.
    """
    rows = [
        (
            round(sp.lo / 1e6, 3) + 0.0,
            round(sp.hi / 1e6, 3) + 0.0,
            sp.signal,
            sp.image,
            sp.attenuated,
        )
        for sp in spans
    ]
    return sorted(rows)
