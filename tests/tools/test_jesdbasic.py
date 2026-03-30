"""Streamlit testing for Basic JESD204 Calculator page."""

import pathlib
import sys
import time

from streamlit.testing.v1 import AppTest

app_path = (
    pathlib.Path(__file__).parent.parent.parent
    / "adijif"
    / "tools"
    / "explorer"
)
app_file_path = app_path / "main.py"

sys.path.append(str(app_path))


def navigate_to_jesdbasic(at: AppTest) -> AppTest:
    """Navigate the sidebar to the Basic JESD204 Calculator page."""
    sb = at.sidebar
    for item in sb.radio:
        if item.label == "Select a Tool":
            item.set_value("Basic JESD204 Calculator").run()
            break
    time.sleep(0.5)
    return at


def test_jesdbasic_page_loads() -> None:
    """Test that the Basic JESD204 Calculator page loads without errors."""
    at = AppTest.from_file(app_file_path).run()
    navigate_to_jesdbasic(at)

    assert not at.exception
    assert len(at.title) > 0
    assert at.title[0].value == "Basic JESD204 Calculator"


def test_jesdbasic_default_inputs_present() -> None:
    """Test that default input widgets are present with expected defaults."""
    at = AppTest.from_file(app_file_path).run()
    navigate_to_jesdbasic(at)

    labels = {ni.label: ni for ni in at.number_input}
    assert "L (number of lanes)" in labels, "L input not found"
    assert "M (number of converters)" in labels, "M input not found"
    assert "Np (Bits per sample)" in labels, "Np input not found"

    assert labels["L (number of lanes)"].value == 4
    assert labels["M (number of converters)"].value == 4
    assert labels["Np (Bits per sample)"].value == 16

    assert not at.exception


def test_jesdbasic_jesd_class_selector() -> None:
    """Test that the JESD204 Class selector is present with correct options."""
    at = AppTest.from_file(app_file_path).run()
    navigate_to_jesdbasic(at)

    class_sel = None
    for sb in at.selectbox:
        if sb.label == "JESD204 Class":
            class_sel = sb
            break

    assert class_sel is not None, "JESD204 Class selectbox not found"
    assert "JESD204B" in class_sel.options
    assert "JESD204C" in class_sel.options
    assert class_sel.value == "JESD204B"

    assert not at.exception


def test_jesdbasic_clock_ref_sample_rate_mode() -> None:
    """Test that Sample Rate mode shows the Sample Rate input."""
    at = AppTest.from_file(app_file_path).run()
    navigate_to_jesdbasic(at)

    # Default mode is Sample Rate — verify the sample rate input is visible
    labels = [ni.label for ni in at.number_input]
    assert any("Sample Rate" in lbl for lbl in labels), (
        "Sample Rate input not found in default mode"
    )

    assert not at.exception


def test_jesdbasic_clock_ref_lane_rate_mode() -> None:
    """Test that switching to Lane Rate mode shows the Lane Rate input."""
    at = AppTest.from_file(app_file_path).run()
    navigate_to_jesdbasic(at)

    for sb in at.selectbox:
        if sb.label == "Clock Reference Source":
            sb.set_value("Lane Rate").run()
            break

    labels = [ni.label for ni in at.number_input]
    assert any("Lane Rate" in lbl for lbl in labels), (
        "Lane Rate input not found after switching Clock Reference Source"
    )

    assert not at.exception


def test_jesdbasic_output_table_present() -> None:
    """Test that the Derived Parameters table is rendered."""
    at = AppTest.from_file(app_file_path).run()
    navigate_to_jesdbasic(at)

    assert len(at.table) > 0, "Output table not found"

    # Table should contain Lane Rate and Core Clock rows
    table_df = at.table[0].value
    params = list(table_df["Parameter"])
    assert "Lane Rate (Gbps)" in params, (
        "Lane Rate row missing from output table"
    )
    assert "Core Clock (MHz)" in params, (
        "Core Clock row missing from output table"
    )

    assert not at.exception


