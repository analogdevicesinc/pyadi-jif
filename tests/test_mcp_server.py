# flake8: noqa
import json

import pytest

pytest.importorskip("fastmcp")
pytest.importorskip("pytest_asyncio")
pytest.importorskip("inline_snapshot")

import pytest_asyncio
from fastmcp import Client
from inline_snapshot import snapshot

from adijif.mcp_server import _apply_converter_profile, create_mcp_server

from . import common


class _DummyProfileConverter:
    """Converter helper used to validate MCP profile application paths."""

    name = "DUMMY_CONVERTER"

    def __init__(self):
        self.quick_configuration_modes = {
            "jesd204b": {
                "1": {"M": 4, "L": 2, "S": 1, "Np": 16},
            }
        }
        self.apply_calls = []

    def apply_profile_settings(
        self, profile_path: str, bypass_version_check: bool = False
    ):
        self.apply_calls.append((profile_path, bypass_version_check))

    def set_quick_configuration_mode(self, mode, jesd_class: str = "jesd204b"):
        self.quick_mode = mode
        self.jesd_class = jesd_class
        for key, value in self.quick_configuration_modes[jesd_class][str(mode)].items():
            setattr(self, key, value)


class _DummyNestedProfileConverter:
    """Nested converter helper with ADC/DAC sub-converters."""

    _nested = ["adc", "dac"]

    def __init__(self):
        self.adc = _DummyProfileConverter()
        self.dac = _DummyProfileConverter()

    @property
    def name(self):
        return "DUMMY_NESTED_CONVERTER"


@pytest_asyncio.fixture
async def mcp_client():
    """
    Pytest fixture that provides an in-memory FastMCP client connected to a test server.
    """
    server = create_mcp_server()
    async with Client(server) as client:
        yield client


@pytest.mark.asyncio
async def test_list_tools(mcp_client: Client):
    """
    Tests listing available tools from the FastMCP server.
    """
    tools = await mcp_client.list_tools()
    tool_names = sorted([tool.name for tool in tools])  # Fixed: use tool.name
    assert tool_names == snapshot(
        [
            "get_component_info",
            "get_vcxo_references",
            "list_components",
            "query_jesd_modes",
            "solve_system",
        ]
    )


@pytest.mark.asyncio
async def test_get_vcxo_references(mcp_client: Client):
    """
    Tests querying VCXO presets from MCP.
    """
    result = await mcp_client.call_tool(
        "get_vcxo_references",
        {},
    )
    assert "vcxo_references" in result.data
    assert isinstance(result.data["vcxo_references"], list)

    triton = await mcp_client.call_tool(
        "get_vcxo_references",
        {
            "board": "Triton (Quad-Apollo)",
            "converter": "ad9084_rx",
            "clock_chip": "ltc6952",
        },
    )
    assert "vcxo_references" in triton.data
    assert len(triton.data["vcxo_references"]) == 1
    triton_ref = triton.data["vcxo_references"][0]
    assert triton_ref["vcxo_hz"] == 400_000_000
    assert triton_ref["pll"] == "adf4382"
    assert triton_ref["converters"] == ["ad9084"]
    assert "ad9084_rx" in triton_ref["compatible_parts"]

    # Verify all entries have required keys
    all_refs = result.data["vcxo_references"]
    for ref in all_refs:
        assert "pll" in ref
        assert "converters" in ref
        assert "compatible_parts" in ref

    # Filter by PLL — only AD9084 boards use adf4382
    pll_result = await mcp_client.call_tool(
        "get_vcxo_references",
        {"pll": "adf4382"},
    )
    pll_refs = pll_result.data["vcxo_references"]
    assert len(pll_refs) == 3
    assert all(r["pll"] == "adf4382" for r in pll_refs)

    # Boards without a PLL should not match a PLL filter
    no_match = await mcp_client.call_tool(
        "get_vcxo_references",
        {"pll": "ad9523_1"},
    )
    assert len(no_match.data["vcxo_references"]) == 0


@pytest.mark.asyncio
async def test_query_jesd_modes_valid(mcp_client: Client):
    """
    Tests the 'query_jesd_modes' tool with valid parameters.
    """
    component_name = "AD9081_RX"
    jesd_params = {"M": 4, "L": 8, "K": 32}
    jesd_params_json = json.dumps(jesd_params)

    result = await mcp_client.call_tool(
        "query_jesd_modes",
        {"component_name": component_name, "jesd_params_json": jesd_params_json},
    )
    assert "error" not in result.data
    assert result.data["component"] == component_name
    assert isinstance(result.data["jesd_modes"], list)
    assert len(result.data["jesd_modes"]) > 0
    assert result.data["query_params"] == jesd_params


