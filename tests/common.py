# flake8: noqa
import pytest

try:
    from gekko import GEKKO  # type: ignore
except ImportError:
    GEKKO = None


def skip_solver(solver):
    if solver.lower() == "gekko" and GEKKO is None:
        pytest.skip("Gekko not available")
