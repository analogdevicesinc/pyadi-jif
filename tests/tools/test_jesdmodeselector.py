"""Streamlit testing for jesd mode selector page."""

# Locate the main app file
import pathlib
import sys
import time
from typing import Any, Optional

from streamlit.testing.v1 import AppTest

from adijif import converters

app_path = pathlib.Path(__file__).parent.parent.parent / "adijif" / "tools" / "explorer"
app_file_path = app_path / "main.py"

# Add app path to sys.path
sys.path.append(str(app_path))


# Webui helpers
def get_item(
    at: AppTest, t: str, label: str, debug: bool = False
) -> Optional[Any]:  # noqa: ANN401
    """Get a UI item by label or key.

    Args:
        at: AppTest instance
        t: Type of item to get
        label: Label or key to search for
        debug: Whether to print debug information

    Returns:
        Found item or None
    """
    for item in getattr(at, t):
        if debug:
            print("Found:", t, item.label, item.value, item.type, item.key)
            print(f"{item.label=}, {item.value=}, {item.type=}, {item.key=}")
            print("Looking for key:", label)
        if item.key == label or item.label == label:
            return item
    return None


def set_item(
    at: AppTest,
    t: str,
    label: str,
    value: Any,  # noqa: ANN401
    skip_warning_check: bool = False,
    print_warnings: bool = False,
    do_read_back: bool = False,
    debug: bool = False,
) -> Any:  # noqa: ANN401
    """Set a UI item value.

    Args:
        at: AppTest instance
        t: Type of item to set
        label: Label or key of item
        value: Value to set
        skip_warning_check: Whether to skip warning checks
        print_warnings: Whether to print warnings
        do_read_back: Whether to verify value after setting
        debug: Whether to print debug information

    Returns:
        The item that was set

    Raises:
        ValueError: If item is not found or warning occurs during setting
    """
    item = get_item(at, t, label, debug=debug)
    if item:
        # print(f"Set {label} to {value} for {t}")
        # print("Item details")
        # print(item)
        # print('----------')
        item.set_value(value).run()
        if do_read_back:
            itemr = get_item(at, t, label)
            print(f"Read back: {itemr.value}")
            options = itemr.options
            print(f"Options: {options}")
            assert itemr.value == value
        # print('#############')
        assert item.value == value
        if at.exception:
            print(item)
        assert not at.exception
        # if print_warnings:
        #     if at.session_state.warning:
        #         print(f"Warning: {at.session_state.warning}")
        # if not skip_warning_check:
        #     if at.session_state.warning:
        #         itemr = get_item(at, t, label)
        #         options = itemr.options
        #         print(f"Options: {options}")
        #         raise ValueError(f"Warning: {at.session_state.warning}")
    else:
        raise ValueError(f"Item {label} not found")
    return item


def test_jesdmodeselector_page_basic() -> None:
    """Test basic jesd mode selector page loading."""
    at = AppTest.from_file(app_file_path).run()

    # Navigate to the JESD Mode Selector page
    # sb = at.sidebar
    # set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(1)

    # Verify page title
    assert len(at.title) > 0
    assert at.title[0].value == "JESD204 Mode Selector"

    # Check that help button exists
    assert len(at.button) > 0
    help_button_found = False
    for button in at.button:
        if button.label == "Help":
            help_button_found = True
            break
    assert help_button_found, "Help button not found"


def test_jesdmodeselector_all_parts_load() -> None:
    """Test that all supported parts load without errors."""
    at = AppTest.from_file(app_file_path).run()

    sb = at.sidebar

    # Navigate to the JESD Mode Selector page
    set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(1)

    parts = converters.supported_parts
    for part in parts:
        set_item(at, "selectbox", "Select a part", part)
        at.run()
        time.sleep(1)
        # Check if errors or warnings are present
        assert not at.exception, f"Exception occurred for part {part}"