@pytest.mark.asyncio
async def test_query_jesd_modes_invalid_component(mcp_client: Client):
    """
    Tests the 'query_jesd_modes' tool with an invalid component name.
    """
    component_name = "NON_EXISTENT_COMPONENT"
    jesd_params_json = json.dumps({"M": 4, "L": 8})

    result = await mcp_client.call_tool(
        "query_jesd_modes",
        {"component_name": component_name, "jesd_params_json": jesd_params_json},
    )
    assert "error" in result.data
    assert "not found in registry" in result.data["error"]


@pytest.mark.asyncio
async def test_query_jesd_modes_invalid_json(mcp_client: Client):
    """
    Tests the 'query_jesd_modes' tool with malformed JSON for jesd_params_json.
    """
    component_name = "AD9081_RX"
    jesd_params_json = "{'M': 4, 'L': 8"  # Malformed JSON

    result = await mcp_client.call_tool(
        "query_jesd_modes",
        {"component_name": component_name, "jesd_params_json": jesd_params_json},
    )
    assert "error" in result.data
    assert "Invalid JSON string" in result.data["error"]


@pytest.mark.asyncio
async def test_get_component_info_valid_converter(mcp_client: Client):
    """
    Tests the 'get_component_info' tool for a valid converter.
    """
    component_type = "converter"
    component_name = "AD9081_RX"

    result = await mcp_client.call_tool(
        "get_component_info",
        {"component_type": component_type, "component_name": component_name},
    )
    assert "error" not in result.data
    assert (
        result.data["name"] == "ad9081_rx"
    )  # Expected lowercase name from ComponentClass.__name__
    assert "docstring" in result.data
    assert "constructor_signature" in result.data
    assert "properties" in result.data
    assert "decimation" in result.data["properties"]  # Example property


@pytest.mark.asyncio
async def test_get_component_info_valid_clock(mcp_client: Client):
    """
    Tests the 'get_component_info' tool for a valid clock.
    """
    component_type = "clock"
    component_name = "HMC7044"

    result = await mcp_client.call_tool(
        "get_component_info",
        {"component_type": component_type, "component_name": component_name},
    )
    assert "error" not in result.data
    assert result.data["name"] == "hmc7044"  # Expected lowercase name
    assert "docstring" in result.data
    assert "constructor_signature" in result.data
    assert "properties" in result.data
    assert (
        "d" in result.data["properties"]
    )  # Example property 'd' confirmed from hmc7044.py


@pytest.mark.asyncio
async def test_get_component_info_invalid_type(mcp_client: Client):
    """
    Tests the 'get_component_info' tool with an invalid component type.
    """
    component_type = "invalid_type"
    component_name = "AD9081_RX"

    result = await mcp_client.call_tool(
        "get_component_info",
        {"component_type": component_type, "component_name": component_name},
    )
    assert "error" in result.data
    assert "Invalid component_type" in result.data["error"]


@pytest.mark.asyncio
async def test_get_component_info_invalid_name(mcp_client: Client):
    """
    Tests the 'get_component_info' tool with an invalid component name.
    """
    component_type = "converter"
    component_name = "NON_EXISTENT_CONVERTER"

    result = await mcp_client.call_tool(
        "get_component_info",
        {"component_type": component_type, "component_name": component_name},
    )
    assert "error" in result.data
    assert "not found" in result.data["error"]  # Simpler assertion


@pytest.mark.asyncio
async def test_list_components_valid(mcp_client: Client):
    """
    Tests the 'list_components' tool with valid component types.
    """
    for component_type in ["converter", "clock", "fpga"]:
        result = await mcp_client.call_tool(
            "list_components", {"component_type": component_type}
        )
        assert "error" not in result.data
        assert "components" in result.data
        assert isinstance(result.data["components"], list)
        assert len(result.data["components"]) > 0


@pytest.mark.asyncio
async def test_list_components_invalid_type(mcp_client: Client):
    """
    Tests the 'list_components' tool with an invalid component type.
    """
    result = await mcp_client.call_tool(
        "list_components", {"component_type": "invalid_type"}
    )
    assert "error" in result.data
    assert "Invalid component_type" in result.data["error"]


