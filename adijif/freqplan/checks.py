"""Per-output capture and interference verdicts for frequency planning."""

from __future__ import annotations

from dataclasses import dataclass, field

from .rx import Signal, StageOutput
from .spectrum import TOL_HZ, Span

CAPTURE_OK = 0.999


@dataclass
class SignalCapture:
    """How much of a signal is captured at an output.

    Attributes:
        signal: Signal name.
        captured_hz: Captured width in Hz.
        bandwidth_hz: Signal bandwidth in Hz.
        fraction: Captured fraction of the bandwidth.
    """

    signal: str
    captured_hz: float
    bandwidth_hz: float
    fraction: float


@dataclass
class Interference:
    """Unwanted energy in the usable band.

    Attributes:
        signal: Originating signal name.
        image: True if the piece is an image/alias.
        attenuated: True if the piece lies in a transition band.
        overlap_hz: In-band width in Hz.
    """

    signal: str
    image: bool
    attenuated: bool
    overlap_hz: float


@dataclass
class Verdict:
    """Quick ok/warn/error verdict for one output.

    Attributes:
        channel: Stage name.
        status: One of ``"ok"``, ``"warn"``, ``"error"``.
        captures: Per-target capture results.
        interference: Interfering pieces.
        used_fraction: Fraction of the output bandwidth used by targets.
        can_decimate_more: True if the output rate could be reduced.
        messages: Human-readable lines.
    """

    channel: str
    status: str
    captures: list[SignalCapture] = field(default_factory=list)
    interference: list[Interference] = field(default_factory=list)
    used_fraction: float = 0.0
    can_decimate_more: bool = False
    messages: list[str] = field(default_factory=list)


def _mhz(hz: float) -> str:
    """Format Hz as MHz without decimals when integral."""
    v = hz / 1e6
    if abs(v - round(v)) < 1e-6:
        return f"{round(v):d}"
    return f"{v:.3f}".rstrip("0").rstrip(".")


def _clip(sp: Span, lo: float, hi: float) -> tuple[float, float] | None:
    """Intersect a span with [lo, hi]; None if outside."""
    if sp.hi - sp.lo < TOL_HZ and sp.hi == sp.lo:
        if lo - TOL_HZ <= sp.lo <= hi + TOL_HZ:
            return (sp.lo, sp.lo)
        return None
    a, b = max(sp.lo, lo), min(sp.hi, hi)
    if b - a < TOL_HZ:
        return None
    return (a, b)


def _union_width(ivs: list[tuple[float, float]]) -> float:
    """Total width of the union of intervals."""
    total = 0.0
    cur_lo: float | None = None
    cur_hi = 0.0
    for a, b in sorted(ivs):
        if cur_lo is None:
            cur_lo, cur_hi = a, b
        elif a <= cur_hi:
            cur_hi = max(cur_hi, b)
        else:
            total += cur_hi - cur_lo
            cur_lo, cur_hi = a, b
    if cur_lo is not None:
        total += cur_hi - cur_lo
    return total


def _capture(
    name: str, bw: float, ivs: list[tuple[float, float]]
) -> SignalCapture:
    """Build a SignalCapture from clean in-band intervals."""
    width = _union_width(ivs)
    if bw <= 0:
        return SignalCapture(name, 0.0, bw, 1.0 if ivs else 0.0)
    return SignalCapture(name, width, bw, min(width / bw, 1.0))


def _capture_msg(c: SignalCapture) -> str:
    """Message line for a capture."""
    if c.bandwidth_hz <= 0:
        return f"{c.signal}: tone {'captured' if c.fraction else 'missed'}"
    return (
        f"{c.signal}: {_mhz(c.captured_hz)} of "
        f"{_mhz(c.bandwidth_hz)} MHz captured"
    )


