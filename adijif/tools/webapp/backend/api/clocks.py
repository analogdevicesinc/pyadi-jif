"""Clock API endpoints for clock configuration."""

import io
import logging
from typing import Any

import adijif
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from adijif.clocks import supported_parts as sp

logger = logging.getLogger(__name__)

router = APIRouter()

# Parse parts and options to skip
options_to_skip = ["list_references_available", "d_syspulse"]
parts_to_ignore = ["ad9545", "ad9523_1"]
supported_clocks = [p for p in sp if p not in parts_to_ignore]
# Put HMC7044 at the front
supported_clocks = [p for p in supported_clocks if p != "hmc7044"]
supported_clocks.insert(0, "hmc7044")


class ClockConfig(BaseModel):
    """Clock configuration model."""

    part: str
    reference_clock: float
    output_clocks: list[float]
    output_names: list[str]
    selections: dict[str, Any] = {}


@router.get("/supported")
async def get_supported_clocks() -> list[str]:
    """Get list of supported clock parts."""
    return supported_clocks


@router.get("/{part}/configurable-properties")
async def get_configurable_properties(part: str) -> dict[str, Any]:
    """Get configurable properties for a clock part."""
    try:
        class_def = eval(f"adijif.{part}")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Clock part {part} not found") from e

    props = dir(class_def)
    props = [p for p in props if not p.startswith("__")]
    props = [p for p in props if not p.startswith("_")]
    configurable_props = [p.replace("_available", "") for p in props if "_available" in p]

    prop_and_options = {}
    for prop in configurable_props:
        if prop in options_to_skip or prop + "_available" not in props:
            continue
        available_options = getattr(class_def, prop + "_available")
        prop_docstring = getattr(class_def, prop).__doc__

        prop_and_options[prop] = {
            "options": available_options,
            "description": prop_docstring,
        }

    return prop_and_options


@router.post("/{part}/solve")
async def solve_clock_config(part: str, config: ClockConfig) -> dict[str, Any]:
    """Solve clock configuration and return the solution."""
    try:
        clk_chip = eval(f"adijif.{part}()")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Clock part {part} not found") from e

    # Apply selections
    for prop, values in config.selections.items():
        if isinstance(values, dict):
            props_available = getattr(clk_chip, prop + "_available")
            if (
                min(props_available) == values.get("start")
                and max(props_available) == values.get("end")
            ):
                continue
            picked = [
                v
                for v in props_available
                if values.get("start", 0) <= v <= values.get("end", float("inf"))
            ]
            setattr(clk_chip, prop, picked)
        else:
            if not values:
                continue
            setattr(clk_chip, prop, values)

    # Set requested clocks
    output_clocks = list(map(int, config.output_clocks))
    clk_chip.set_requested_clocks(config.reference_clock, output_clocks, config.output_names)

    try:
        clk_chip.solve()
        solution = clk_chip.get_config()
        return {"success": True, "config": solution}
    except Exception as e:
        logger.warning(f"Failed to solve clock configuration: {e}")
        return {"success": False, "error": str(e)}


@router.post("/{part}/diagram")
async def get_clock_diagram(part: str, config: ClockConfig) -> StreamingResponse:
    """Generate and return clock diagram."""
    try:
        clk_chip = eval(f"adijif.{part}()")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Clock part {part} not found") from e

    # Apply selections
    for prop, values in config.selections.items():
        if isinstance(values, dict):
            props_available = getattr(clk_chip, prop + "_available")
            if (
                min(props_available) == values.get("start")
                and max(props_available) == values.get("end")
            ):
                continue
            picked = [
                v
                for v in props_available
                if values.get("start", 0) <= v <= values.get("end", float("inf"))
            ]
            setattr(clk_chip, prop, picked)
        else:
            if not values:
                continue
            setattr(clk_chip, prop, values)

    # Set requested clocks
    output_clocks = list(map(int, config.output_clocks))
    clk_chip.set_requested_clocks(config.reference_clock, output_clocks, config.output_names)

    try:
        clk_chip.solve()
        svg_data = clk_chip.draw()
        return StreamingResponse(io.BytesIO(svg_data.encode()), media_type="image/svg+xml")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating diagram: {e!s}") from e