def test_jesdbasic_lane_rate_calculation_sample_rate_mode() -> None:
    """Test lane rate calculation in Sample Rate mode with known values."""
    at = AppTest.from_file(app_file_path).run()
    navigate_to_jesdbasic(at)

    # Set known values: L=4, M=4, Np=16, Sample Rate=1e8 SPS, JESD204B
    # Expected lane rate = (4 * 16 * 1e8 * 10/8) / 4 / 1e9 = 2.0 Gbps
    for ni in at.number_input:
        if ni.label == "Sample Rate (SPS)":
            ni.set_value(1e8).run()
            break

    assert not at.exception
    table_df = at.table[0].value
    row = table_df[table_df["Parameter"] == "Lane Rate (Gbps)"]
    assert len(row) == 1
    assert abs(float(row["Value"].iloc[0]) - 2.0) < 1e-6


def test_jesdbasic_sample_rate_calculation_lane_rate_mode() -> None:
    """Test sample rate calculation in Lane Rate mode with known values."""
    at = AppTest.from_file(app_file_path).run()
    navigate_to_jesdbasic(at)

    for sb in at.selectbox:
        if sb.label == "Clock Reference Source":
            sb.set_value("Lane Rate").run()
            break

    # Set lane rate to 10 Gbps with defaults L=4, M=4, Np=16, JESD204B
    # Expected sample rate = (10e9 * 4) / (4 * 16 * 10/8) / 1e6 = 500 MSPS
    for ni in at.number_input:
        if ni.label == "Lane Rate (Gbps)":
            ni.set_value(10.0).run()
            break

    assert not at.exception
    table_df = at.table[0].value
    row = table_df[table_df["Parameter"] == "Sample Rate (MSPS)"]
    assert len(row) == 1
    assert abs(float(row["Value"].iloc[0]) - 500.0) < 1e-6


def test_jesdbasic_jesd204c_encoding() -> None:
    """Test that switching to JESD204C uses 66/64 encoding factor."""
    at = AppTest.from_file(app_file_path).run()
    navigate_to_jesdbasic(at)

    for sb in at.selectbox:
        if sb.label == "JESD204 Class":
            sb.set_value("JESD204C").run()
            break

    assert not at.exception

    # With L=4, M=4, Np=16, SR=1e8, JESD204C (66/64 encoding):
    # lane rate = (4 * 16 * 1e8 * 66/64) / 4 / 1e9 = 1.65625 Gbps
    for ni in at.number_input:
        if ni.label == "Sample Rate (SPS)":
            ni.set_value(1e8).run()
            break

    assert not at.exception
    table_df = at.table[0].value
    row = table_df[table_df["Parameter"] == "Lane Rate (Gbps)"]
    assert len(row) == 1
    expected = (4 * 16 * 1e8 * 66 / 64) / 4 / 1e9
    assert abs(float(row["Value"].iloc[0]) - expected) < 1e-6


def test_jesdbasic_core_clock_jesd204b() -> None:
    """Test core clock calculation for JESD204B."""
    at = AppTest.from_file(app_file_path).run()
    navigate_to_jesdbasic(at)

    for ni in at.number_input:
        if ni.label == "Sample Rate (SPS)":
            ni.set_value(1e8).run()
            break

    assert not at.exception

    # With lane rate = 2.0 Gbps, JESD204B core clock = 2.0 / 40 * 1e3 = 50 MHz
    table_df = at.table[0].value
    row = table_df[table_df["Parameter"] == "Core Clock (MHz)"]
    assert len(row) == 1
    assert abs(float(row["Value"].iloc[0]) - 50.0) < 1e-6


def test_jesdbasic_no_exception_on_param_changes() -> None:
    """Test that changing L, M, Np inputs produces no exceptions."""
    at = AppTest.from_file(app_file_path).run()
    navigate_to_jesdbasic(at)

    for label, value in [
        ("L (number of lanes)", 8),
        ("M (number of converters)", 2),
        ("Np (Bits per sample)", 12),
    ]:
        for ni in at.number_input:
            if ni.label == label:
                ni.set_value(value).run()
                assert not at.exception, (
                    f"Exception when setting {label}={value}"
                )
                break
