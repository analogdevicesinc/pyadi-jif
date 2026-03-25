"""Common VCXO references for eval boards."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EvalBoardInfo:
    """Known eval board / module reference configuration.

    Attributes:
        board: Human-readable board or module name.
        converters: Physical converter part(s) on the
            board (all present simultaneously).
        compatible_parts: All pyadi-jif component names
            that match this board for lookup purposes.
            Includes RX/TX sub-designations and
            pin-compatible variants (e.g. AD9082 on an
            AD9081 eval board).
        clock_chip: Clock chip model.
        vcxo_hz: VCXO frequency in Hz.
        pll: External PLL between clock chip and
            converter, if present.
        notes: Optional description.
    """

    board: str
    converters: tuple[str, ...]
    compatible_parts: tuple[str, ...]
    clock_chip: str
    vcxo_hz: int
    pll: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict (JSON-serializable)."""
        d = asdict(self)
        d["converters"] = list(d["converters"])
        d["compatible_parts"] = list(d["compatible_parts"])
        return d


EVAL_BOARD_VCXO_REFERENCES: List[EvalBoardInfo] = [
    EvalBoardInfo(
        board="AD-FMCDAQ2-EBZ",
        converters=("ad9680", "ad9144"),
        compatible_parts=("ad9680", "ad9144"),
        clock_chip="ad9523_1",
        vcxo_hz=125_000_000,
        notes=("DAQ2 eval board with" " AD9680 ADC and AD9144 DAC."),
    ),
    EvalBoardInfo(
        board="DAQ2-HMC7044",
        converters=("ad9680", "ad9144"),
        compatible_parts=("ad9680", "ad9144"),
        clock_chip="hmc7044",
        vcxo_hz=125_000_000,
        notes=("DAQ2 example using" " HMC7044 clock chip variant."),
    ),
    EvalBoardInfo(
        board="AD9081/AD9082 EVAL HMC7044",
        converters=("ad9081",),
        compatible_parts=(
            "ad9081",
            "ad9081_rx",
            "ad9081_tx",
            "ad9082",
            "ad9082_rx",
            "ad9082_tx",
        ),
        clock_chip="hmc7044",
        vcxo_hz=100_000_000,
        notes=("Pin-compatible with" " AD9081 and AD9082 variants."),
    ),
    EvalBoardInfo(
        board="AD9084-FMCA-EBZ",
        converters=("ad9084",),
        compatible_parts=(
            "ad9084_rx",
            "ad9088_rx",
        ),
        clock_chip="hmc7044",
        vcxo_hz=125_000_000,
        pll="adf4382",
        notes=("Pin-compatible with" " AD9084 and AD9088 variants."),
    ),
    EvalBoardInfo(
        board="ADSY1100",
        converters=("ad9084",),
        compatible_parts=("ad9084_rx",),
        clock_chip="ltc6952",
        vcxo_hz=125_000_000,
        pll="adf4382",
        notes="Used in ADSY1100 RX flow.",
    ),
    EvalBoardInfo(
        board="Triton (Quad-Apollo)",
        converters=("ad9084",),
        compatible_parts=("ad9084_rx",),
        clock_chip="ltc6952",
        vcxo_hz=400_000_000,
        pll="adf4382",
        notes=("Observed in Triton" " reference profile examples."),
    ),
    EvalBoardInfo(
        board="ADRV9009 PCBZ",
        converters=("adrv9009",),
        compatible_parts=(
            "adrv9009",
            "adrv9009_rx",
            "adrv9009_tx",
        ),
        clock_chip="ad9528",
        vcxo_hz=122_880_000,
        notes=("Used in ADRV9009" " example configuration."),
    ),
]


def _normalize_name(name: str) -> str:
    """Normalize component names for matching."""
    return name.strip().lower()


def get_common_vcxo_references(
    converter: Optional[str] = None,
    clock_chip: Optional[str] = None,
    board: Optional[str] = None,
    pll: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return matching VCXO reference entries.

    Filters known evaluation board presets by any
    combination of converter, clock chip, board, or PLL.

    Args:
        converter: Optional converter name
            (e.g. ``"ad9084_rx"``).  Matched against
            each entry's ``compatible_parts``.
        clock_chip: Optional clock chip name
            (e.g. ``"ltc6952"``).
        board: Optional board/platform name
            (e.g. ``"Triton (Quad-Apollo)"``).
        pll: Optional PLL name
            (e.g. ``"adf4382"``).

    Returns:
        List of matching reference dictionaries.
    """
    out: List[Dict[str, Any]] = []
    conv_l = _normalize_name(converter) if converter else None
    clk_l = _normalize_name(clock_chip) if clock_chip else None
    board_l = _normalize_name(board) if board else None
    pll_l = _normalize_name(pll) if pll else None

    for entry in EVAL_BOARD_VCXO_REFERENCES:
        if conv_l and conv_l not in [
            _normalize_name(x) for x in entry.compatible_parts
        ]:
            continue
        if clk_l:
            if _normalize_name(entry.clock_chip) != clk_l:
                continue
        if board_l:
            if _normalize_name(entry.board) != board_l:
                continue
        if pll_l:
            if entry.pll is None or _normalize_name(entry.pll) != pll_l:
                continue
        out.append(entry.to_dict())

    return out


def get_default_vcxo_hz(
    converter: str,
    clock_chip: str,
    board: Optional[str] = None,
) -> Optional[int]:
    """Return the first matching VCXO value.

    Args:
        converter: Converter name to match
            (checked against ``compatible_parts``).
        clock_chip: Clock chip name to match.
        board: Optional board name to narrow
            the match.

    Returns:
        VCXO frequency in Hz or ``None`` if
        no match exists.
    """
    refs = get_common_vcxo_references(
        converter=converter,
        clock_chip=clock_chip,
        board=board,
    )
    if not refs:
        return None
    return refs[0]["vcxo_hz"]
