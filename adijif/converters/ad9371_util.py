"""AD9371 profile parsing helpers."""

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


def _number(value: str) -> int | float | str:
    value = value.strip()
    try:
        number = float(value) if "." in value else int(value)
    except ValueError:
        return value
    return int(number) if isinstance(number, float) and number.is_integer() else number


def _parse_scalars(body: str) -> dict[str, int | float | str]:
    values: dict[str, int | float | str] = {}
    for raw_line in body.splitlines():
        match = _SCALAR_RE.match(raw_line.strip())
        if match:
            key, value = match.groups()
            values[key] = _number(value)
    return values


def parse_ad9371_profile(profile_path: str | Path) -> dict[str, Any]:
    """Parse an AD9371 profile exported by the ADI profile wizard.

    The profile format is XML-like rather than valid XML because scalar fields
    are encoded as ``<name=value>``.  This parser intentionally extracts the
    clock and datapath scalars needed by the JIF model while tolerating filter
    coefficient blocks used by the Linux driver.

    Args:
        profile_path: Path to an AD9371 text profile.

    Returns:
        Parsed profile metadata and ``clocks``, ``rx``, ``obs``, and ``tx``
        scalar dictionaries.

    Raises:
        FileNotFoundError: If ``profile_path`` does not exist.
        ValueError: If the file is not an AD9371 profile or lacks a required
            section.
    """
    path = Path(profile_path)
    if not path.is_file():
        raise FileNotFoundError(f"Profile file not found: {path}")
    content = path.read_text(encoding="utf-8")
    header = _PROFILE_RE.search(content)
    if not header or header.group("device").upper() != "AD9371":
        raise ValueError(f"Not an AD9371 profile: {path}")

    sections = {
        match.group("name").lower(): _parse_scalars(match.group("body"))
        for match in _SECTION_RE.finditer(content)
    }
    missing = [name for name in ("clocks", "rx", "obs", "tx") if not sections.get(name)]
    if missing:
        raise ValueError(
            f"AD9371 profile {path} is missing required section(s): {', '.join(missing)}"
        )

    return {
        "profile": {
            "device": header.group("device"),
            "version": _number(header.group("version")),
            "name": header.group("name").strip(),
        },
        **sections,
    }