@pytest.mark.asyncio
async def test_list_components_pll(mcp_client: Client):
    """
    Tests listing available PLLs using the list_components tool.
    """
    result = await mcp_client.call_tool("list_components", {"component_type": "pll"})
    assert "error" not in result.data
    assert "components" in result.data
    assert isinstance(result.data["components"], list)
    assert "ADF4371" in result.data["components"]


@pytest.mark.asyncio
async def test_list_fpgas(mcp_client: Client):
    """
    Tests listing all available FPGAs using the list_components tool.
    """
    result = await mcp_client.call_tool("list_components", {"component_type": "fpga"})
    assert "error" not in result.data
    assert "components" in result.data
    available_fpgas = result.data["components"]
    print(f"\nAvailable FPGAs: {available_fpgas}")
    assert "XILINX_BF" in available_fpgas


# Minimal solve_system test (will likely be challenging due to CPLEX/solver requirements)


@pytest.mark.asyncio
async def test_solve_system_minimal_valid(mcp_client: Client):
    """
    Tests the 'solve_system' tool with a minimal valid configuration.
    This test is highly dependent on CPLEX being correctly set up and
    a minimal configuration actually yielding a solution.
    """
    common.skip_solver("CPLEX")
    # This configuration is very basic and might need adjustment based on
    # actual valid minimal setups for adijif.system
    system_config = {
        "conv": "AD9081_RX",
        "clk": "HMC7044",
        "fpga": "XILINX",
        "vcxo": {"type": "fixed", "value": 100000000},
        "solver": "CPLEX",
        "converter_properties": {
            "sample_clock": 250000000,
            "M": 8,
            "L": 4,
            "Np": 16,
            "K": 32,
            "F": 4,
            "S": 1,
        },
        "clock_properties": {},
        "fpga_properties": {
            "ref_clock_min": 60000000,
            "ref_clock_max": 670000000,
            "out_clk_select": "XCVR_REFCLK",
        },
        "constraints": {},
    }
    system_config_json = json.dumps(system_config)

    result = await mcp_client.call_tool(
        "solve_system", {"system_config_json": system_config_json}
    )
    # This test might fail if CPLEX is not correctly set up or if the
    # minimal config does not yield a valid solution.
    assert (
        "error" not in result.data
    ), f"Error in solve_system: {result.data.get('error')}"
    assert result.data["status"] == "solved"
    assert "solution" in result.data
    assert isinstance(result.data["solution"], dict)


@pytest.mark.asyncio
async def test_solve_system_invalid_config(mcp_client: Client):
    """
    Tests the 'solve_system' tool with an invalid configuration (missing components).
    """
    system_config = {
        "clk": "HMC7044",
        "fpga": "XILINX_BF",  # Fixed: Corrected FPGA name
        "vcxo": {"type": "fixed", "value": 100000000},
    }
    system_config_json = json.dumps(system_config)

    result = await mcp_client.call_tool(
        "solve_system", {"system_config_json": system_config_json}
    )
    assert "error" in result.data
    assert (
        "System configuration must specify 'conv', 'clk', and 'fpga'."
        in result.data["error"]
    )


@pytest.mark.asyncio
async def test_solve_system_invalid_json(mcp_client: Client):
    """
    Tests the 'solve_system' tool with malformed JSON.
    """
    system_config_json = "{'conv': 'AD9081_RX'"  # Malformed JSON

    result = await mcp_client.call_tool(
        "solve_system", {"system_config_json": system_config_json}
    )
    assert "error" in result.data
    assert "Invalid JSON string" in result.data["error"]


@pytest.mark.asyncio
async def test_solve_system_invalid_converter(mcp_client: Client):
    """
    Tests the 'solve_system' tool with an invalid converter name.
    """
    system_config = {
        "conv": "INVALID_CONVERTER",
        "clk": "HMC7044",
        "fpga": "XILINX_BF",
        "vcxo": {"type": "fixed", "value": 100000000},
    }
    system_config_json = json.dumps(system_config)

    result = await mcp_client.call_tool(
        "solve_system", {"system_config_json": system_config_json}
    )
    assert "error" in result.data
    assert "Converter 'INVALID_CONVERTER' not found in registry" in result.data["error"]


