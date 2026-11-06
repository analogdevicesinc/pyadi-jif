"""Public automatic-planning API, independent of Streamlit."""

import pytest

import adijif.freqplan as fp


def test_public_solver_exports():
    """Python users can use the same planner as the UI through the package."""
    for name in (
        "RateDomain",
        "SignalTarget",
        "SolveRequest",
        "SolveResult",
        "solve_plan",
        "available_settings",
    ):
        assert hasattr(fp, name), name
        assert name in fp.__all__


@pytest.mark.parametrize("part", ["AD9144", "AD9152"])
def test_public_tx_optimization_preserves_plan_and_rf_position(part):
    """A real-only DAC chooses the lowest usable input rate on a small grid."""
    tx = fp.default_tx_plan(part)
    tx.datapath.enabled = [i == 0 for i in range(len(tx.datapath.enabled))]
    tx.dac_rate_hz = 1e9
    tx.datapath.factor = 1
    tx.signals = [fp.Signal("wanted", 90e6, 20e6, 0)]
    before = fp.dumps(None, tx)
    result = fp.solve_plan(
        fp.SolveRequest(
            tx=tx,
            targets=[fp.SignalTarget("tx", "wanted", "dac0", 90e6)],
            automatic={"tx.rate", "tx.factor"},
            rate_domains={"tx": fp.RateDomain(values_hz=(800e6, 1e9, 1.2e9))},
        )
    )
    assert result.status == "optimal", result.message
    assert fp.dumps(None, tx) == before
    assert result.tx.dac_rate_hz == 1e9
    assert result.tx.datapath.factor == 4
    stage = fp.compute_tx(result.tx).stages["dac0"]
    desired = [s for s in stage.spans if s.signal == "wanted" and not s.image]
    assert min(s.lo for s in desired) == pytest.approx(80e6)
    assert max(s.hi for s in desired) == pytest.approx(100e6)