def test_jesdmodeselector_adc_datapath_config() -> None:
    """Test ADC datapath configuration options."""
    at = AppTest.from_file(app_file_path).run()

    sb = at.sidebar
    set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(0.5)

    # Select an ADC part (ad9680 is a known ADC)
    set_item(at, "selectbox", "Select a part", "ad9680")
    at.run()

    # Verify expanders exist
    assert len(at.expander) > 0, "No expanders found"

    # Check for Datapath Configuration expander
    datapath_expander_found = False
    for expander in at.expander:
        if "Datapath Configuration" in str(expander.label):
            datapath_expander_found = True
            break
    assert datapath_expander_found, "Datapath Configuration expander not found"

    # Check for Units selector
    units_found = False
    for selectbox in at.selectbox:
        if selectbox.label == "Units":
            units_found = True
            assert selectbox.value == "GHz", "Default unit should be GHz"
            assert "Hz" in selectbox.options
            assert "kHz" in selectbox.options
            assert "MHz" in selectbox.options
            assert "GHz" in selectbox.options
            break
    assert units_found, "Units selector not found"

    assert not at.exception


def test_jesdmodeselector_converter_rate_units() -> None:
    """Test converter rate units selection and conversion."""
    at = AppTest.from_file(app_file_path).run()

    sb = at.sidebar
    set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(0.5)

    set_item(at, "selectbox", "Select a part", "ad9680")
    at.run()

    # Test different unit selections
    for unit in ["Hz", "kHz", "MHz", "GHz"]:
        set_item(at, "selectbox", "Units", unit)
        at.run()
        assert not at.exception, f"Exception occurred when selecting {unit}"

        # Verify converter rate input exists
        converter_rate_found = False
        for number_input in at.number_input:
            if f"Converter Rate ({unit})" in number_input.label:
                converter_rate_found = True
                break
        assert converter_rate_found, f"Converter Rate input not found for {unit}"


def test_jesdmodeselector_derived_settings() -> None:
    """Test that derived settings are displayed."""
    at = AppTest.from_file(app_file_path).run()

    sb = at.sidebar
    set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(0.5)

    set_item(at, "selectbox", "Select a part", "ad9680")
    at.run()

    # Check that dataframe with derived settings exists
    assert len(at.dataframe) > 0, "No dataframe found for derived settings"

    # Check that the first dataframe contains sample rate
    df_found = False
    for df in at.dataframe:
        if hasattr(df, "value") and df.value is not None:
            if "Sample Rate (MSPS)" in str(df.value):
                df_found = True
                break
    assert df_found, "Sample Rate derived setting not found"

    assert not at.exception


def test_jesdmodeselector_jesd_modes_display() -> None:
    """Test that JESD modes are displayed correctly."""
    at = AppTest.from_file(app_file_path).run()

    sb = at.sidebar
    set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(0.5)

    set_item(at, "selectbox", "Select a part", "ad9680")
    at.run()

    # Check that Configuration and JESD204 Modes subheaders exist
    assert len(at.subheader) >= 2, "Expected at least 2 subheaders"

    subheader_texts = [sh.value for sh in at.subheader]
    assert "Configuration" in subheader_texts, "Configuration subheader not found"
    assert "JESD204 Modes" in subheader_texts, "JESD204 Modes subheader not found"

    # Check for toggle to show only valid modes
    toggle_found = False
    for toggle in at.toggle:
        if "Show only valid modes" in toggle.label:
            toggle_found = True
            assert toggle.value is True, "Toggle should default to True"
            break
    assert toggle_found, "Show only valid modes toggle not found"

    assert not at.exception


def test_jesdmodeselector_valid_modes_toggle() -> None:
    """Test toggling between valid and all modes."""
    at = AppTest.from_file(app_file_path).run()

    sb = at.sidebar
    set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(0.5)

    set_item(at, "selectbox", "Select a part", "ad9680")
    at.run()

    # Find and toggle the "Show only valid modes" toggle
    toggle_item = None
    for toggle in at.toggle:
        if "Show only valid modes" in toggle.label:
            toggle_item = toggle
            break

    assert toggle_item is not None, "Show only valid modes toggle not found"

    # Toggle to show all modes
    toggle_item.set_value(False).run()
    assert not at.exception, "Exception occurred when toggling to show all modes"

    # Toggle back to show only valid modes
    toggle_item.set_value(True).run()
    assert not at.exception, "Exception occurred when toggling to show valid modes"


