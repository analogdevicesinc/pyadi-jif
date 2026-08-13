"""Typed exceptions for solver outcomes.

An infeasible request is a normal thing for a caller to handle - the user asked
for output frequencies the part cannot produce - and it should be
distinguishable from a missing solver backend or an internal defect without
inspecting exception message text.
"""

import pytest

import adijif
from adijif.exceptions import (
    InfeasibleError,
    JIFError,
    SolverError,
    UnsupportedSolverError,
)


def test_exception_types_are_exported():
    for name in (
        "JIFError",
        "SolverError",
        "InfeasibleError",
        "UnsupportedSolverError",
        "UnsupportedPartError",
        "InvalidConfigurationError",
    ):
        assert hasattr(adijif, name), f"adijif.{name} is not exported"


def test_hierarchy_keeps_broad_handlers_working():
    """Existing callers catch Exception; that must not change."""
    assert issubclass(InfeasibleError, SolverError)
    assert issubclass(SolverError, JIFError)
    assert issubclass(JIFError, Exception)
    assert issubclass(UnsupportedSolverError, SolverError)


@pytest.mark.parametrize("solver", ["CPLEX"])
def test_infeasible_clock_request_raises_infeasible_error(solver):
    """Frequencies above the VCO ceiling have no solution at any divider."""
    clk = adijif.hmc7044(solver=solver)
    clk.set_requested_clocks(100000000, [4000000000] * 4, ["A", "B", "C", "D"])

    with pytest.raises(InfeasibleError):
        clk.solve()


def test_infeasible_is_still_catchable_as_exception():
    """The backward-compatible path, which is how callers behave today."""
    clk = adijif.hmc7044(solver="CPLEX")
    clk.set_requested_clocks(100000000, [4000000000] * 4, ["A", "B", "C", "D"])

    with pytest.raises(Exception):  # noqa: B017 - the point is the broad catch
        clk.solve()


def test_unknown_solver_raises_unsupported_solver_error():
    clk = adijif.hmc7044(solver="CPLEX")
    clk.solver = "definitely-not-a-solver"

    with pytest.raises(UnsupportedSolverError):
        clk.solve()


def test_feasible_request_still_solves():
    """The happy path must be untouched by the exception work.

    Asserted as invariants rather than against a specific solution: which VCO
    the model picks is a legitimate modelling choice that may change, but the
    divider relationship and the VCO bounds may not.
    """
    clk = adijif.hmc7044(solver="CPLEX")
    clk.set_requested_clocks(100000000, [10000000] * 4, ["A", "B", "C", "D"])

    config = clk.get_config(clk.solve())

    assert clk.vco_min <= config["vco"] <= clk.vco_max
    for divider in config["out_dividers"]:
        assert divider * 10000000 == config["vco"]
