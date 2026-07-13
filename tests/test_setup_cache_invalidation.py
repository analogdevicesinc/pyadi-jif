"""Regression tests for low-level setup cache invalidation."""

import pytest

import adijif


@pytest.mark.parametrize(
    "component,configure,reset",
    [
        (
            adijif.ltc6953,
            lambda device: device.set_requested_clocks(
                1_000_000_000, [500_000_000], ["output"]
            ),
            lambda device: device.setup_constraints(1_000_000_000),
        ),
        (
            adijif.adf4030,
            lambda device: device.set_requested_clocks(
                125_000_000, [100_000_000], ["output"]
            ),
            lambda device: device.setup_constraints(125_000_000),
        ),
    ],
)
def test_setup_constraints_invalidates_solved_config_cache(
    component, configure, reset
):
    """Low-level setup must invalidate any prior solved drawing state."""
    device = component(solver="CPLEX")
    configure(device)
    device.solve()
    device.get_config()
    assert device._last_config is not None

    try:
        reset(device)
    except Exception as ex:
        # Reusing a standalone CPLEX model can reject duplicate variable names.
        assert "already exists in model" in str(ex)

    assert device._last_config is None
    with pytest.raises(Exception, match="No solution to draw"):
        device.draw()
