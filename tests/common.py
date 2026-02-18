# flake8: noqa
import shutil

import pytest

try:
    from gekko import GEKKO  # type: ignore
except ImportError:
    GEKKO = None

_CPLEX_AVAILABLE = shutil.which("cpoptimizer") is not None


def skip_solver(solver):
    if solver.lower() == "gekko" and GEKKO is None:
        pytest.skip("Gekko not available")
    if solver.upper() == "CPLEX" and not _CPLEX_AVAILABLE:
        pytest.skip("CPLEX solver executable not available")