@pytest.mark.asyncio
async def test_solve_system_invalid_clock(mcp_client: Client):
    """
    Tests the 'solve_system' tool with an invalid clock name.
    """
    system_config = {
        "conv": "AD9081_RX",
        "clk": "INVALID_CLOCK",
        "fpga": "XILINX_BF",
        "vcxo": {"type": "fixed", "value": 100000000},
    }
    system_config_json = json.dumps(system_config)

    result = await mcp_client.call_tool(
        "solve_system", {"system_config_json": system_config_json}
    )
    assert "error" in result.data
    assert "Clock 'INVALID_CLOCK' not found in registry" in result.data["error"]


@pytest.mark.asyncio
async def test_solve_system_invalid_fpga(mcp_client: Client):
    """
    Tests the 'solve_system' tool with an invalid FPGA name.
    """
    system_config = {
        "conv": "AD9081_RX",
        "clk": "HMC7044",
        "fpga": "INVALID_FPGA",
        "vcxo": {"type": "fixed", "value": 100000000},
    }
    system_config_json = json.dumps(system_config)

    result = await mcp_client.call_tool(
        "solve_system", {"system_config_json": system_config_json}
    )
    assert "error" in result.data
    assert "FPGA 'INVALID_FPGA' not found in registry" in result.data["error"]


@pytest.mark.asyncio
@pytest.mark.skip(
    reason="GEKKO solver is not fully supported and may not be installed."
)
async def test_solve_system_with_gekko_solver(mcp_client: Client):
    """
    Tests the 'solve_system' tool with the GEKKO solver.
    """
    system_config = {
        "conv": "AD9081_RX",
        "clk": "HMC7044",
        "fpga": "XILINX_BF",
        "vcxo": {"type": "fixed", "value": 100000000},
        "solver": "GEKKO",
        "converter_properties": {
            "sample_clock": 1000000000,
            "jesd_class": "jesd204c",
            "M": 4,
            "L": 8,
            "F": 1,
        },
        "clock_properties": {"jesd_class": "jesd204c"},
        "fpga_properties": {},
        "constraints": {},
    }
    system_config_json = json.dumps(system_config)

    result = await mcp_client.call_tool(
        "solve_system", {"system_config_json": system_config_json}
    )
    assert "error" not in result.data
    assert result.data["status"] == "solved"


def test_apply_converter_profile_uses_apply_profile_settings(tmp_path):
    """Profile payload with a path should call converter-level apply_profile_settings."""
    converter = _DummyProfileConverter()
    converter_profile = tmp_path / "ad9084_profile.json"
    converter_profile.write_text("{}")

    _apply_converter_profile(
        converter,
        {"path": str(converter_profile), "bypass_version_check": True},
    )

    assert converter.apply_calls == [(str(converter_profile), True)]


def test_apply_converter_profile_uses_mode_lookup():
    """Quick-mode profile data should infer and apply JESD mode settings."""
    converter = _DummyProfileConverter()

    _apply_converter_profile(
        converter,
        {"M": 4, "L": 2, "S": 1, "Np": 16, "jesd_class": "jesd204b"},
    )

    assert converter.quick_mode == "1"
    assert converter.jesd_class == "jesd204b"
    assert converter.M == 4
    assert converter.L == 2
    assert converter.Np == 16


def test_apply_converter_profile_nested_converter_applies_sides(tmp_path):
    """Nested converter profiles should apply ADC and DAC payloads independently."""
    converter = _DummyNestedProfileConverter()

    _apply_converter_profile(
        converter,
        {
            "adc": {"mode": "1", "jesd_class": "jesd204b"},
            "dac": {"M": 4, "L": 2, "S": 1, "Np": 16, "jesd_class": "jesd204b"},
        },
    )

    assert converter.adc.quick_mode == "1"
    assert converter.dac.quick_mode == "1"


def test_apply_converter_profile_nested_converter_with_path(tmp_path):
    """Nested converters without side maps should apply the same payload to ADC/DAC."""
    converter = _DummyNestedProfileConverter()
    profile_path = tmp_path / "nested_profile.json"
    profile_path.write_text(
        '{"jesd_class": "jesd204b", "M": 4, "L": 2, "S": 1, "Np": 16}'
    )

    _apply_converter_profile(converter, str(profile_path))

    assert converter.adc.quick_mode == "1"
    assert converter.dac.quick_mode == "1"
