"""AD9371 profile parsing and JESD-mode helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_PROFILE_RE = re.compile(
    r"<profile\s+(?P<device>\S+)\s+version=(?P<version>\S+)\s+name=(?P<name>.*?)>",
    re.IGNORECASE,
)
_SECTION_RE = re.compile(
    r"<(?P<name>clocks|rx|obs|tx)\b[^>]*>(?P<body>.*?)</(?P=name)>",
    re.DOTALL | re.IGNORECASE,
)
_SCALAR_RE = re.compile(r"^<([A-Za-z0-9_]+)\s*=\s*([^>]+)>$")

_REQUIRED = {
    "clocks": {
        "deviceClock_kHz",
        "clkPllVcoFreq_kHz",
        "clkPllVcoDiv",
        "clkPllHsDiv",
    },
    "rx": {
        "adcDiv",
        "rxFirDecimation",
        "rxDec5Decimation",
        "enHighRejDec5",
        "rhb1Decimation",
        "iqRate_kHz",
    },
    "obs": {
        "adcDiv",
        "rxFirDecimation",
        "rxDec5Decimation",
        "enHighRejDec5",
        "rhb1Decimation",
        "iqRate_kHz",
    },
    "tx": {
        "dacDiv",
        "txFirInterpolation",
        "thb1Interpolation",
        "thb2Interpolation",
        "txInputHbInterpolation",
        "iqRate_kHz",
    },
}


def _number(value: str) -> int | float | str:
    value = value.strip()
    try:
        number = float(value) if "." in value else int(value)
    except ValueError:
        return value
    return int(number) if isinstance(number, float) and number.is_integer() else number


def _parse_scalars(body: str, section: str) -> dict[str, int | float | str]:
    values: dict[str, int | float | str] = {}
    for raw_line in body.splitlines():
        match = _SCALAR_RE.match(raw_line.strip())
        if not match:
            continue
        key, value = match.groups()
        if key in values:
            raise ValueError(f"AD9371 profile has duplicate {section}.{key}")
        values[key] = _number(value)
    return values


def ad9371_jesd_mode(*, M: int, L: int) -> dict[str, int]:
    """Build one valid Mykonos JESD204B mode."""
    if M not in (2, 4) or L not in (1, 2, 4) or (2 * M) % L:
        raise ValueError(f"Unsupported AD9371 JESD mode M={M}, L={L}")
    return {
        "L": L,
        "M": M,
        "F": 2 * M // L,
        "S": 1,
        "HD": 0,
        "Np": 16,
        "N": 14,
        "CS": 2,
        "CF": 0,
        "K": 32,
    }


AD9371_RX_MODES = {
    "8": ad9371_jesd_mode(M=2, L=1),
    "10": ad9371_jesd_mode(M=2, L=2),
    "13": ad9371_jesd_mode(M=2, L=4),
    "16": ad9371_jesd_mode(M=4, L=2),  # Standard primary-RX default.
    "17": ad9371_jesd_mode(M=4, L=1),
    "19": ad9371_jesd_mode(M=4, L=4),
}
AD9371_OBS_MODES = {
    **AD9371_RX_MODES,
    "16": ad9371_jesd_mode(M=2, L=2),  # Standard observation-RX default.
}
AD9371_TX_MODES = {
    "2": ad9371_jesd_mode(M=2, L=1),
    "3": ad9371_jesd_mode(M=2, L=2),
    "4": ad9371_jesd_mode(M=2, L=4),
    "5": ad9371_jesd_mode(M=4, L=1),
    "6": ad9371_jesd_mode(M=4, L=4),  # Standard TX default.
    "7": ad9371_jesd_mode(M=4, L=2),
}


def parse_ad9371_profile(profile_path: str | Path) -> dict[str, Any]:
    """Parse and strictly validate an AD9371 profile-wizard text file."""
    path = Path(profile_path)
    if not path.is_file():
        raise FileNotFoundError(f"Profile file not found: {path}")
    content = path.read_text(encoding="utf-8")
    header = _PROFILE_RE.search(content)
    if not header or header.group("device").upper() != "AD9371":
        raise ValueError(f"Not an AD9371 profile: {path}")
    version = _number(header.group("version"))
    if version != 0:
        raise ValueError(f"Unsupported AD9371 profile version: {version}")

    sections: dict[str, dict[str, int | float | str]] = {}
    for match in _SECTION_RE.finditer(content):
        name = match.group("name").lower()
        if name in sections:
            raise ValueError(f"AD9371 profile has duplicate {name} section")
        sections[name] = _parse_scalars(match.group("body"), name)

    missing_sections = [name for name in _REQUIRED if name not in sections]
    if missing_sections:
        raise ValueError(
            f"AD9371 profile {path} is missing required section(s): "
            f"{', '.join(missing_sections)}"
        )
    for name, required in _REQUIRED.items():
        missing = sorted(required - set(sections[name]))
        if missing:
            raise ValueError(
                f"AD9371 profile {path} is missing required {name} field(s): "
                f"{', '.join(missing)}"
            )

    return {
        "profile": {
            "device": header.group("device"),
            "version": version,
            "name": header.group("name").strip(),
        },
        **sections,
    }
