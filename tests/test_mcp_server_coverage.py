"""Additional tests for adijif.mcp_server to improve coverage."""

import json
import pytest
from adijif.mcp_server import create_mcp_server, _parse_vcxo, _apply_config_recursively


def test_mcp_parse_vcxo_range():
    """Verify _parse_vcxo with range type."""
    config = {
        "type": "range",
        "start": int(100e6),
        "stop": int(200e6),
        "step": int(1e6)
    }
    res = _parse_vcxo(config)
    assert res.start == 100e6
    assert res.stop == 200e6


def test_mcp_parse_vcxo_range_missing_fields_should_raise():
    """Verify _parse_vcxo range validation."""
    config = {"type": "range", "start": int(100e6)}
    with pytest.raises(ValueError, match="requires 'start', 'stop', and 'step'"):
        _parse_vcxo(config)


def test_mcp_parse_vcxo_arb_source():
    """Verify _parse_vcxo with arb_source type."""
    config = {
        "type": "arb_source",
        "frequency": 125e6,
        "count": 1
    }
    res = _parse_vcxo(config)
    assert res.name == "125000000.0"


def test_mcp_parse_vcxo_arb_source_missing_fields_should_raise():
    """Verify _parse_vcxo arb_source validation."""
    config = {"type": "arb_source", "frequency": 125e6}
    with pytest.raises(ValueError, match="requires 'frequency' and 'count'"):
        _parse_vcxo(config)


def test_mcp_apply_config_recursively():
    """Verify recursive config application."""
    class Sub:
        def __init__(self): self.val = 0
    class Obj:
        def __init__(self):
            self.sub = Sub()
            self.top = 0
    
    o = Obj()
    config = {"top": 1, "sub": {"val": 2}, "new_attr": 3}
    _apply_config_recursively(o, config)
    
    assert o.top == 1
    assert o.sub.val == 2
    assert o.new_attr == 3


async def _get_mcp_tool_fn(mcp, name):
    """Helper to get a tool function from FastMCP instance."""
    tool = await mcp.get_tool(name)
    return tool.fn


@pytest.mark.asyncio
async def test_mcp_list_components_invalid_type():
    """Verify list_components error handling for invalid type."""
    mcp = create_mcp_server()
    fn = await _get_mcp_tool_fn(mcp, "list_components")
    res = fn(component_type="invalid")
    assert "error" in res
    assert "Invalid component_type" in res["error"]


@pytest.mark.asyncio
async def test_mcp_query_jesd_modes_not_found():
    """Verify query_jesd_modes error handling for unknown component."""
    mcp = create_mcp_server()
    fn = await _get_mcp_tool_fn(mcp, "query_jesd_modes")
    res = fn(component_name="NON_EXISTENT")
    assert "error" in res
    assert "not found in registry" in res["error"]


@pytest.mark.asyncio
async def test_mcp_query_jesd_modes_invalid_json():
    """Verify query_jesd_modes error handling for invalid JSON."""
    mcp = create_mcp_server()
    fn = await _get_mcp_tool_fn(mcp, "query_jesd_modes")
    res = fn(component_name="AD9680", jesd_params_json="{invalid")
    assert "error" in res
    assert "Invalid JSON string" in res["error"]


@pytest.mark.asyncio
async def test_mcp_get_component_info_invalid_type():
    """Verify get_component_info error handling for invalid type."""
    mcp = create_mcp_server()
    fn = await _get_mcp_tool_fn(mcp, "get_component_info")
    res = fn(component_type="invalid", component_name="ANY")
    assert "error" in res


@pytest.mark.asyncio
async def test_mcp_get_component_info_not_found():
    """Verify get_component_info error handling for unknown component."""
    mcp = create_mcp_server()
    fn = await _get_mcp_tool_fn(mcp, "get_component_info")
    res = fn(component_type="converter", component_name="NON_EXISTENT")
    assert "error" in res


@pytest.mark.asyncio
async def test_mcp_solve_system_invalid_json():
    """Verify solve_system error handling for invalid JSON."""
    mcp = create_mcp_server()
    fn = await _get_mcp_tool_fn(mcp, "solve_system")
    res = fn(system_config_json="{invalid")
    assert "error" in res
    assert "Invalid JSON string" in res["error"]


@pytest.mark.asyncio
async def test_mcp_solve_system_missing_fields():
    """Verify solve_system error handling for missing required fields."""
    mcp = create_mcp_server()
    fn = await _get_mcp_tool_fn(mcp, "solve_system")
    res = fn(system_config_json=json.dumps({"conv": "AD9680"}))
    assert "error" in res
    assert "must specify 'conv', 'clk', and 'fpga'" in res["error"]


@pytest.mark.asyncio
async def test_mcp_solve_system_component_not_found():
    """Verify solve_system error handling for unknown components."""
    mcp = create_mcp_server()
    fn = await _get_mcp_tool_fn(mcp, "solve_system")
    config = {"conv": "UNKNOWN", "clk": "AD9523_1", "fpga": "XILINX"}
    res = fn(system_config_json=json.dumps(config))
    assert "error" in res
    assert "not found in registry" in res["error"]


@pytest.mark.asyncio
async def test_mcp_solve_system_invalid_pll_type():
    """Verify solve_system error handling for unsupported PLL type."""
    mcp = create_mcp_server()
    fn = await _get_mcp_tool_fn(mcp, "solve_system")
    config = {
        "conv": "AD9680", "clk": "AD9523_1", "fpga": "XILINX",
        "pll_configurations": [{
            "type": "invalid", 
            "name": "ADF4371",
            "vcxo": {"value": 125e6},
            "target_component": "converter"
        }]
    }
    res = fn(system_config_json=json.dumps(config))
    assert "error" in res
    assert "Unsupported PLL configuration type" in res["error"]


@pytest.mark.asyncio
async def test_mcp_solve_system_pll_not_found():
    """Verify solve_system error handling for unknown PLL name."""
    mcp = create_mcp_server()
    fn = await _get_mcp_tool_fn(mcp, "solve_system")
    config = {
        "conv": "AD9680", "clk": "AD9523_1", "fpga": "XILINX",
        "pll_configurations": [{
            "type": "inline", 
            "name": "UNKNOWN", 
            "vcxo": {"value": 125e6}, 
            "target_component": "converter"
        }]
    }
    res = fn(system_config_json=json.dumps(config))
    assert "error" in res
    assert "not found in clock registry" in res["error"]


@pytest.mark.asyncio
async def test_mcp_solve_system_invalid_target_component():
    """Verify solve_system error handling for invalid target component."""
    mcp = create_mcp_server()
    fn = await _get_mcp_tool_fn(mcp, "solve_system")
    config = {
        "conv": "AD9680", "clk": "AD9523_1", "fpga": "XILINX",
        "pll_configurations": [{
            "type": "inline", 
            "name": "HMC7044", 
            "vcxo": {"value": 125e6}, 
            "target_component": "invalid"
        }]
    }
    res = fn(system_config_json=json.dumps(config))
    assert "error" in res
    assert "Invalid target_component" in res["error"]

