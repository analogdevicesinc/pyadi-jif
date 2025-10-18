"""System API endpoints for full system configuration."""

import io
import logging
from typing import Any

import adijif
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from adijif.clocks import supported_parts as clock_sp
from adijif.converters import supported_parts as converter_sp

logger = logging.getLogger(__name__)

router = APIRouter()

# Parse parts to exclude
clock_parts_to_ignore = ["ad9545", "ad9523_1"]
supported_clock_parts = [p for p in clock_sp if p not in clock_parts_to_ignore]
supported_clock_parts = [p for p in supported_clock_parts if p != "hmc7044"]
supported_clock_parts.insert(0, "hmc7044")


class SystemConfig(BaseModel):
    """System configuration model."""

    converter_part: str
    clock_part: str
    fpga_dev_kit: str
    reference_rate: float
    sample_clock: float
    decimation: int
    quick_mode: str
    jesd_class: str
    ref_clock_constraint: str
    sys_clk_select: str
    out_clk_select: list[str]
    force_pll: str


@router.get("/fpga-dev-kits")
async def get_fpga_dev_kits() -> list[str]:
    """Get list of available FPGA development kits."""
    return adijif.xilinx._available_dev_kit_names


@router.get("/fpga-constraints")
async def get_fpga_constraints() -> dict[str, Any]:
    """Get FPGA constraint options."""
    return {
        "ref_clock_constraints": adijif.xilinx._ref_clock_constraint_options,
        "sys_clk_selections": adijif.xilinx.sys_clk_selections,
        "out_clk_selections": adijif.xilinx._out_clk_selections,
    }


@router.post("/solve")
async def solve_system_config(config: SystemConfig) -> dict[str, Any]:
    """Solve complete system configuration."""
    try:
        # Create system
        sys = adijif.system(
            config.converter_part.lower(),
            config.clock_part.lower(),
            "xilinx",
            config.reference_rate,
        )

        # Configure converter
        sys.converter.sample_clock = config.sample_clock
        sys.converter.decimation = config.decimation
        sys.converter.set_quick_configuration_mode(config.quick_mode, config.jesd_class)

        # Configure FPGA
        sys.fpga.setup_by_dev_kit_name(config.fpga_dev_kit.lower())
        sys.fpga.ref_clock_constraint = config.ref_clock_constraint
        sys.fpga.sys_clk_select = config.sys_clk_select
        sys.fpga.out_clk_select = config.out_clk_select

        # Set PLL configuration
        if config.force_pll == "Force QPLL":
            sys.fpga.force_qpll = True
        elif config.force_pll == "Force QPLL1":
            sys.fpga.force_qpll1 = True
        elif config.force_pll == "Force CPLL":
            sys.fpga.force_cpll = True

        sys.Debug_Solver = False

        # Solve
        cfg = sys.solve()

        return {"success": True, "config": cfg}
    except Exception as e:
        logger.error(f"Failed to solve system configuration: {e}")
        return {"success": False, "error": str(e)}


@router.post("/diagram")
async def get_system_diagram(config: SystemConfig) -> StreamingResponse:
    """Generate and return system diagram."""
    try:
        # Create system
        sys = adijif.system(
            config.converter_part.lower(),
            config.clock_part.lower(),
            "xilinx",
            config.reference_rate,
        )

        # Configure converter
        sys.converter.sample_clock = config.sample_clock
        sys.converter.decimation = config.decimation
        sys.converter.set_quick_configuration_mode(config.quick_mode, config.jesd_class)

        # Configure FPGA
        sys.fpga.setup_by_dev_kit_name(config.fpga_dev_kit.lower())
        sys.fpga.ref_clock_constraint = config.ref_clock_constraint
        sys.fpga.sys_clk_select = config.sys_clk_select
        sys.fpga.out_clk_select = config.out_clk_select

        # Set PLL configuration
        if config.force_pll == "Force QPLL":
            sys.fpga.force_qpll = True
        elif config.force_pll == "Force QPLL1":
            sys.fpga.force_qpll1 = True
        elif config.force_pll == "Force CPLL":
            sys.fpga.force_cpll = True

        sys.Debug_Solver = False

        # Solve and draw
        cfg = sys.solve()
        svg_data = sys.draw(cfg)

        return StreamingResponse(io.BytesIO(svg_data.encode()), media_type="image/svg+xml")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating diagram: {e!s}") from e
