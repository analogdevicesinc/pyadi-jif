"""Tests for the JSON local-agent CLI."""

import json
from types import SimpleNamespace

from click.testing import CliRunner

import adijif.agent_api as agent_api
from adijif.cli import main


def _json(result):
    assert result.output
    return json.loads(result.output)


def test_tools_describes_mcp_equivalent_operations():
    result = CliRunner().invoke(main, ["--compact", "tools"])

    assert result.exit_code == 0
    tools = _json(result)["tools"]
    assert [tool["name"] for tool in tools] == [
        "list_components",
        "query_jesd_modes",
        "get_component_info",
        "solve_system",
    ]
    assert tools[0]["input_schema"] == {
        "additionalProperties": False,
        "properties": {"component_type": {"type": "string"}},
        "required": ["component_type"],
        "type": "object",
    }


def test_components_outputs_json_only():
    result = CliRunner().invoke(main, ["--compact", "components", "converter"])

    assert result.exit_code == 0
    assert "AD9680" in _json(result)["components"]


def test_info_outputs_component_contract():
    result = CliRunner().invoke(
        main, ["--compact", "info", "clock", "HMC7044"]
    )

    assert result.exit_code == 0
    payload = _json(result)
    assert payload["name"] == "hmc7044"
    assert "d" in payload["properties"]


def test_jesd_modes_accepts_stdin_json():
    result = CliRunner().invoke(
        main,
        ["--compact", "jesd-modes", "AD9081_RX", "--params-file", "-"],
        input='{"M": 4, "L": 8, "K": 32}',
    )

    assert result.exit_code == 0
    payload = _json(result)
    assert payload["query_params"] == {"M": 4, "L": 8, "K": 32}
    assert payload["jesd_modes"]


def test_generic_call_accepts_mcp_tool_name_and_arguments():
    result = CliRunner().invoke(
        main,
        [
            "--compact",
            "call",
            "list_components",
            "--arguments",
            '{"component_type": "pll"}',
        ],
    )

    assert result.exit_code == 0
    assert "ADF4030" in _json(result)["components"]


def test_operation_error_is_json_and_nonzero():
    result = CliRunner().invoke(
        main, ["--compact", "components", "not-a-component-type"]
    )

    assert result.exit_code == 1
    assert "Invalid component_type" in _json(result)["error"]


def test_solve_reads_stdin_and_returns_json_error():
    result = CliRunner().invoke(
        main,
        ["--compact", "solve", "-"],
        input='{"conv": "AD9680"}',
    )

    assert result.exit_code == 1
    assert "must specify 'conv', 'clk', and 'fpga'" in _json(result)["error"]


def test_call_rejects_non_object_arguments():
    result = CliRunner().invoke(
        main,
        ["--compact", "call", "list_components", "--arguments", "[]"],
    )

    assert result.exit_code == 1
    assert "arguments must be a JSON object" in _json(result)["error"]


def test_call_rejects_wrong_argument_types_as_json():
    result = CliRunner().invoke(
        main,
        [
            "--compact",
            "call",
            "list_components",
            "--arguments",
            '{"component_type": 1}',
        ],
    )

    assert result.exit_code == 1
    assert _json(result)["error"] == "component_type must be a string"


def test_call_input_errors_are_json(tmp_path):
    missing = tmp_path / "missing.json"
    result = CliRunner().invoke(
        main,
        [
            "--compact",
            "call",
            "list_components",
            "--arguments-file",
            str(missing),
        ],
    )

    assert result.exit_code == 1
    assert "Invalid arguments JSON" in _json(result)["error"]


def test_solve_wires_supported_pll_topologies(monkeypatch):
    created = []

    class FakeSystem:
        def __init__(self):
            self.converter = SimpleNamespace(name="AD9680")
            self.clock = SimpleNamespace(name="AD9523_1")
            self.fpga = SimpleNamespace(name="XILINX")
            self.plls = []
            self._plls_sysref = []
            self.calls = []

        def add_pll_inline(self, name, clock, converter):
            self.calls.append(("inline", name, clock, converter))
            self.plls.append(SimpleNamespace(r_divider=0))

        def add_pll_sysref(self, name, clock, converter, fpga):
            self.calls.append(("sysref", name, clock, converter, fpga))
            self._plls_sysref.append(SimpleNamespace(r_divider=0))

        def solve(self, out_clock_constraints):
            return {"constraints": out_clock_constraints}

    def factory(**kwargs):
        instance = FakeSystem()
        created.append(instance)
        return instance

    monkeypatch.setattr(agent_api, "_system", factory)
    config = {
        "conv": "AD9680",
        "clk": "AD9523_1",
        "fpga": "XILINX",
        "pll_configurations": [
            {
                "type": "inline",
                "name": "ADF4382",
                "target_component": "converter",
                "pll_properties": {"r_divider": 2},
            },
            {
                "type": "sysref",
                "name": "ADF4030",
                "pll_properties": {"r_divider": 3},
            },
        ],
    }

    result = agent_api.solve_system(json.dumps(config))

    assert result["status"] == "solved"
    system = created[0]
    assert system.calls[0] == (
        "inline",
        "ADF4382",
        system.clock,
        system.converter,
    )
    assert system.calls[1] == (
        "sysref",
        "ADF4030",
        system.clock,
        system.converter,
        system.fpga,
    )
    assert system.plls[0].r_divider == 2
    assert system._plls_sysref[0].r_divider == 3


def test_solve_rejects_obsolete_per_pll_vcxo():
    config = {
        "conv": "AD9680",
        "clk": "AD9523_1",
        "fpga": "XILINX",
        "pll_configurations": [
            {
                "type": "inline",
                "name": "ADF4382",
                "vcxo": {"type": "fixed", "value": 125_000_000},
            }
        ],
    }

    result = agent_api.solve_system(json.dumps(config))

    assert "Per-PLL 'vcxo' is not supported" in result["error"]
