"""Pytest fixtures/options for pyadi-jif hardware-in-the-loop tests.

Mirrors the adi-labgrid-plugins convention: hardware tests are gated behind
``--run-hardware`` and target a labgrid coordinator. Each per-board test asks
for the ``dut`` fixture via an indirect ``place`` parameter; the fixture
resolves the place's booted address from the coordinator and opens SSH,
skipping cleanly when the board is unreachable (e.g. powered off).

Local invocation::

    pytest --run-hardware tests/hardware/ -v
    pytest --run-hardware --lg-coordinator 10.0.0.41:20408 \
        tests/hardware/test_hw_nuc_fmcdaq3.py -v
"""

from __future__ import annotations

import pytest

from .dut import DUT, coordinator_place_address


def pytest_addoption(parser):
    group = parser.getgroup("pyadi-jif-hardware")
    group.addoption(
        "--run-hardware",
        action="store_true",
        default=False,
        help="Run tests that require real hardware on the labgrid coordinator.",
    )
    group.addoption(
        "--lg-coordinator",
        action="store",
        default="10.0.0.41:20408",
        help="labgrid coordinator host:port advertising the DUT places.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "hardware: mark test as requiring real hardware (labgrid)"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-hardware"):
        return
    skip_hw = pytest.mark.skip(reason="need --run-hardware option to run")
    for item in items:
        # Use the marker (not item.keywords, which also contains the directory
        # name "hardware" and would skip every test under tests/hardware/).
        if item.get_closest_marker("hardware") is not None:
            item.add_marker(skip_hw)


@pytest.fixture
def coordinator(request) -> str:
    """The labgrid coordinator host:port under test."""
    return request.config.getoption("--lg-coordinator")


@pytest.fixture
def dut(request, coordinator) -> DUT:
    """Resolve and connect to a booted DUT for the requested ``place``.

    Parametrize indirectly::

        @pytest.mark.parametrize("dut", ["nemo"], indirect=True)

    Skips when the place address cannot be resolved or SSH fails (board down).
    """
    place = getattr(request, "param", None)
    if place is None:
        pytest.fail("dut fixture requires an indirect 'place' parameter")

    address = coordinator_place_address(place, coordinator)
    if not address:
        pytest.skip(
            f"could not resolve NetworkService address for place '{place}' "
            f"on coordinator {coordinator}"
        )

    handle = DUT(address)
    try:
        handle.connect()
    except Exception as exc:  # noqa: BLE001 - any SSH failure means board is down
        pytest.skip(
            f"DUT '{place}' at {address} unreachable ({exc!r}); "
            "board likely powered off / not booted"
        )

    yield handle
    handle.close()
