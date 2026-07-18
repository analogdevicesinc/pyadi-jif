"""Versioned pyadi-jif producer model for the pyadi-dt handoff."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

CONTRACT_NAME = "adi.jif-dt"
CONTRACT_VERSION = "1.0"


def _semantic_id(value: str) -> str:
    """Normalize a component or clock name into a stable contract ID segment."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _integer_hz(value: Any, field_name: str) -> int:
    """Convert an integral solver rate to integer hertz without truncation."""
    converted = int(value)
    if converted <= 0 or float(value) != converted:
        raise ValueError(f"{field_name} must be a positive integral Hz value")
    return converted


@dataclass(frozen=True)
class Producer:
    """Identity of the package that generated a contract."""

    version: str
    name: Literal["pyadi-jif"] = "pyadi-jif"

    def __post_init__(self) -> None:
        """Validate producer identity and version provenance."""
        if self.name != "pyadi-jif" or not self.version:
            raise ValueError("producer must identify a pyadi-jif version")


@dataclass(frozen=True)
class JesdParameters:
    """JESD transport parameters shared by converter and FPGA endpoints."""

    F: int
    K: int
    L: int
    M: int
    N: int
    Np: int
    S: int
    HD: int
    CS: int = 0
    CF: int = 0

    def __post_init__(self) -> None:
        """Validate positive integer framing values and transport identity."""
        values = (self.F, self.K, self.L, self.M, self.N, self.Np, self.S)
        if any(type(value) is not int or value <= 0 for value in values):
            raise ValueError("JESD parameters must be positive integers")
        if self.HD not in (0, 1):
            raise ValueError("HD must be 0 or 1")
        if self.M * self.S * self.Np != 8 * self.L * self.F:
            raise ValueError("M*S*Np must equal 8*L*F")


