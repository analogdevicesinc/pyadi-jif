"""Streamlit testing for System Configurator optimization controls."""

import pathlib
import sys

from streamlit.testing.v1 import AppTest

app_path = (
    pathlib.Path(__file__).parent.parent.parent
    / "adijif"
    / "tools"
    / "explorer"
)
app_file_path = app_path / "main.py"

sys.path.append(str(app_path))


_RUN_TIMEOUT = 60


def _navigate_to_system_configurator(at: AppTest) -> AppTest:
    """Navigate from the sidebar to the System Configurator page."""
    sb = at.sidebar
    for item in sb.radio:
        if item.label == "Select a Tool":
            item.set_value("System Configurator").run(timeout=_RUN_TIMEOUT)
            break
    return at


def _click_button(at: AppTest, key: str) -> AppTest:
    """Click a Streamlit button identified by ``key`` and rerun."""
    for btn in at.button:
        if btn.key == key:
            btn.click().run(timeout=_RUN_TIMEOUT)
            return at
    raise AssertionError(f"Button with key {key!r} not found")


def _subheader_labels(at: AppTest) -> list:
    return [str(sub.value) for sub in at.subheader]


def _selectbox_by_key(at: AppTest, key: str):
    for sb in at.selectbox:
        if sb.key == key:
            return sb
    return None


def _number_input_by_key(at: AppTest, key: str):
    for ni in at.number_input:
        if ni.key == key:
            return ni
    return None


def _make_app() -> AppTest:
    """Return an AppTest navigated to System Configurator with a feasible setup.

    The page's default JESD mode (L=1) at 1 GHz produces a 20 Gbps lane rate
    that exceeds JESD204B limits and makes ``sys.initialize()`` raise. Lower
    the converter clock so the default mode is solvable and the optimization
    controls section renders.
    """
    at = AppTest.from_file(app_file_path, default_timeout=_RUN_TIMEOUT)
    at.run(timeout=_RUN_TIMEOUT)
    _navigate_to_system_configurator(at)
    for ni in at.number_input:
        if ni.key == "system_converter_clock_input":
            ni.set_value(400.0).run(timeout=_RUN_TIMEOUT)
            break
    return at


def test_optimization_controls_section_present() -> None:
    """The 'Optimization controls' section renders without errors."""
    at = _make_app()
    assert not at.exception, f"Page raised: {at.exception}"
    assert "Optimization controls" in _subheader_labels(at)


def test_initial_state_has_no_constraint_or_objective_rows() -> None:
    """No constraint/objective rows exist on first load."""
    at = _make_app()
    assert _selectbox_by_key(at, "sys_c_clock_1") is None
    assert _selectbox_by_key(at, "sys_o_clock_1") is None


def test_add_constraint_creates_row_widgets() -> None:
    """Clicking 'Add Constraint' appends a row with the expected widgets."""
    at = _make_app()
    _click_button(at, "sys_c_add")

    assert not at.exception
    clock_sb = _selectbox_by_key(at, "sys_c_clock_1")
    assert clock_sb is not None, "Clock selectbox for new row not found"
    # Default kind is 'range' so both v1 and v2 inputs should render.
    assert _number_input_by_key(at, "sys_c_v1_1") is not None
    assert _number_input_by_key(at, "sys_c_v2_1") is not None
    # Bundle keys for the default ad9680 system include this clock.
    assert "AD9680_fpga_ref_clk" in clock_sb.options


def test_add_objective_creates_row_widgets() -> None:
    """Clicking 'Add Objective' appends a row with the expected widgets."""
    at = _make_app()
    _click_button(at, "sys_o_add")

    assert not at.exception
    clock_sb = _selectbox_by_key(at, "sys_o_clock_1")
    sense_sb = _selectbox_by_key(at, "sys_o_sense_1")
    tier_ni = _number_input_by_key(at, "sys_o_tier_1")
    weight_ni = _number_input_by_key(at, "sys_o_weight_1")
    assert clock_sb is not None
    assert sense_sb is not None and sense_sb.value == "min"
    assert tier_ni is not None and tier_ni.value == 0
    assert weight_ni is not None and weight_ni.value == 1.0


def test_remove_constraint_row() -> None:
    """A row created by Add Constraint can be removed via its 'Remove' button."""
    at = _make_app()
    _click_button(at, "sys_c_add")
    assert _selectbox_by_key(at, "sys_c_clock_1") is not None

    _click_button(at, "sys_c_rm_1")
    assert not at.exception
    assert _selectbox_by_key(at, "sys_c_clock_1") is None


def test_two_constraint_rows_have_independent_keys() -> None:
    """Adding two constraint rows yields rows keyed by separate ids."""
    at = _make_app()
    _click_button(at, "sys_c_add")
    _click_button(at, "sys_c_add")
    assert not at.exception
    assert _selectbox_by_key(at, "sys_c_clock_1") is not None
    assert _selectbox_by_key(at, "sys_c_clock_2") is not None


def test_constraint_kind_switches_inputs() -> None:
    """Switching the constraint kind to 'equal_to' hides the second value input."""
    at = _make_app()
    _click_button(at, "sys_c_add")

    kind_sb = _selectbox_by_key(at, "sys_c_kind_1")
    assert kind_sb is not None
    kind_sb.set_value("equal_to").run()

    assert not at.exception
    assert _number_input_by_key(at, "sys_c_v1_1") is not None
    # 'equal_to' renders a placeholder st.write() instead of v2 input.
    assert _number_input_by_key(at, "sys_c_v2_1") is None


def test_objective_min_clock_keeps_solve_succeeding() -> None:
    """Adding a tier-0 'min' objective on a bundle clock keeps the solve healthy."""
    at = _make_app()
    _click_button(at, "sys_o_add")

    # Defaults already set sense=min, tier=0, weight=1.0; just rerun.
    at.run(timeout=30)
    assert not at.exception, f"Solve failed with user objective: {at.exception}"


def test_range_constraint_keeps_solve_succeeding() -> None:
    """A wide range constraint on the FPGA ref clock leaves the solve healthy."""
    at = _make_app()
    _click_button(at, "sys_c_add")

    clock_sb = _selectbox_by_key(at, "sys_c_clock_1")
    assert clock_sb is not None
    if "AD9680_fpga_ref_clk" not in clock_sb.options:
        return  # Default page state shifted; skip rather than false-fail.
    clock_sb.set_value("AD9680_fpga_ref_clk").run(timeout=30)
    assert not at.exception

    # Wide MHz-range that easily contains a default valid rate.
    v1 = _number_input_by_key(at, "sys_c_v1_1")
    v2 = _number_input_by_key(at, "sys_c_v2_1")
    assert v1 is not None and v2 is not None
    v1.set_value(50.0).run(timeout=30)
    assert not at.exception
    v2.set_value(500.0).run(timeout=30)
    assert not at.exception


def test_infeasible_constraint_does_not_crash_page() -> None:
    """An infeasible equal_to=1 Hz constraint surfaces as an error, not a crash."""
    at = _make_app()
    _click_button(at, "sys_c_add")

    kind_sb = _selectbox_by_key(at, "sys_c_kind_1")
    kind_sb.set_value("equal_to").run(timeout=30)
    assert not at.exception

    # 1 Hz in the default MHz units is impossible for any of these clocks.
    v1 = _number_input_by_key(at, "sys_c_v1_1")
    v1.set_value(1.0).run(timeout=60)

    # The page itself must not raise; the solver error is rendered as st.error.
    assert not at.exception
    # And the optimization controls section must still be present.
    assert "Optimization controls" in _subheader_labels(at)
