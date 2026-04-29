"""Streamlit testing for System Configurator page."""

import pathlib
import sys
import time

import pytest
from streamlit.testing.v1 import AppTest

import adijif
from adijif.clocks import supported_parts as _clock_parts
from adijif.converters import supported_parts as _converter_parts

app_path = (
    pathlib.Path(__file__).parent.parent.parent
    / "adijif"
    / "tools"
    / "explorer"
)
app_file_path = app_path / "main.py"

sys.path.append(str(app_path))

# Match the page's own filtering (see systemconfigurator.py:18) — these
# clock parts are deliberately hidden in the explorer UI.
_PAGE_HIDDEN_CLOCK_PARTS = {"ad9545", "ad9523_1"}
CLOCK_PARTS = [p for p in _clock_parts if p not in _PAGE_HIDDEN_CLOCK_PARTS]
CONVERTER_PARTS = list(_converter_parts)
FPGA_DEV_KITS = list(adijif.xilinx._available_dev_kit_names)

# AppTest's default 3s timeout is too tight for the System Configurator
# page when solve + d2 diagram rendering both run.
_APP_TIMEOUT = 30


def _new_app(timeout: int = _APP_TIMEOUT) -> AppTest:
    return AppTest.from_file(app_file_path, default_timeout=timeout).run()


def navigate_to_systemconfigurator(at: AppTest) -> AppTest:
    """Navigate the sidebar to the System Configurator page."""
    sb = at.sidebar
    for item in sb.radio:
        if item.label == "Select a Tool":
            item.set_value("System Configurator").run()
            break
    time.sleep(0.5)
    return at


def _set_selectbox(at: AppTest, key: str, value: str) -> None:
    """Set a selectbox by `key` to the given underlying value and re-run."""
    for sb in at.selectbox:
        if sb.key == key:
            sb.set_value(value).run()
            return
    raise AssertionError(f"Selectbox with key={key!r} not found")


def test_systemconfigurator_page_loads() -> None:
    at = _new_app()
    navigate_to_systemconfigurator(at)

    assert not at.exception
    assert len(at.title) > 0
    assert at.title[0].value == "System Configurator"


def test_systemconfigurator_infeasible_shows_st_error() -> None:
    """An infeasible config surfaces via st.error, not a raised exception."""
    at = _new_app()
    navigate_to_systemconfigurator(at)

    # Force an infeasible converter clock (well above the device max for
    # the default ad9680 converter, whose sample rate ceiling is ~1 GSPS).
    for ni in at.number_input:
        if ni.label and ni.label.startswith("Converter Clock"):
            ni.set_value(15000.0).run()  # 15 GHz in MHz units
            break

    # Solver failure should be surfaced as an st.error message, and must
    # NOT escape as a Python exception. The failure can come from either
    # `sys.initialize()` (clock chip) or `sys.do_solve()` (final solve).
    assert not at.exception, f"Unexpected exception: {at.exception}"
    expected_prefixes = (
        "Error solving system configuration",
        "Error initializing system",
    )
    assert any(
        any(prefix in e.value for prefix in expected_prefixes) for e in at.error
    ), (
        f"Expected one of {expected_prefixes!r} in st.error; "
        f"got: {[e.value for e in at.error]}"
    )


def test_systemconfigurator_display_bug_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Programming bugs in the display block must not be swallowed.

    Stub `system.do_solve` to return a malformed cfg dict missing the
    `"clock"` key. The page now reads cfg["clock"] outside the
    try/except, so a `KeyError` should surface as `at.exception`. If
    someone re-broadens the catch, this test fails.
    """

    def fake_do_solve(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return {"converter": {}, "fpga_AD9680": {}, "jesd_AD9680": {}}

    # `adijif.system` resolves to the class (re-exported in
    # adijif/__init__.py), not the module — patch `do_solve` directly on
    # it. The page calls `sys.initialize()` then `sys.do_solve()`; the
    # initialize step still runs normally and only the solve result is
    # replaced.
    monkeypatch.setattr(adijif.system, "do_solve", fake_do_solve)

    at = _new_app()
    navigate_to_systemconfigurator(at)

    # The default 1 GHz converter clock is infeasible at JESD204B for
    # ad9680's default mode (lane rate 20 Gbps), which trips
    # `sys.initialize()` and short-circuits the page before reaching
    # `do_solve`. Drop to a feasible clock so the patched `do_solve`
    # actually runs.
    for ni in at.number_input:
        if ni.label and ni.label.startswith("Converter Clock"):
            ni.set_value(500.0).run()
            break

    assert at.exception, (
        "Expected an exception to propagate from the display block, but "
        "none was recorded. The broad except may have been re-introduced "
        "around the cfg[...] reads."
    )
    # AppTest exposes the KeyError's args as `e.value` (e.g. `"'clock'"`).
    # The presence of "clock" is sufficient evidence the display block
    # raised on `cfg["clock"]` rather than the solver itself.
    assert any("clock" in str(e.value) for e in at.exception), (
        f"Expected 'clock' KeyError, got: "
        f"{[str(e.value) for e in at.exception]}"
    )


# ---------------------------------------------------------------------------
# Part-coverage smoke tests
#
# Each parametrized test selects a single component on the page and asserts
# that the page mounts without raising a Python exception. The solve may or
# may not succeed for a given combination — that's surfaced via st.error and
# is fine here. The point is that no part triggers a programming bug that
# crashes the page.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("part", CONVERTER_PARTS)
def test_systemconfigurator_loads_for_converter(part: str) -> None:
    at = _new_app()
    navigate_to_systemconfigurator(at)

    _set_selectbox(at, "converter_part_select", part)

    assert not at.exception, (
        f"Page raised with converter={part!r}: "
        f"{[str(e.value) for e in at.exception]}"
    )


@pytest.mark.parametrize("part", CLOCK_PARTS)
def test_systemconfigurator_loads_for_clock(part: str) -> None:
    at = _new_app()
    navigate_to_systemconfigurator(at)

    _set_selectbox(at, "clock_part_select", part)

    assert not at.exception, (
        f"Page raised with clock={part!r}: "
        f"{[str(e.value) for e in at.exception]}"
    )


@pytest.mark.parametrize("kit", FPGA_DEV_KITS)
def test_systemconfigurator_loads_for_fpga_kit(kit: str) -> None:
    at = _new_app()
    navigate_to_systemconfigurator(at)

    _set_selectbox(at, "fpga_dev_kit_select", kit)

    assert not at.exception, (
        f"Page raised with fpga_kit={kit!r}: "
        f"{[str(e.value) for e in at.exception]}"
    )
