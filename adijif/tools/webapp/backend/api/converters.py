"""Converter API endpoints for JESD204 mode selection."""

import io
import logging
from typing import Any

import adijif
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from adijif.converters import supported_parts as sp
from adijif.utils import get_jesd_mode_from_params

from adijif.tools.webapp.backend.services.diagram_service import (
    draw_adc_diagram,
    draw_dac_diagram,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ConverterConfig(BaseModel):
    """Converter configuration model."""

    part: str
    sample_clock: float
    decimation: int | None = None
    interpolation: int | None = None
    cddc_decimation: int | None = None
    fddc_decimation: int | None = None
    cduc_interpolation: int | None = None
    fduc_interpolation: int | None = None


class JESDModeFilter(BaseModel):
    """JESD mode filter parameters."""

    part: str
    sample_clock: float
    decimation: int | None = None
    interpolation: int | None = None
    cddc_decimation: int | None = None
    fddc_decimation: int | None = None
    cduc_interpolation: int | None = None
    fduc_interpolation: int | None = None
    filters: dict[str, list[Any]] = {}


@router.get("/supported")
async def get_supported_converters() -> list[str]:
    """Get list of supported converter parts."""
    supported_parts_filtered = []
    for part in sp:
        try:
            converter = eval(f"adijif.{part}()")
            _ = converter.quick_configuration_modes
            supported_parts_filtered.append(part)
        except Exception:
            pass
    return supported_parts_filtered


@router.get("/{part}/info")
async def get_converter_info(part: str) -> dict[str, Any]:
    """Get converter information including type and available datapaths."""
    try:
        converter = eval(f"adijif.{part}()")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Converter {part} not found") from e

    info = {
        "part": part,
        "converter_type": converter.converter_type.lower(),
        "has_datapath": bool(converter.datapath),
    }

    # Add datapath information
    if converter.datapath:
        if hasattr(converter.datapath, "cddc_decimations_available"):
            info["cddc_decimations_available"] = converter.datapath.cddc_decimations_available
        if hasattr(converter.datapath, "fddc_decimations_available"):
            info["fddc_decimations_available"] = converter.datapath.fddc_decimations_available
        if hasattr(converter.datapath, "cduc_interpolations_available"):
            info["cduc_interpolations_available"] = converter.datapath.cduc_interpolations_available
        if hasattr(converter.datapath, "fduc_interpolations_available"):
            info["fduc_interpolations_available"] = converter.datapath.fduc_interpolations_available
    elif hasattr(converter, "decimation_available"):
        info["decimation_available"] = converter.decimation_available
    elif hasattr(converter, "interpolation_available"):
        info["interpolation_available"] = converter.interpolation_available

    return info


@router.get("/{part}/quick-modes")
async def get_quick_configuration_modes(part: str) -> dict[str, Any]:
    """Get quick configuration modes for a converter."""
    try:
        converter = eval(f"adijif.{part}()")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Converter {part} not found") from e

    try:
        qsm = converter.quick_configuration_modes
        return qsm
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting modes: {e!s}") from e


@router.post("/{part}/jesd-controls")
async def get_jesd_controls(part: str) -> dict[str, Any]:
    """Get JESD control options for a converter."""
    try:
        converter = eval(f"adijif.{part}()")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Converter {part} not found") from e

    options_to_skip = ["global_index", "decimations", "interpolations"]

    all_modes = converter.quick_configuration_modes
    subclasses = list(all_modes.keys())

    mode_knobs = None
    for subclass in subclasses:
        ks = list(all_modes[subclass].keys())
        if len(ks) == 0:
            continue
        first_mode = list(all_modes[subclass].keys())[0]
        mode_settings = sorted(all_modes[subclass][first_mode].keys())
        if not mode_knobs:
            mode_knobs = mode_settings
            continue

        if mode_settings != mode_knobs:
            logger.warning("Mode settings are not consistent across all subclasses")

    # Parse all options for each control across modes
    options = {}
    for setting in mode_knobs or []:
        if setting in options_to_skip:
            continue
        options[setting] = []
        for subclass in subclasses:
            for mode in all_modes[subclass]:
                data = all_modes[subclass][mode][setting]
                if isinstance(data, list):
                    continue
                options[setting].append(data)

    # Make sure options only contain unique values
    for option in options:
        options[option] = list(set(options[option]))

    return {"options": options, "all_modes": all_modes}


@router.post("/{part}/valid-modes")
async def get_valid_jesd_modes(part: str, config: JESDModeFilter) -> dict[str, Any]:
    """Get valid JESD modes based on configuration and filters."""
    try:
        converter = eval(f"adijif.{part}()")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Converter {part} not found") from e

    # Configure converter
    converter.sample_clock = config.sample_clock

    if converter.converter_type.lower() == "adc":
        if config.decimation:
            converter.decimation = config.decimation
        if converter.datapath:
            if config.cddc_decimation and hasattr(converter.datapath, "cddc_decimations"):
                v = len(converter.datapath.cddc_decimations)
                converter.datapath.cddc_decimations = [config.cddc_decimation] * v
            if config.fddc_decimation and hasattr(converter.datapath, "fddc_decimations"):
                v = len(converter.datapath.fddc_decimations)
                converter.datapath.fddc_decimations = [config.fddc_decimation] * v
    else:
        if config.interpolation:
            converter.interpolation = config.interpolation
        if converter.datapath:
            if config.cduc_interpolation and hasattr(converter.datapath, "cduc_interpolation"):
                converter.datapath.cduc_interpolation = config.cduc_interpolation
            if config.fduc_interpolation and hasattr(converter.datapath, "fduc_interpolation"):
                converter.datapath.fduc_interpolation = config.fduc_interpolation

    # Get modes based on filters
    try:
        found_modes = get_jesd_mode_from_params(converter, **config.filters)
    except Exception as e:
        return {"modes": [], "error": str(e)}

    all_modes = converter.quick_configuration_modes
    options_to_skip = ["global_index", "decimations", "interpolations"]

    modes_all_info = []
    for mode in found_modes:
        jesd_cfg = all_modes[mode["jesd_class"]][mode["mode"]].copy()
        jesd_cfg["mode"] = mode["mode"]
        jesd_cfg["jesd_class"] = mode["jesd_class"]

        for option in options_to_skip:
            jesd_cfg.pop(option, None)

        # Calculate clocks
        rate = converter.sample_clock
        converter.set_quick_configuration_mode(mode["mode"], mode["jesd_class"])
        converter.sample_clock = rate

        jesd_cfg["Sample Rate (MSPS)"] = converter.sample_clock / 1e6
        jesd_cfg["Lane Rate (GSPS)"] = converter.bit_clock / 1e9

        try:
            converter.validate_config()
            jesd_cfg["Valid"] = "Yes"
        except Exception:
            jesd_cfg["Valid"] = "No"

        modes_all_info.append(jesd_cfg)

    return {"modes": modes_all_info}


@router.get("/{part}/diagram")
async def get_converter_diagram(part: str) -> StreamingResponse:
    """Get SVG diagram for a converter."""
    try:
        converter = eval(f"adijif.{part}()")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Converter {part} not found") from e

    try:
        if converter.converter_type.lower() == "adc":
            svg_data = draw_adc_diagram(converter)
        else:
            svg_data = draw_dac_diagram(converter)

        return StreamingResponse(io.BytesIO(svg_data.encode()), media_type="image/svg+xml")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating diagram: {e!s}") from e
