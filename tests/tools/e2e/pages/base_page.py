"""Base page object for Streamlit apps."""

from playwright.sync_api import Locator, Page


class BasePage:
    """Base page with common Streamlit interactions.

    Provides common methods for interacting with Streamlit UI elements
    including selectboxes, number inputs, buttons, and expanders.
    """

    def __init__(self, page: Page, base_url: str):
        """Initialize page object.

        Args:
            page: Playwright Page object
            base_url: Base URL of the Streamlit app
        """
        self.page = page
        self.base_url = base_url
        self.page.goto(base_url)
        self.wait_for_streamlit_ready()

    def navigate_to_tool(self, tool_name: str) -> None:
        """Navigate via sidebar radio button.

        Args:
            tool_name: Display name of the tool to navigate to
        """
        # Wait for sidebar content to be rendered
        self.page.wait_for_selector(
            '[data-testid="stSidebarUserContent"]', state="visible", timeout=15000
        )

        # Find the radio button in the sidebar with the tool name
        sidebar_content = self.page.locator('[data-testid="stSidebarUserContent"]')
        radio_button = sidebar_content.locator(f"label:has-text({tool_name!r})")

        # Wait for the radio button to be visible and clickable
        radio_button.wait_for(state="visible", timeout=10000)
        radio_button.click()
        self.wait_for_streamlit_ready()

    def wait_for_streamlit_ready(self, timeout: int = 15000) -> None:
        """Wait for Streamlit to finish rendering.

        Args:
            timeout: Maximum time to wait (milliseconds) - extended to 15s
        """
        # Wait for stApp to be visible
        self.page.wait_for_selector(
            '[data-testid="stApp"]', state="visible", timeout=timeout
        )

        # Streamlit needs to fully render all content via React/JavaScript
        # Try to wait for sidebar content using primary selector, then fallback
        try:
            self.page.wait_for_selector(
                '[data-testid="stSidebarUserContent"]', state="visible", timeout=timeout
            )
        except TimeoutError:
            # Fallback: wait for complementary role (sidebar container)
            self.page.wait_for_selector(
                '[role="complementary"]', state="visible", timeout=timeout
            )

        # Wait for loading spinners to disappear (if any exist)
        try:
            self.page.wait_for_function(
                "() => document.querySelectorAll('[data-testid=\"stSpinner\"]')"
                ".length === 0",
                timeout=5000,
            )
        except TimeoutError:
            # Continue even if spinners don't disappear
            pass

        # Wait a bit longer for dynamic content to render
        # This helps with pages that update after selectbox changes
        self.page.wait_for_timeout(500)

    def get_selectbox(self, label: str) -> Locator:
        """Get selectbox by label.

        Args:
            label: Text label of the selectbox

        Returns:
            Locator: Playwright locator for the selectbox
        """
        # Streamlit selectbox structure: label -> parent -> div with button
        return (
            self.page.locator(f"label:has-text({label!r})")
            .locator("..")
            .locator("button")
        )

    def set_selectbox(self, label: str, value: str) -> None:
        """Set selectbox value.

        Args:
            label: Text label of the selectbox
            value: Value to select

        Raises:
            ValueError: If dropdown cannot be opened or option not found
        """
        # Find the label and locate the combobox in the parent container
        label_elem = self.page.locator(f"label:has-text({label!r})")
        label_elem.wait_for(state="visible", timeout=10000)

        # Streamlit uses Baseweb combobox (role="combobox"), not button
        selectbox_container = label_elem.locator("..")
        combobox = selectbox_container.locator('[role="combobox"]')
        combobox.wait_for(state="visible", timeout=10000)

        # Click combobox to open dropdown
        # First ensure it's in focus
        combobox.focus()
        self.page.wait_for_timeout(50)

        # Try clicking
        combobox.click()

        # Wait a moment for the click to be processed
        self.page.wait_for_timeout(100)

        # If click doesn't work, try keyboard (Space or Enter)
        # First check if dropdown opened
        initial_expanded = combobox.get_attribute("aria-expanded")
        if initial_expanded == "false":
            # Try keyboard navigation
            combobox.press("ArrowDown")
            self.page.wait_for_timeout(100)

        # Wait for dropdown to appear - check for options being rendered
        # or aria-expanded
        try:
            self.page.wait_for_function(
                "() => document.querySelectorAll('[role=\"option\"]')" ".length > 0",
                timeout=5000,
            )
        except Exception:
            # If options don't appear, try checking if the combobox opened
            # with aria-expanded
            try:
                self.page.wait_for_function(
                    "() => document.querySelector("
                    '\'[role="combobox"][aria-expanded="true"]\') !== null',
                    timeout=5000,
                )
            except Exception as err:
                # Last resort: take a screenshot and list what we can find
                all_comboboxes = self.page.locator('[role="combobox"]')
                print(f"Found {all_comboboxes.count()} comboboxes")
                for i in range(all_comboboxes.count()):
                    elem = all_comboboxes.nth(i)
                    expanded = elem.get_attribute("aria-expanded")
                    print(f"  Combobox {i}: aria-expanded={expanded}")
                msg = f"Dropdown did not open for {label!r}"
                raise ValueError(msg) from err

        # Get all options - they might use different text than the value parameter
        all_options = self.page.locator('[role="option"]')
        option_count = all_options.count()

        if option_count == 0:
            raise ValueError(f"No options found in dropdown for {label!r}")

        # Log available options for debugging
        available_options = []
        for i in range(min(option_count, 10)):  # Log first 10 options
            opt_text = all_options.nth(i).text_content()
            available_options.append(opt_text)

        print(f"Available options for {label!r}: {available_options}")

        # Click the option by text
        # The dropdown options have role="option"
        # Try exact match first
        dropdown_option = self.page.locator(f'[role="option"]:has-text({value!r})')

        if dropdown_option.count() > 0:
            # Option found with exact match
            dropdown_option.first.click()
        else:
            # Try case-insensitive search
            dropdown_option = self.page.locator(f'[role="option"] >> text=/{value}/i')
            if dropdown_option.count() > 0:
                dropdown_option.first.click()
            else:
                # Try looking for the uppercased version (common with format_func)
                upper_value = value.upper().replace("_", "-")
                dropdown_option = self.page.locator(
                    f'[role="option"]:has-text({upper_value!r})'
                )
                if dropdown_option.count() > 0:
                    dropdown_option.first.click()
                else:
                    msg = (
                        f"Option {value!r} not found in dropdown "
                        f"(available: {available_options})"
                    )
                    raise ValueError(msg)

        # Wait for dropdown to close
        self.page.wait_for_function(
            "() => document.querySelectorAll('[role=\"listbox\"]').length === 0",
            timeout=5000,
        )
        self.wait_for_streamlit_ready()

    def set_number_input(self, label: str, value: float) -> None:
        """Set number input value.

        Args:
            label: Text label of the number input
            value: Value to enter
        """
        # Find the label and locate the input within the parent
        label_elem = self.page.locator(f"label:has-text({label!r})")
        label_elem.wait_for(state="visible", timeout=10000)

        # Find input field - could be direct sibling or within parent
        input_field = label_elem.locator('//following::input[@type="number"]').first
        if not input_field.is_visible():
            input_field = label_elem.locator("..").locator('input[type="number"]')

        input_field.wait_for(state="visible", timeout=10000)
        input_field.fill(str(value))
        input_field.blur()
        self.wait_for_streamlit_ready()

    def click_button(self, label: str) -> None:
        """Click button by label.

        Args:
            label: Text label of the button
        """
        button = self.page.get_by_role("button", name=label)
        button.wait_for(state="visible", timeout=10000)
        button.click()
        self.wait_for_streamlit_ready()

    def expand_expander(self, label: str) -> None:
        """Expand expander if not already expanded.

        Args:
            label: Text label of the expander
        """
        # Try to find expander by label
        expander = self.page.locator(f"summary:has-text({label!r})")
        expander.wait_for(state="visible", timeout=10000)

        # Check if parent details is already open
        parent = expander.locator("..")
        is_open = parent.evaluate("el => el.open")

        if not is_open:
            expander.click()
            # Wait for details element to open - check if it has 'open' attribute
            self.page.wait_for_function(
                "() => document.querySelector('details[open]') !== null", timeout=5000
            )

    def take_screenshot(self, name: str, full_page: bool = True) -> bytes:
        """Take screenshot.

        Args:
            name: Name for reference (not used for file saving)
            full_page: Whether to capture full page or viewport

        Returns:
            bytes: Screenshot data
        """
        return self.page.screenshot(full_page=full_page)

    def is_visible(self, text: str) -> bool:
        """Check if text is visible on page.

        Args:
            text: Text to search for

        Returns:
            bool: True if text is visible
        """
        try:
            # Use first() to avoid strict mode violation with multiple matches
            elem = self.page.get_by_text(text).first
            return elem.is_visible()
        except (TimeoutError, AttributeError):
            # Element not found or not visible
            return False

    def get_text_value(self, label: str) -> str:
        """Get text value from input field.

        Args:
            label: Label of the input field

        Returns:
            str: Current value in the input field
        """
        label_elem = self.page.locator(f"label:has-text({label!r})")
        label_elem.wait_for(state="visible", timeout=10000)

        # Find input field within parent container
        input_field = label_elem.locator("..").locator('input[type="number"]')
        input_field.wait_for(state="visible", timeout=10000)
        return input_field.input_value()

    def toggle_checkbox(self, label: str, enabled: bool) -> None:
        """Toggle checkbox state.

        Args:
            label: Text label of the checkbox
            enabled: Whether checkbox should be enabled
        """
        # Find checkbox near the label
        label_elem = self.page.locator(f"label:has-text({label!r})")
        label_elem.wait_for(state="visible", timeout=10000)

        # Checkbox might be before or after the label
        checkbox = label_elem.locator("..").locator('input[type="checkbox"]')
        if not checkbox.count() > 0:
            checkbox = label_elem.locator('input[type="checkbox"]')

        # Don't wait for checkbox to be visible - Streamlit hides native checkboxes
        # Just click the label which is the visible control
        current_state = checkbox.is_checked()

        if current_state != enabled:
            # Click the label to toggle the checkbox
            label_elem.click()
            self.wait_for_streamlit_ready()
