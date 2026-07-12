"""Regression tests for per-instance PLL selection ownership."""

import pytest

from adijif.registry import get_component_class

SETTER_CASES = [
    ("adf4030", "r", [1, 2]),
    ("adf4030", "n", [8, 9]),
    ("adf4030", "o", [10, 11]),
    ("adf4371", "d", [0, 1]),
    ("adf4371", "r", [1, 2]),
    ("adf4371", "t", [0, 1]),
    ("adf4371", "rf_div", [1, 2]),
    ("adf4371", "mode", ["integer", "fractional"]),
    ("adf4382", "d", [1, 2]),
    ("adf4382", "r", [1, 2]),
    ("adf4382", "o", [1, 2]),
    ("adf4382", "n", [4, 5]),
    ("adf4382", "mode", ["integer", "fractional"]),
    ("adf4382", "EFM3_MODE", [0, 4]),
]


@pytest.mark.parametrize("name,attribute,selection", SETTER_CASES)
def test_pll_setters_copy_mutable_selections(name, attribute, selection):
    """A caller mutation must not alter a configured PLL selection."""
    pll = get_component_class("pll", name)(solver="CPLEX")
    expected = list(selection)

    setattr(pll, attribute, selection)
    selection.clear()

    assert getattr(pll, attribute) == expected


@pytest.mark.parametrize("name", ["adf4030", "adf4371", "adf4382"])
def test_pll_instances_isolate_private_mutable_defaults(name):
    """Each PLL instance must own its mutable runtime defaults."""
    pll_type = get_component_class("pll", name)
    first = pll_type(solver="CPLEX")
    second = pll_type(solver="CPLEX")

    mutable_fields = {
        field
        for cls in pll_type.__mro__
        for field, value in vars(cls).items()
        if field.startswith("_")
        and not field.startswith("__")
        and isinstance(value, (list, dict, set))
    }

    for field in mutable_fields:
        assert getattr(first, field) is not getattr(second, field), field
