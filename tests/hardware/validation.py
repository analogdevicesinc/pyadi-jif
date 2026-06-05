"""Helpers to validate pyadi-jif converter models against measured HW facts.

The core idea: a booted board reports its JESD *lane rate* and *sample rate*.
A faithful pyadi-jif model must contain a quick-configuration mode that, at the
measured sample rate, reproduces the measured lane rate. This validates the
model's JESD lane-rate math against reality without needing to read the raw
L/M/F/S parameters from the kernel (which are not exposed uniformly).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class MatchedMode:
    """A converter quick-configuration mode that matches measured hardware."""

    mode: str
    jesd_class: str
    L: int
    M: int
    Np: int
    bit_clock: float


def find_matching_mode(
    conv,
    sample_clock: float,
    lane_rate_hz: float,
    rel_tol: float = 1e-6,
) -> Optional[MatchedMode]:
    """Find a quick-config mode reproducing ``lane_rate_hz`` at ``sample_clock``.

    Args:
        conv: A pyadi-jif converter instance (e.g. ``adijif.ad9680()``).
        sample_clock: Measured sample rate in hertz.
        lane_rate_hz: Measured JESD lane rate in hertz.
        rel_tol: Relative tolerance for the lane-rate comparison.

    Returns:
        The first matching :class:`MatchedMode`, or ``None`` if no mode matches.
    """
    conv.sample_clock = sample_clock
    modes = conv.quick_configuration_modes
    for jesd_class, table in modes.items():
        for mode in table:
            try:
                conv.set_quick_configuration_mode(mode, jesd_class)
                conv.sample_clock = sample_clock
                bc = conv.bit_clock
            except Exception:  # noqa: BLE001 - skip modes invalid for this rate
                continue
            if bc <= 0:
                continue
            if abs(bc - lane_rate_hz) <= rel_tol * lane_rate_hz:
                return MatchedMode(
                    mode=mode,
                    jesd_class=jesd_class,
                    L=int(conv.L),
                    M=int(conv.M),
                    Np=int(conv.Np),
                    bit_clock=bc,
                )
    return None


def match_link(
    conv_factory,
    lane_rate_hz: float,
    sample_rates: List[float],
    rel_tol: float = 1e-6,
) -> Optional[Tuple[float, MatchedMode]]:
    """Find a (sample_rate, mode) the model reproduces for a measured lane rate.

    Tries each candidate sample rate (e.g. every IIO ``sampling_frequency`` the
    board reports) against a fresh converter so a failed mode set on one rate
    does not leak into the next.

    Args:
        conv_factory: Zero-arg callable returning a fresh converter instance.
        lane_rate_hz: Measured JESD lane rate in hertz.
        sample_rates: Candidate sample rates in hertz.
        rel_tol: Relative tolerance for the lane-rate comparison.

    Returns:
        ``(sample_rate, MatchedMode)`` for the first match, else ``None``.
    """
    for sr in sample_rates:
        if sr <= 0:
            continue
        match = find_matching_mode(conv_factory(), sr, lane_rate_hz, rel_tol)
        if match is not None:
            return sr, match
    return None


def available_lane_rates(conv, sample_clock: float) -> List[Tuple[str, float]]:
    """List ``(mode, bit_clock)`` pairs for all modes at ``sample_clock``.

    Useful for diagnostics when :func:`find_matching_mode` returns ``None``.
    """
    out: List[Tuple[str, float]] = []
    modes = conv.quick_configuration_modes
    for jesd_class, table in modes.items():
        for mode in table:
            try:
                conv.set_quick_configuration_mode(mode, jesd_class)
                conv.sample_clock = sample_clock
                out.append((f"{jesd_class}/{mode}", conv.bit_clock))
            except Exception:  # noqa: BLE001
                continue
    return out
