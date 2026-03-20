"""Common VCXO references for common converter and clock-chip evaluation boards."""

from typing import Any, Dict, List, Optional

EVAL_BOARD_VCXO_REFERENCES = [
    {
        "board": "AD-FMCDAQ2-EBZ",
        "converter": ["ad9680"],
        "clock_chip": "ad9523_1",
        "vcxo_hz": 125_000_000,
        "notes": "Used by DAQ2 ADC-side example flow.",
    },
    {
        "board": "DAQ2-HMC7044",
        "converter": ["ad9680"],
        "clock_chip": "hmc7044",
        "vcxo_hz": 125_000_000,
        "notes": "DAQ2 example using HMC7044 clock chip variant.",
    },
    {
        "board": "AD9081/AD9082 EVAL HMC7044",
        "converter": [
            "ad9081",
            "ad9081_rx",
            "ad9081_tx",
            "ad9082",
            "ad9082_rx",
            "ad9082_tx",
        ],
        "clock_chip": "hmc7044",
        "vcxo_hz": 100_000_000,
        "notes": "Common across AD9081/AD9082 example setups.",
    },
    {
        "board": "AD9084-FMCA-EBZ",
        "converter": ["ad9084_rx", "ad9088_rx"],
        "clock_chip": "hmc7044",
        "vcxo_hz": 125_000_000,
        "notes": "AD9084/RX variants on HMC7044 eval-board flows.",
    },
    {
        "board": "ADSY1100",
        "converter": ["ad9084_rx"],
        "clock_chip": "ltc6952",
        "vcxo_hz": 125_000_000,
        "notes": "Used in ADSY1100 RX flow.",
    },
    {
        "board": "Triton (Quad-Apollo)",
        "converter": ["ad9084_rx"],
        "clock_chip": "ltc6952",
        "vcxo_hz": 400_000_000,
        "notes": "Observed in Triton reference profile examples.",
    },
    {
        "board": "ADRV9009 PCBZ",
        "converter": ["adrv9009", "adrv9009_rx", "adrv9009_tx"],
        "clock_chip": "ad9528",
        "vcxo_hz": 122_880_000,
        "notes": "Used in ADRV9009 example configuration.",
    },
]


def _normalize_name(name: str) -> str:
    """Normalize component names for matching."""
    return name.strip().lower()


def get_common_vcxo_references(
    converter: Optional[str] = None,
    clock_chip: Optional[str] = None,
    board: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return matching VCXO reference entries from known evaluation board presets.

    Args:
        converter: Optional converter name (e.g. ``"ad9084_rx"``).
        clock_chip: Optional clock chip name (e.g. ``"ltc6952"``).
        board: Optional board/platform name (e.g. ``"Triton (Quad-Apollo)"``).

    Returns:
        List of matching reference dictionaries.
    """
    out: List[Dict[str, Any]] = []
    converter_l = _normalize_name(converter) if converter else None
    clock_chip_l = _normalize_name(clock_chip) if clock_chip else None
    board_l = _normalize_name(board) if board else None

    for entry in EVAL_BOARD_VCXO_REFERENCES:
        if converter_l and converter_l not in [
            _normalize_name(x) for x in entry["converter"]
        ]:
            continue
        if clock_chip_l and _normalize_name(entry["clock_chip"]) != clock_chip_l:
            continue
        if board_l and _normalize_name(entry["board"]) != board_l:
            continue
        out.append(dict(entry))

    return out


def get_default_vcxo_hz(
    converter: str, clock_chip: str, board: Optional[str] = None
) -> Optional[int]:
    """Return the first matching VCXO value from common board presets.

    Args:
        converter: Converter name to match.
        clock_chip: Clock chip name to match.
        board: Optional board name to narrow the match.

    Returns:
        VCXO frequency in Hz or ``None`` if no match exists.
    """
    refs = get_common_vcxo_references(
        converter=converter, clock_chip=clock_chip, board=board
    )
    if not refs:
        return None
    return refs[0]["vcxo_hz"]
