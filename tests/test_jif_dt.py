"""Tests for the versioned pyadi-jif -> pyadi-dt producer contract."""

from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from adijif.jif_dt import JifDtContract
from adijif.system import system as System


def _fake_system_and_solution():
    converter = SimpleNamespace(
        name="AD9680", converter_type="ADC", N=14, _nested=None
    )
    system = SimpleNamespace(
        converter=converter,
        fpga=SimpleNamespace(name="zc706"),
        clock=SimpleNamespace(name="HMC7044"),
        solver="CPLEX",
    )
    solution = {
        "jesd_AD9680": {
            "bit_clock": 10_000_000_000.0,
            "sample_clock": 1_000_000_000,
            "F": 1,
            "HD": 1,
            "K": 32,
            "L": 4,
            "M": 2,
            "Np": 16,
            "S": 1,
            "CS": 0,
            "jesd_class": "jesd204b",
        },
        "fpga_AD9680": {"type": "qpll", "sys_clk_select": "XCVR_QPLL0"},
        "clock": {
            "output_clocks": {
                "AD9680_ref_clk": {"rate": 1_000_000_000.0, "divider": 3},
                "AD9680_sysref": {"rate": 31_250_000.0, "divider": 96},
                "zc706_AD9680_ref_clk": {"rate": 250_000_000.0, "divider": 12},
                "zc706_AD9680_device_clk": {
                    "rate": 250_000_000.0,
                    "divider": 12,
                },
            }
        },
    }
    return system, solution


def test_system_solution_exports_semantic_contract_without_physical_channels():
    system, solution = _fake_system_and_solution()
    contract = JifDtContract.from_system_solution(system, solution)
    payload = contract.to_dict()

    assert payload["schema"] == "adi.jif-dt"
    assert payload["version"] == "1.0"
    assert payload["jesd_links"][0]["id"] == "ad9680.rx"
    assert payload["jesd_links"][0]["lane_rate_hz"] == 10_000_000_000
    assert {clock["id"] for clock in payload["clock_requirements"]} == {
        "ad9680.device-clock",
        "ad9680.sysref",
        "ad9680.fpga-ref",
        "ad9680.fpga-link",
    }
    assert all(
        "output_index" not in clock for clock in payload["clock_requirements"]
    )
    assert all(
        "dt_label" not in clock for clock in payload["clock_requirements"]
    )


def test_export_is_a_detached_deterministic_json_snapshot():
    system, solution = _fake_system_and_solution()
    contract = JifDtContract.from_system_solution(system, solution)
    before = contract.to_json()

    solution["fpga_AD9680"]["type"] = "cpll"
    solution["clock"]["output_clocks"]["AD9680_ref_clk"]["divider"] = 999

    assert contract.to_json() == before
    assert json.loads(before)["jesd_links"][0]["fpga_config"]["type"] == "qpll"


def test_export_rejects_fractional_hertz_and_unsupported_topology():
    system, solution = _fake_system_and_solution()
    fractional = deepcopy(solution)
    fractional["jesd_AD9680"]["bit_clock"] = 10_000_000_000.5
    with pytest.raises(ValueError, match="integral Hz"):
        JifDtContract.from_system_solution(system, fractional)

    system.converter = [system.converter]
    with pytest.raises(ValueError, match="one non-nested converter"):
        JifDtContract.from_system_solution(system, solution)


def test_system_rejects_unknown_export_format_before_solving():
    fake = object.__new__(System)
    with pytest.raises(ValueError, match="unsupported export format"):
        fake.export_config(format="raw-dict")
