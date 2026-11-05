"""Streamlit-free output-path enumeration for the Frequency Planner.

A path is one signal route through the datapath: an Rx output channel
with its feeding ADC/CDDC, or a Tx (signal, DAC) pair with its FDUC/CDUC.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adijif.freqplan import (
    RxPlan,
    RxResult,
    TxPlan,
    TxResult,
    evaluate_dac,
    evaluate_output,
)


@dataclass(frozen=True)
class Path:
    """One selectable datapath route.

    Attributes:
        id: Unique path id.
        stages: Block ids in signal order.
        output: Id of the final output block.
        signals: Names of the signals carried.
        label: Display label without status glyph.
    """

    id: str
    stages: tuple[str, ...]
    output: str
    signals: tuple[str, ...]
    label: str


def _index(name: str) -> int:
    """Return the trailing integer of a stage name.

    Args:
        name: Stage name such as ``"cddc3"``.

    Returns:
        The index.
    """
    return int(name.lstrip("abcdefghijklmnopqrstuvwxyz"))


def rx_paths(plan: RxPlan, result: RxResult) -> list[Path]:
    """Enumerate Rx output paths.

    Args:
        plan: The Rx plan.
        result: Computed Rx result.

    Returns:
        One path per output stage, in result order.
    """
    paths: list[Path] = []
    for name, stage in result.stages.items():
        if not stage.is_output:
            continue
        if stage.kind == "fddc":
            cddc = _index(stage.parent) if stage.parent else 0
            adc = plan.adc_to_cddc[cddc]
            stages = (f"adc{adc}", f"cddc{cddc}", name)
        else:
            stages = (stage.parent or "", name)
        targets = plan.targets.get(name)
        if targets:
            sigs = tuple(targets)
        else:
            sigs = tuple(
                sorted({sp.signal for sp in stage.spans if not sp.image})
            )
        label = f"{', '.join(sigs) or '(empty)'} · {name.upper()}"
        paths.append(Path(name, stages, name, sigs, label))
    return paths


def tx_paths(plan: TxPlan, result: TxResult) -> list[Path]:
    """Enumerate Tx (signal, DAC) paths.

    Args:
        plan: The Tx plan.
        result: Computed Tx result.

    Returns:
        Paths ordered by signal, then DAC index.
    """
    dp = plan.datapath
    paths: list[Path] = []
    for sig in plan.signals:
        i = sig.source
        if not 0 <= i < len(dp.fduc_enabled) or not dp.fduc_enabled[i]:
            continue
        c = dp.fduc_source[i] - 1
        if not 0 <= c < len(dp.cduc_enabled) or not dp.cduc_enabled[c]:
            continue
        for j, srcs in enumerate(dp.cduc_sources):
            if c + 1 not in srcs or f"dac{j}" not in result.stages:
                continue
            paths.append(
                Path(
                    f"{sig.name}@dac{j}",
                    (f"fduc{i}", f"cduc{c}", f"dac{j}"),
                    f"dac{j}",
                    (sig.name,),
                    f"{sig.name} · FDUC{i} → DAC{j}",
                )
            )
    return paths


def path_status(path: Path, plan: Any, result: Any) -> str:
    """Return the verdict status of a path's output.

    Args:
        path: The path.
        plan: The Rx or Tx plan.
        result: The matching result.

    Returns:
        ``"ok"``, ``"warn"`` or ``"error"``.
    """
    stage = result.stages[path.output]
    sigs = {s.name: s for s in plan.signals}
    if stage.kind == "dac":
        return evaluate_dac(stage, sigs).status
    targets = plan.targets.get(path.output, [])
    return evaluate_output(stage, sigs, targets).status


def select_path_for_block(
    paths: list[Path], current: str | None, block: str
) -> str | None:
    """Pick the path a block click selects.

    Args:
        paths: Available paths.
        current: Currently selected path id.
        block: Clicked block id.

    Returns:
        ``current`` if it contains the block, else the first path that
        does, else ``current``.
    """
    for p in paths:
        if p.id == current and block in p.stages:
            return current
    for p in paths:
        if block in p.stages:
            return p.id
    return current


def resolve_path_id(paths: list[Path], saved: str | None) -> str:
    """Validate a saved path selection.

    Args:
        paths: Available paths.
        saved: Previously saved selection.

    Returns:
        ``saved`` if valid or ``"all"``, else the first path id, or
        ``"all"`` when there are no paths.
    """
    if saved == "all" or any(p.id == saved for p in paths):
        return str(saved)
    return paths[0].id if paths else "all"