@dataclass(frozen=True)
class JesdLink:
    """One solved unidirectional JESD link."""

    id: str
    direction: Literal["adc-to-fpga", "fpga-to-dac"]
    converter: str
    fpga: str
    standard: Literal["jesd204b", "jesd204c"]
    sample_rate_hz: int
    lane_rate_hz: int
    parameters: JesdParameters
    fpga_config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the solved lane rate against framing and encoding."""
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", self.id):
            raise ValueError(f"invalid JESD link ID: {self.id}")
        if type(self.sample_rate_hz) is not int or self.sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be a positive integer")
        if type(self.lane_rate_hz) is not int or self.lane_rate_hz <= 0:
            raise ValueError("lane_rate_hz must be a positive integer")
        ratio = (10, 8) if self.standard == "jesd204b" else (66, 64)
        p = self.parameters
        expected_num = self.sample_rate_hz * p.M * p.Np * ratio[0]
        expected_den = p.L * ratio[1]
        if abs(self.lane_rate_hz * expected_den - expected_num) > expected_den:
            raise ValueError(
                "lane_rate_hz is inconsistent with JESD parameters"
            )


@dataclass(frozen=True)
class ClockRequirement:
    """A solved semantic clock requirement, independent of output placement."""

    id: str
    role: Literal[
        "converter-device",
        "converter-sysref",
        "fpga-ref",
        "fpga-link",
        "pll-ref",
        "other",
    ]
    sink: str
    rate_hz: int
    source: str
    divider: int | None = None

    def __post_init__(self) -> None:
        """Validate semantic identity and solved integer values."""
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", self.id):
            raise ValueError(f"invalid clock requirement ID: {self.id}")
        if type(self.rate_hz) is not int or self.rate_hz <= 0:
            raise ValueError("rate_hz must be a positive integer")
        if self.divider is not None and (
            type(self.divider) is not int or self.divider <= 0
        ):
            raise ValueError("divider must be a positive integer")


@dataclass(frozen=True)
class JifDtContract:
    """Portable solved electrical intent for a pyadi-dt consumer."""

    producer: Producer
    jesd_links: tuple[JesdLink, ...]
    clock_requirements: tuple[ClockRequirement, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    schema: Literal["adi.jif-dt"] = CONTRACT_NAME
    version: Literal["1.0"] = CONTRACT_VERSION

    def __post_init__(self) -> None:
        """Reject duplicate IDs and values that cannot cross a JSON boundary."""
        if self.schema != CONTRACT_NAME or self.version != CONTRACT_VERSION:
            raise ValueError(
                f"unsupported contract identity: {self.schema} {self.version}"
            )
        for kind, entries in (
            ("JESD link", self.jesd_links),
            ("clock requirement", self.clock_requirements),
        ):
            ids = [entry.id for entry in entries]
            duplicates = sorted({item for item in ids if ids.count(item) > 1})
            if duplicates:
                raise ValueError(f"duplicate {kind} IDs: {duplicates}")
        # Reject backend objects hidden in extension dictionaries.
        json.dumps(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible snapshot."""
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize the contract deterministically."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"

    def to_json_file(self, path: str | Path) -> None:
        """Write deterministic interchange JSON to *path*."""
        Path(path).write_text(self.to_json())

    @classmethod
    def from_system_solution(
        cls, system: Any, solution: dict[str, Any]
    ) -> "JifDtContract":
        """Project a solved single-converter system into the 1.0 contract.

        Physical clock output channels and device-tree labels are intentionally
        absent. A pyadi-dt board profile binds these semantic requirements later.
        """
        converter = system.converter
        if isinstance(converter, list) or getattr(converter, "_nested", None):
            raise ValueError(
                "from_system_solution currently supports one non-nested converter"
            )

        name = converter.name
        jesd = solution[f"jesd_{name}"]
        fpga_config = solution[f"fpga_{name}"]
        converter_type = converter.converter_type.lower()
        if converter_type == "adc":
            direction = "adc-to-fpga"
            direction_id = "rx"
        elif converter_type == "dac":
            direction = "fpga-to-dac"
            direction_id = "tx"
        else:
            raise ValueError(f"unsupported converter type: {converter_type}")

        parameters = JesdParameters(
            F=int(jesd["F"]),
            K=int(jesd["K"]),
            L=int(jesd["L"]),
            M=int(jesd["M"]),
            N=int(converter.N),
            Np=int(jesd["Np"]),
            S=int(jesd["S"]),
            HD=int(jesd["HD"]),
            CS=int(jesd.get("CS", 0)),
            CF=int(jesd.get("CF", 0)),
        )
        link = JesdLink(
            id=f"{_semantic_id(name)}.{direction_id}",
            direction=direction,
            converter=name,
            fpga=system.fpga.name,
            standard=jesd["jesd_class"].lower(),
            sample_rate_hz=_integer_hz(jesd["sample_clock"], "sample_rate_hz"),
            lane_rate_hz=_integer_hz(jesd["bit_clock"], "lane_rate_hz"),
            parameters=parameters,
            fpga_config=deepcopy(fpga_config),
        )

        clocks = tuple(
            _clock_requirement(
                clock_name, clock, name, system.fpga.name, system.clock.name
            )
            for clock_name, clock in solution["clock"]["output_clocks"].items()
        )
        import adijif

        return cls(
            producer=Producer(version=adijif.__version__),
            jesd_links=(link,),
            clock_requirements=clocks,
            metadata={"solver": system.solver},
        )


def _clock_requirement(
    clock_name: str,
    config: dict[str, Any],
    converter_name: str,
    fpga_name: str,
    source_name: str,
) -> ClockRequirement:
    """Translate one semantic requested clock from a solved clock configuration."""
    lower = clock_name.lower()
    converter_id = _semantic_id(converter_name)
    if lower.endswith("_sysref"):
        role = "converter-sysref"
        sink = converter_name
        requirement_id = f"{converter_id}.sysref"
    elif lower.startswith(fpga_name.lower()) and lower.endswith("_ref_clk"):
        role = "fpga-ref"
        sink = fpga_name
        requirement_id = f"{converter_id}.fpga-ref"
    elif lower.startswith(fpga_name.lower()) and lower.endswith("_device_clk"):
        role = "fpga-link"
        sink = fpga_name
        requirement_id = f"{converter_id}.fpga-link"
    elif lower.endswith("_ref_clk"):
        role = "converter-device"
        sink = converter_name
        requirement_id = f"{converter_id}.device-clock"
    else:
        role = "other"
        sink = clock_name
        requirement_id = _semantic_id(clock_name)

    divider = config.get("divider")
    return ClockRequirement(
        id=requirement_id,
        role=role,
        sink=sink,
        rate_hz=_integer_hz(config["rate"], f"{clock_name}.rate_hz"),
        source=source_name,
        divider=int(divider) if divider is not None else None,
    )
