"""Regression tests for per-instance clock-chip runtime state."""

import pytest

from adijif.registry import get_component_class

CLOCKS = ["ad9523_1", "ad9528", "ad9545", "hmc7044", "ltc6952", "ltc6953"]


@pytest.mark.parametrize("name", CLOCKS)
def test_clock_private_mutable_state_is_instance_local(name):
    """Mutable divider selections and clock names must not leak across chips."""
    clock_class = get_component_class("clock", name)
    first = clock_class(solver="gekko")
    second = clock_class(solver="gekko")

    mutable_fields = {
        field
        for cls in type(first).mro()
        for field, value in vars(cls).items()
        if field.startswith("_")
        and not field.startswith("__")
        and isinstance(value, (list, dict, set))
    }

    for field in mutable_fields:
        first_value = getattr(first, field)
        second_value = getattr(second, field)
        assert first_value is not second_value, f"{name}.{field} is shared"

        before = (
            list(second_value)
            if isinstance(second_value, list)
            else second_value.copy()
        )
        if isinstance(first_value, list):
            first_value.append("ownership-probe")
        elif isinstance(first_value, dict):
            first_value["ownership-probe"] = True
        else:
            first_value.add("ownership-probe")
        assert second_value == before
