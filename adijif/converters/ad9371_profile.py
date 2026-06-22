"""AD9371 (Mykonos) TES profile parser.

Parses the text-format profile files distributed with iio-oscilloscope under
``filters/ad9371_5/profile_*.txt`` and applies the relevant clocking and
sample-rate settings to an AD9371 converter model.

The TES profile format is a custom XML-like text:

    <profile AD9371 version=0 name=Rx 100, IQrate 122.880>
     <clocks>
      <deviceClock_kHz=122880>
      ...
     </clocks>
     <rx>
      <iqRate_kHz=122880>
      <rxFirDecimation=2>
      <rxDec5Decimation=5>
      <rhb1Decimation=1>
      ...
     </rx>
     <obs> ... </obs>
     <tx>
      <iqRate_kHz=122880>
      <txFirInterpolation=1>
      <thb1Interpolation=2>
      <thb2Interpolation=2>
      <txInputHbInterpolation=1>
      ...
     </tx>
    </profile>

Filter coefficient and ADC profile blocks (``<filter ...>``, ``<adc-profile>``,
``<lpbk-adc-profile>``) carry no clocking information and are skipped.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Union

from adijif.converters.converter import converter

_SECTION_NAMES = ("clocks", "rx", "obs", "tx")
_NESTED_BLOCK_RE = re.compile(
    r"<(filter|[\w-]+-profile)\b[^>]*>.*?</\1>", re.DOTALL
)
_KV_RE = re.compile(r"<(\w+)=([^>]+)>")
_HEADER_RE = re.compile(
    r"<profile\s+(?P<part>\S+)\s+version=(?P<version>\d+)"
    r"(?:\s+name=(?P<name>[^>]+))?>"
)


def _coerce(value: str) -> Union[int, float, str]:
    """Convert a string token to int, float, or leave as str."""
    value = value.strip()
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def parse_profile(profile: str) -> Dict[str, Any]:
    """Parse an AD9371 TES profile.

    Args:
        profile: Path to a ``.txt`` profile file or the profile text itself.

    Returns:
        Dictionary with keys ``part``, ``version``, ``name`` (header metadata)
        and one entry per section (``clocks``, ``rx``, ``obs``, ``tx``) mapping
        to a dict of ``{field: value}`` pairs. Numeric fields are coerced to
        ``int`` or ``float``; everything else is left as ``str``.

    Raises:
        ValueError: If the profile header is missing or names a non-AD9371 part.
    """
    if os.path.exists(profile):
        with open(profile) as f:
            text = f.read()
    else:
        text = profile

    header = _HEADER_RE.search(text)
    if header is None:
        raise ValueError("Profile is missing a <profile ...> header")
    part = header.group("part")
    if part != "AD9371":
        raise ValueError(
            f"Profile part '{part}' is not AD9371 — refusing to parse"
        )

    result: Dict[str, Any] = {
        "part": part,
        "version": int(header.group("version")),
        "name": (header.group("name") or "").strip(),
    }

    for section in _SECTION_NAMES:
        section_re = re.compile(
            rf"<{section}>(.*?)</{section}>", re.DOTALL
        )
        match = section_re.search(text)
        if match is None:
            continue
        body = _NESTED_BLOCK_RE.sub("", match.group(1))
        result[section] = {
            key: _coerce(value) for key, value in _KV_RE.findall(body)
        }

    return result


def _rx_decimation(rx: Dict[str, Any]) -> int:
    return (
        int(rx["rxFirDecimation"])
        * int(rx["rxDec5Decimation"])
        * int(rx["rhb1Decimation"])
    )


def _tx_interpolation(tx: Dict[str, Any]) -> int:
    return (
        int(tx["txFirInterpolation"])
        * int(tx["thb1Interpolation"])
        * int(tx["thb2Interpolation"])
        * int(tx.get("txInputHbInterpolation", 1))
    )


def _apply_rx_settings(conv: converter, profile: Dict[str, Any]) -> None:
    rx = profile["rx"]
    conv.sample_clock = int(rx["iqRate_kHz"]) * 1000
    conv.decimation = _rx_decimation(rx)


def _apply_tx_settings(conv: converter, profile: Dict[str, Any]) -> None:
    tx = profile["tx"]
    conv.sample_clock = int(tx["iqRate_kHz"]) * 1000
    conv.interpolation = _tx_interpolation(tx)


def apply_settings(conv: converter, profile: Dict[str, Any]) -> None:
    """Apply parsed profile settings to an AD9371 converter model.

    Sets ``sample_clock`` and the appropriate decimation/interpolation on the
    target converter. JESD link parameters (M/L/F/Np) are not part of the TES
    profile and must be selected separately via ``set_quick_configuration_mode``
    or by setting M, L, Np, S directly.

    Args:
        conv: ``ad9371_rx``, ``ad9371_tx``, or combined ``ad9371`` instance.
        profile: Parsed profile dict from :func:`parse_profile`.

    Raises:
        ValueError: If ``conv`` is not a recognized AD9371 converter type.
    """
    ctype = getattr(conv, "converter_type", None)
    if ctype == "adc":
        _apply_rx_settings(conv, profile)
    elif ctype == "dac":
        _apply_tx_settings(conv, profile)
    elif ctype == "adc_dac":
        _apply_rx_settings(conv.adc, profile)
        _apply_tx_settings(conv.dac, profile)
    else:
        raise ValueError(
            f"Cannot apply AD9371 profile to converter_type={ctype!r}"
        )
