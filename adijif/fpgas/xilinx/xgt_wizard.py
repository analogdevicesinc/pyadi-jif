"""Export solved configs to the ADI HDL repo xgt_wizard (adi_xcvr) flow.

The HDL repo's ``adi_xcvr_project`` proc consumes a flat parameter list
(``LANE_RATE``/``REF_CLK``/``PLL_TYPE``/``JESD_MODE`` plus ``XCVR_RX_*``
overrides). This module maps a solved pyadi-jif system onto that contract
and renders it as a make command, a sourceable tcl snippet, or JSON.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple


def _fmt(value: float) -> str:
    """Format a rate for the HDL parameter list (e.g. ``10``, ``245.76``).

    Rounds to 6 decimals to absorb solver float noise, then strips
    trailing zeros and any dangling decimal point.

    Args:
        value: Rate in Gbps or MHz.

    Returns:
        Compact decimal string.
    """
    return f"{round(value, 6):.6f}".rstrip("0").rstrip(".")

_PLL_TYPES = ("CPLL", "QPLL0", "QPLL1")
_PLL_NAME_MAP = {"cpll": "CPLL", "qpll": "QPLL0", "qpll1": "QPLL1"}
_JESD_MODE_MAP = {"jesd204b": "8B10B", "jesd204c": "64B66B"}


@dataclass(frozen=True)
class XgtWizardLink:
    """Solved transceiver settings for one JESD link direction."""

    lane_rate_gbps: float
    ref_clk_mhz: float
    pll_type: str
    num_lanes: int

    def __post_init__(self) -> None:
        """Validate rates, PLL naming, and lane count.

        Raises:
            ValueError: If a rate is not positive, ``pll_type`` is not one
                of CPLL/QPLL0/QPLL1, or ``num_lanes`` is not >= 1.
        """
        if self.lane_rate_gbps <= 0 or self.ref_clk_mhz <= 0:
            raise ValueError("lane_rate_gbps and ref_clk_mhz must be positive")
        if self.pll_type not in _PLL_TYPES:
            raise ValueError(
                f"pll_type must be one of {_PLL_TYPES}, got {self.pll_type}"
            )
        if type(self.num_lanes) is not int or self.num_lanes < 1:
            raise ValueError("num_lanes must be a positive integer")


@dataclass(frozen=True)
class XgtWizardConfig:
    """Parameters for the HDL repo ``adi_xcvr_project`` xgt_wizard flow."""

    jesd_mode: str
    tx: Optional[XgtWizardLink]
    rx: Optional[XgtWizardLink]
    transceiver_type: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate the JESD mode and require at least one direction.

        Raises:
            ValueError: If ``jesd_mode`` is not ``8B10B``/``64B66B`` or
                both ``tx`` and ``rx`` are ``None``.
        """
        if self.jesd_mode not in _JESD_MODE_MAP.values():
            raise ValueError(
                "jesd_mode must be '8B10B' or '64B66B', got "
                f"{self.jesd_mode}"
            )
        if self.tx is None and self.rx is None:
            raise ValueError("at least one of tx or rx must be set")

    def to_dict(self) -> Dict[str, Any]:
        """Return a detached JSON-compatible snapshot.

        Returns:
            Nested plain dictionary of all fields.
        """
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize the config deterministically.

        Args:
            indent: JSON indentation width.

        Returns:
            JSON document with sorted keys and a trailing newline.
        """
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"

    def _project_params(self) -> List[Tuple[str, str]]:
        """Build the ordered ``adi_xcvr_project`` parameter pairs.

        The primary direction is TX when both directions exist, otherwise
        whichever exists. ``XCVR_RX_*`` overrides are emitted individually
        and only where the RX value differs from the primary.

        Returns:
            Ordered list of ``(key, value)`` string pairs.
        """
        primary = self.tx if self.tx is not None else self.rx
        params = [
            ("LANE_RATE", _fmt(primary.lane_rate_gbps)),
            ("REF_CLK", _fmt(primary.ref_clk_mhz)),
            ("PLL_TYPE", primary.pll_type),
            ("JESD_MODE", self.jesd_mode),
        ]
        if self.tx is not None and self.rx is not None:
            overrides = (
                ("XCVR_RX_LANE_RATE", "lane_rate_gbps", _fmt),
                ("XCVR_RX_REF_CLK", "ref_clk_mhz", _fmt),
                ("XCVR_RX_PLL_TYPE", "pll_type", str),
            )
            for key, attr, render in overrides:
                rx_value = getattr(self.rx, attr)
                if rx_value != getattr(self.tx, attr):
                    params.append((key, render(rx_value)))
        return params

    def to_make_args(self) -> str:
        """Render the make-level ``KEY=value`` parameter overrides.

        Returns:
            Space-separated ``KEY=value`` string for an HDL project make.
        """
        return " ".join(f"{k}={v}" for k, v in self._project_params())

    def to_make_command(self, project: str) -> str:
        """Render a full make invocation for an HDL project.

        Args:
            project: HDL project path relative to ``projects/``, e.g.
                ``"ad9081_fmca_ebz/zcu102"``.

        Returns:
            Complete ``make -C projects/<project> ...`` command line.
        """
        return f"make -C projects/{project} {self.to_make_args()}"

    def to_tcl(self) -> str:
        """Render a sourceable tcl snippet with the wizard parameters.

        Defines ``adi_xcvr_project_args`` for ``adi_xcvr_project`` in
        ``system_project.tcl`` and ``adi_xcvr_parameters_args`` (lane
        counts) for ``adi_xcvr_parameters`` in the block design tcl.

        Returns:
            Tcl source text.
        """
        import adijif

        lane_counts = []
        if self.rx is not None:
            lane_counts.append(("RX_NUM_OF_LANES", str(self.rx.num_lanes)))
        if self.tx is not None:
            lane_counts.append(("TX_NUM_OF_LANES", str(self.tx.num_lanes)))

        lines = [f"# Generated by pyadi-jif {adijif.__version__}"]
        for var, pairs in (
            ("adi_xcvr_project_args", self._project_params()),
            ("adi_xcvr_parameters_args", lane_counts),
        ):
            lines.append(f"set {var} [list \\")
            lines.extend(f"  {k} {v} \\" for k, v in pairs)
            lines.append("]")
        return "\n".join(lines) + "\n"

    @classmethod
    def from_system_solution(
        cls, system: Any, solution: Dict[str, Any]
    ) -> "XgtWizardConfig":
        """Map a solved single-converter system onto the xgt_wizard contract.

        Args:
            system: Solved :class:`adijif.system.system` instance. The FPGA
                must have been configured via ``setup_by_dev_kit_name`` so
                ``fpga.name`` matches the solution clock names.
            solution: Result of :meth:`adijif.system.system.solve`.

        Returns:
            Frozen :class:`XgtWizardConfig` snapshot.

        Raises:
            ValueError: If the system has multiple converters, uses a PLL
                the xgt_wizard flow does not support (Versal RPLL/LCPLL),
                mixes JESD classes across directions, or a required ref
                clock cannot be found in the solution.
        """
        converter = system.converter
        if isinstance(converter, list):
            raise ValueError(
                "xgt_wizard export supports a single converter system"
            )

        nested = getattr(converter, "_nested", None)
        if nested:
            links = [(name, getattr(converter, name)) for name in nested]
        else:
            links = [(converter.name, converter)]

        tx: Optional[XgtWizardLink] = None
        rx: Optional[XgtWizardLink] = None
        jesd_mode: Optional[str] = None
        for name, child in links:
            if f"fpga_{name}" not in solution:
                continue
            link, mode, direction = _extract_link(
                system, solution, name, child
            )
            if jesd_mode is None:
                jesd_mode = mode
            elif jesd_mode != mode:
                raise ValueError(
                    "jesd_class differs between directions; xgt_wizard "
                    "supports a single JESD_MODE"
                )
            if direction == "tx":
                tx = link
            else:
                rx = link

        if jesd_mode is None:
            raise ValueError("solution contains no fpga_* link sections")
        return cls(
            jesd_mode=jesd_mode,
            tx=tx,
            rx=rx,
            transceiver_type=getattr(system.fpga, "transceiver_type", None),
        )


def _extract_link(
    system: Any, solution: Dict[str, Any], name: str, child: Any
) -> Tuple[XgtWizardLink, str, str]:
    """Build one direction's link parameters from the solution.

    Args:
        system: Solved system instance.
        solution: Full solve result.
        name: Link name used in ``fpga_{name}``/``jesd_{name}`` keys.
        child: Converter object for this link (for ``converter_type``).

    Returns:
        Tuple of the link, the JESD mode string, and ``"tx"`` or ``"rx"``.

    Raises:
        ValueError: On unsupported PLL types, unknown ``jesd_class`` or
            converter type, or a missing FPGA ref clock.
    """
    fpga_cfg = solution[f"fpga_{name}"]
    jesd = solution[f"jesd_{name}"]

    pll = _PLL_NAME_MAP.get(fpga_cfg["type"])
    if pll is None:
        raise ValueError(
            f"xgt_wizard flow does not support PLL type "
            f"'{fpga_cfg['type']}' (Versal is unsupported)"
        )

    jesd_class = jesd["jesd_class"].lower()
    mode = _JESD_MODE_MAP.get(jesd_class)
    if mode is None:
        raise ValueError(f"unknown jesd_class: {jesd_class}")

    converter_type = child.converter_type.lower()
    if converter_type == "adc":
        direction = "rx"
    elif converter_type == "dac":
        direction = "tx"
    else:
        raise ValueError(f"unsupported converter type: {converter_type}")

    link = XgtWizardLink(
        lane_rate_gbps=jesd["bit_clock"] / 1e9,
        ref_clk_mhz=_find_ref_clk(system, solution, name) / 1e6,
        pll_type=pll,
        num_lanes=int(jesd["L"]),
    )
    return link, mode, direction


def _find_ref_clk(
    system: Any, solution: Dict[str, Any], name: str
) -> float:
    """Locate the FPGA reference clock rate for one link.

    Args:
        system: Solved system instance (``fpga.name`` prefixes the clock).
        solution: Full solve result.
        name: Link name (``{fpga.name}_{name}_ref_clk`` is expected).

    Returns:
        Reference clock rate in Hz.

    Raises:
        ValueError: If no matching output clock exists. Ensure the FPGA was
            configured with ``setup_by_dev_kit_name`` so its name matches.
    """
    clocks = solution["clock"]["output_clocks"]
    fpga_name = getattr(system.fpga, "name", "")
    key = f"{fpga_name}_{name}_ref_clk"
    if key in clocks:
        return clocks[key]["rate"]
    suffix = f"_{name}_ref_clk"
    matches = [k for k in clocks if k.endswith(suffix)]
    if len(matches) == 1:
        return clocks[matches[0]]["rate"]
    raise ValueError(
        f"could not find FPGA ref clock '{key}' in output_clocks "
        f"(available: {sorted(clocks)}); was the FPGA configured with "
        "setup_by_dev_kit_name?"
    )