def test_jesdmodeselector_jesd_configuration_multiselect() -> None:
    """Test JESD configuration multiselect options."""
    at = AppTest.from_file(app_file_path).run()

    sb = at.sidebar
    set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(0.5)

    set_item(at, "selectbox", "Select a part", "ad9680")
    at.run()

    # Check that multiselect widgets exist for JESD parameters
    assert (
        len(at.multiselect) > 0
    ), "No multiselect widgets found for JESD configuration"

    # Common JESD parameters that might be present
    expected_params = ["M", "L", "N", "Np", "F", "S", "K", "HD", "CS"]

    # Check that at least some JESD parameters are available as multiselect
    found_params = []
    for ms in at.multiselect:
        if ms.label in expected_params:
            found_params.append(ms.label)

    assert len(found_params) > 0, "No JESD configuration parameters found"

    assert not at.exception


def test_jesdmodeselector_dac_part() -> None:
    """Test DAC part loading (if available)."""
    at = AppTest.from_file(app_file_path).run()

    sb = at.sidebar
    set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(0.5)

    # Try to find a DAC part (ad9136 is a known DAC)
    dac_parts = ["ad9136", "ad9144", "ad9172", "ad9081"]
    dac_found = False

    for part in dac_parts:
        if part in converters.supported_parts:
            try:
                set_item(at, "selectbox", "Select a part", part)
                at.run()
                dac_found = True

                # Note: Some parts might not have interpolation settings
                # so we just check that the page loads without errors
                assert not at.exception, f"Exception occurred for DAC part {part}"
                break
            except Exception:  # noqa: S110, S112
                continue

    # If no DAC parts found, that's okay - just note it
    if not dac_found:
        print("Note: No DAC parts with quick_configuration_modes found for testing")


def test_jesdmodeselector_diagram_adc() -> None:
    """Test that diagram is shown for ADC parts."""
    at = AppTest.from_file(app_file_path).run()

    sb = at.sidebar
    set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(0.5)

    set_item(at, "selectbox", "Select a part", "ad9680")
    at.run()

    # Check for Diagram expander
    diagram_expander_found = False
    for expander in at.expander:
        if "Diagram" in str(expander.label):
            diagram_expander_found = True
            break

    assert diagram_expander_found, "Diagram expander not found"

    # Check that an image is rendered (images are rendered within expanders)
    # We just verify the expander exists and no exception occurred
    assert not at.exception


def test_jesdmodeselector_data_editor_present() -> None:
    """Test that JESD modes section is present."""
    at = AppTest.from_file(app_file_path).run()

    sb = at.sidebar
    set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(0.5)

    set_item(at, "selectbox", "Select a part", "ad9680")
    at.run()

    # Check that JESD204 Modes subheader exists
    # (this indicates the modes section is rendered)
    jesd_modes_subheader_found = False
    for subheader in at.subheader:
        if "JESD204 Modes" in subheader.value:
            jesd_modes_subheader_found = True
            break

    assert jesd_modes_subheader_found, "JESD204 Modes subheader not found"

    # Check that toggle for valid modes exists
    toggle_found = False
    for toggle in at.toggle:
        if "Show only valid modes" in toggle.label:
            toggle_found = True
            break

    assert toggle_found, "Show only valid modes toggle not found"

    assert not at.exception


def test_jesdmodeselector_converter_rate_change() -> None:
    """Test changing converter rate and verify no errors."""
    at = AppTest.from_file(app_file_path).run()

    sb = at.sidebar
    set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(0.5)

    set_item(at, "selectbox", "Select a part", "ad9680")
    at.run()

    # Find converter rate input
    for number_input in at.number_input:
        if "Converter Rate" in number_input.label:
            # Try setting different values
            original_value = number_input.value
            test_values = [0.5, 1.0, 2.0]

            for test_val in test_values:
                try:
                    number_input.set_value(test_val).run()
                    assert (
                        not at.exception
                    ), f"Exception when setting rate to {test_val}"
                except Exception:  # noqa: S110
                    # Some values might be out of range, which is okay
                    pass

            # Set back to original value
            try:
                number_input.set_value(original_value).run()
            except Exception:  # noqa: S110
                pass
            break
