"""Regression tests for solved-configuration cache invalidation."""

import pytest

import adijif


@pytest.mark.parametrize(
    "component,first,second",
    [
        (
            adijif.ltc6953,
            (1_000_000_000, [500_000_000], ["first"]),
            (1_000_000_000, [250_000_000], ["second"]),
        ),
        (
            adijif.adf4030,
            (125_000_000, [100_000_000], ["first"]),
            (125_000_000, [50_000_000], ["second"]),
        ),
    ],
)
def test_reconfiguration_invalidates_solved_config_cache(component, first, second):
    """A new request must make the prior solved configuration stale."""
    device = component(solver="CPLEX")
    device.set_requested_clocks(*first)
    device.solve()
    device.get_config()
    assert device._last_config is not None

    try:
        device.set_requested_clocks(*second)
    except Exception as ex:
        # Some standalone solver models cannot redefine named variables without
        # rebuilding the model. The stale cache must still be invalidated.
        assert "already exists in model" in str(ex)

    assert device._last_config is None
    with pytest.raises(Exception, match="No solution to draw"):
        device.draw()
