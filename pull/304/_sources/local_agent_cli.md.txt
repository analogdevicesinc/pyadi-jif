# Local agent CLI

`jifagent` exposes the same component discovery, JESD-mode query, and system-solving operations as the pyadi-jif MCP server without starting a server. It is intended for local coding agents, shell automation, and tools that communicate through JSON over standard input and output.

## Installation

Install pyadi-jif with at least one solver:

```bash
pip install "pyadi-jif[cplex]"
```

The CLI itself is part of the base package and does not require the `mcp` extra.

## Agent protocol

Discover the available operations:

```bash
jifagent --compact tools
```

Invoke any MCP-equivalent operation by name:

```bash
jifagent --compact call list_components \
  --arguments '{"component_type":"converter"}'

jifagent --compact call query_jesd_modes \
  --arguments '{"component_name":"AD9081_RX","jesd_params_json":"{\"M\":4,\"L\":8,\"K\":32}"}'
```

For larger requests, pass a JSON object through standard input:

```bash
printf '%s' '{"component_type":"clock","component_name":"HMC7044"}' |
  jifagent --compact call get_component_info --arguments-file -
```

Each successful invocation writes exactly one JSON document to standard output and exits with status `0`. Operation errors are also returned as one JSON document, with an `error` field, and exit with status `1`. Solver diagnostics are directed to standard error so standard output remains machine-readable.

## Convenience commands

The common operations also have direct commands:

```bash
jifagent --compact components converter
jifagent --compact info clock HMC7044
jifagent --compact jesd-modes AD9081_RX --params '{"M":4,"L":8}'
```

Use `--pretty` instead of `--compact` for formatted output.

## Solve a system

Save an MCP-compatible system request as `system.json`:

```json
{
  "conv": "AD9680",
  "clk": "AD9523_1",
  "fpga": "XILINX",
  "vcxo": {"type": "fixed", "value": 125000000},
  "solver": "CPLEX",
  "converter_properties": {
    "sample_clock": 1000000000,
    "decimation": 1,
    "L": 4,
    "M": 2,
    "N": 14,
    "Np": 16,
    "K": 32,
    "F": 1
  },
  "fpga_properties": {
    "ref_clock_min": 60000000,
    "ref_clock_max": 670000000,
    "out_clk_select": "XCVR_REFCLK"
  }
}
```

Then solve it from a file or standard input:

```bash
jifagent --compact solve system.json
cat system.json | jifagent --compact solve -
```

The result contains `status`, the original `config`, and the solved `solution`. Set `"export_format": "adi.jif-dt"` in the request to include the versioned `adi.jif-dt` interoperability contract under the `contract` key.

For the complete request schema and MCP transport setup, see [pyadi-jif MCP Server](mcp_server.md).
