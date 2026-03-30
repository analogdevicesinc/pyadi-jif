# pyadi-jif MCP Server

The pyadi-jif **Model Context Protocol** (MCP) server provides a programmatic interface for
interacting with pyadi-jif functionalities, including querying JESD modes and performing
system-level solving. This server leverages the `fastmcp` library to expose its capabilities
as discoverable tools, making it accessible to AI assistants and other automated systems.

## Installation

Install pyadi-jif with the `mcp` optional extras:

```bash
pip install "pyadi-jif[mcp]"
```

## Starting the Server

### stdio (default — for Claude Desktop and local tools)

```bash
jifmcp
```

### HTTP transport

```bash
jifmcp --transport http --port 8000
```

## Claude Desktop Integration

Add the following snippet to your `claude_desktop_config.json` to connect pyadi-jif to
Claude Desktop:

```json
{
  "mcpServers": {
    "pyadi-jif": {
      "command": "jifmcp",
      "args": []
    }
  }
}
```

The config file is located at:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

Restart Claude Desktop after saving the file. The pyadi-jif tools will appear in the tools
panel.

## Available Tools

### `list_components`

Lists all available components of a given type.

```
list_components(component_type: str) -> dict
```

| Parameter        | Type | Description                                      |
|------------------|------|--------------------------------------------------|
| `component_type` | str  | One of `"converter"`, `"clock"`, or `"fpga"`.   |

**Returns** a dict with a `"components"` key containing a list of component name strings.

---

### `get_component_info`

Retrieves the docstring, constructor signature, and public properties of a specific component.

```
get_component_info(component_type: str, component_name: str) -> dict
```

| Parameter        | Type | Description                                                         |
|------------------|------|---------------------------------------------------------------------|
| `component_type` | str  | One of `"converter"`, `"clock"`, or `"fpga"`.                      |
| `component_name` | str  | Component name as returned by `list_components` (e.g. `"AD9081_RX"`). |

**Returns** a dict with keys `name`, `docstring`, `constructor_signature`, and `properties`.

---

### `query_jesd_modes`

Queries the available JESD modes for a converter component, optionally filtered by JESD
parameters.

```
query_jesd_modes(component_name: str, jesd_params_json: str = "{}") -> dict
```

| Parameter          | Type | Description                                                                          |
|--------------------|------|--------------------------------------------------------------------------------------|
| `component_name`   | str  | Converter name (e.g. `"AD9081_RX"`, `"ADRV9009_TX"`).                               |
| `jesd_params_json` | str  | JSON string of JESD filter parameters (e.g. `'{"M": 4, "L": 8, "K": 32}'`). Default: `"{}"` (all modes). |

**Returns** a dict with keys `component`, `jesd_modes` (list), and `query_params`.

---

### `solve_system`

Performs system-level clock and JESD solving based on a JSON configuration.

```
solve_system(system_config_json: str) -> dict
```

| Parameter           | Type | Description                                                  |
|---------------------|------|--------------------------------------------------------------|
| `system_config_json`| str  | JSON string describing the system. See schema below.         |

**Returns** a dict with keys `status` (`"solved"`), `solution`, and `config` on success, or
`error` on failure.

## `system_config_json` Schema

```json
{
  "conv": "AD9081_RX",
  "clk": "HMC7044",
  "fpga": "XILINX_BF",
  "vcxo": {
    "type": "fixed",
    "value": 100000000
  },
  "solver": "CPLEX",
  "converter_properties": {
    "sample_clock": 1000000000,
    "jesd_class": "jesd204c",
    "M": 4,
    "L": 8,
    "F": 1
  },
  "clock_properties": {
    "jesd_class": "jesd204c"
  },
  "fpga_properties": {},
  "pll_configurations": [
    {
      "type": "inline",
      "name": "ADF4371",
      "vcxo": { "type": "fixed", "value": 122880000 },
      "target_component": "converter",
      "pll_properties": {
        "r_divider": 1,
        "n_divider": 20
      }
    }
  ],
  "constraints": {}
}
```

**Field reference:**

| Field                  | Required | Description                                                                    |
|------------------------|----------|--------------------------------------------------------------------------------|
| `conv`                 | yes      | Converter name (e.g. `"AD9081_RX"`).                                          |
| `clk`                  | yes      | Clock chip name (e.g. `"HMC7044"`).                                           |
| `fpga`                 | yes      | FPGA name (e.g. `"XILINX_BF"`).                                               |
| `vcxo`                 | no       | VCXO config. Default: `{"type": "fixed", "value": 100000000}`.               |
| `vcxo.type`            | —        | `"fixed"` (requires `value`), `"range"` (requires `start`, `stop`, `step`), or `"arb_source"` (requires `frequency`, `count`). |
| `solver`               | no       | Solver to use. Default: `"CPLEX"`. Also supports `"GEKKO"`.                   |
| `converter_properties` | no       | Attributes to set on the converter instance.                                   |
| `clock_properties`     | no       | Attributes to set on the clock instance.                                       |
| `fpga_properties`      | no       | Attributes to set on the FPGA instance.                                        |
| `pll_configurations`   | no       | List of inline or sysref PLL configs. Each entry has `type`, `name`, `vcxo`, `target_component`, and `pll_properties`. |
| `constraints`          | no       | Output clock constraints dict passed to `sys.solve()`.                        |

## Python Client Example

```python
import asyncio
import json
from fastmcp import Client
from adijif.mcp_server import create_mcp_server

async def main():
    server = create_mcp_server()
    async with Client(server) as client:
        # List available converters
        result = await client.call_tool("list_components", {"component_type": "converter"})
        print("Converters:", result.data["components"])

        # Query JESD modes for AD9081_RX filtered by M=4, L=8
        result = await client.call_tool(
            "query_jesd_modes",
            {
                "component_name": "AD9081_RX",
                "jesd_params_json": json.dumps({"M": 4, "L": 8}),
            },
        )
        print("JESD modes:", result.data["jesd_modes"])

        # Solve a system
        system_config = {
            "conv": "AD9081_RX",
            "clk": "HMC7044",
            "fpga": "XILINX_BF",
            "vcxo": {"type": "fixed", "value": 100000000},
            "solver": "CPLEX",
            "converter_properties": {
                "sample_clock": 1000000000,
                "jesd_class": "jesd204c",
                "M": 4,
                "L": 8,
                "F": 1,
            },
            "clock_properties": {"jesd_class": "jesd204c"},
        }
        result = await client.call_tool(
            "solve_system", {"system_config_json": json.dumps(system_config)}
        )
        if "error" in result.data:
            print("Error:", result.data["error"])
        else:
            print("Solution:", result.data["solution"])

asyncio.run(main())
```