def evaluate_output(
    stage: StageOutput, signals: dict[str, Signal], targets: list[str]
) -> Verdict:
    """Evaluate an output stage against its target signals.

    Args:
        stage: The stage output.
        signals: Signals by name.
        targets: Target signal names; empty means all signals present.

    Returns:
        The verdict.
    """
    if stage.error:
        return Verdict(stage.channel, "error", messages=[stage.error])

    p = stage.passband_hz
    clipped: list[tuple[Span, tuple[float, float]]] = []
    for sp in stage.spans:
        iv = _clip(sp, -p, p)
        if iv is not None:
            clipped.append((sp, iv))

    tgts = list(targets)
    if not tgts:
        for sp, _ in clipped:
            if not sp.image and sp.signal not in tgts:
                tgts.append(sp.signal)

    captures: list[SignalCapture] = []
    used: list[tuple[float, float]] = []
    for name in tgts:
        ivs = [
            iv
            for sp, iv in clipped
            if sp.signal == name and not sp.image and not sp.attenuated
        ]
        bw = signals[name].bandwidth_hz if name in signals else 0.0
        captures.append(_capture(name, bw, ivs))
        used.extend(ivs)

    interference = [
        Interference(sp.signal, sp.image, sp.attenuated, iv[1] - iv[0])
        for sp, iv in clipped
        if sp.image or sp.signal not in tgts
    ]

    used_fraction = _union_width(used) / (2 * p) if p > 0 else 0.0
    can_more = used_fraction <= 0.5

    if any(not i.attenuated for i in interference):
        status = "error"
    elif interference or any(c.fraction < CAPTURE_OK for c in captures):
        status = "warn"
    else:
        status = "ok"

    msgs = [_capture_msg(c) for c in captures]
    for i in interference:
        kind = "image" if i.image else "in band"
        att = " (attenuated)" if i.attenuated else ""
        if i.image:
            msgs.append(
                f"{i.signal} image in band ({_mhz(i.overlap_hz)} MHz){att}"
            )
        else:
            msgs.append(f"{i.signal} {kind} ({_mhz(i.overlap_hz)} MHz){att}")
    msgs.append(f"{round(used_fraction * 100):d}% of output BW used")
    if can_more:
        msgs.append("could decimate further")
    return Verdict(
        stage.channel,
        status,
        captures,
        interference,
        used_fraction,
        can_more,
        msgs,
    )


def evaluate_dac(stage: StageOutput, signals: dict[str, Signal]) -> Verdict:
    """Evaluate a DAC stage for collisions within [0, fs/2].

    The DAC output is real, so a signal's mirrored (image) pieces carry
    its energy at ``|f|`` and count toward its capture. Overlaps between
    different signals, or between a signal and its own mirror, are
    collisions. Pieces above fs/2 (the second Nyquist zone) are ignored.

    Args:
        stage: The DAC stage output.
        signals: Signals by name.

    Returns:
        The verdict.
    """
    if stage.error:
        return Verdict(stage.channel, "error", messages=[stage.error])

    half = stage.rate_hz / 2
    pieces: list[tuple[Span, tuple[float, float]]] = []
    for sp in stage.spans:
        iv = _clip(sp, 0.0, half)
        if iv is not None:
            pieces.append((sp, iv))

    names: list[str] = []
    for sp in stage.spans:
        if sp.signal not in names:
            names.append(sp.signal)

    captures: list[SignalCapture] = []
    used: list[tuple[float, float]] = []
    for name in names:
        ivs = [
            iv
            for sp, iv in pieces
            if sp.signal == name and not sp.attenuated
        ]
        bw = signals[name].bandwidth_hz if name in signals else 0.0
        captures.append(_capture(name, bw, ivs))
        used.extend(ivs)

    interference: list[Interference] = []
    hard = False
    msgs: list[str] = []
    for i, (a, (alo, ahi)) in enumerate(pieces):
        for b, (blo, bhi) in pieces[i + 1 :]:
            if a.signal == b.signal and a.image == b.image:
                continue
            ov = min(ahi, bhi) - max(alo, blo)
            if ov <= 0:
                continue
            att = a.attenuated or b.attenuated
            hard = hard or not att
            interference.append(Interference(b.signal, b.image, att, ov))
            msgs.append(
                f"{a.signal} and {b.signal} overlap ({_mhz(ov)} MHz)"
                + (" (attenuated)" if att else "")
            )

    if hard:
        status = "error"
    elif interference or any(c.fraction < CAPTURE_OK for c in captures):
        status = "warn"
    else:
        status = "ok"

    msgs = [_capture_msg(c) for c in captures] + msgs
    used_fraction = _union_width(used) / half if half > 0 else 0.0
    return Verdict(
        stage.channel,
        status,
        captures,
        interference,
        used_fraction,
        False,
        msgs,
    )
