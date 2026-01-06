"""Page object for JESD204 Mode Selector tool."""

from .base_page import BasePage


class JESDModeSelectorPage(BasePage):
    """Page object for JESD204 Mode Selector.

    Provides methods to interact with the JESD Mode Selector UI including
    part selection, converter rate configuration, and mode filtering.
    """

    def __init__(self, page, base_url, navigate: bool = True):
        """Initialize JESD Mode Selector page.

        Args:
            page: Playwright Page object
            base_url: Base URL of the app
            navigate: Whether to navigate to the tool (default True)
        """
        super().__init__(page, base_url)
        # BasePage.__init__ already waits for the app and sidebar to be ready
        if navigate:
            self.navigate_to_tool("JESD204 Mode Selector")

    def select_part(self, part_name: str) -> None:
        """Select a converter part.

        Args:
            part_name: Name of the part to select (e.g., "ad9680")
        """
        self.set_selectbox("Select a part", part_name)

    def set_converter_rate(self, rate: float, units: str = "GHz") -> None:
        """Set converter sample rate.

        Args:
            rate: Rate value
            units: Units for rate (Hz, kHz, MHz, GHz)
        """
        self.select_units(units)
        self.set_number_input(f"Converter Rate ({units})", rate)

    def select_units(self, units: str) -> None:
        """Select rate units.

        Args:
            units: Units to select (Hz, kHz, MHz, GHz)
        """
        self.set_selectbox("Units", units)

    def toggle_valid_modes_only(self, enabled: bool) -> None:
        """Toggle "Show only valid modes" filter.

        Args:
            enabled: Whether to enable the filter
        """
        self.toggle_checkbox("Show only valid modes", enabled)

    def is_help_button_visible(self) -> bool:
        """Check if Help button is visible.

        Returns:
            bool: True if Help button is visible
        """
        return self.page.get_by_role("button", name="Help").is_visible()

    def get_datapath_config(self) -> bool:
        """Check if datapath configuration section is visible.

        Returns:
            bool: True if datapath configuration is visible
        """
        return self.is_visible("Datapath Configuration")

    def is_diagram_visible(self) -> bool:
        """Check if diagram is visible.

        Returns:
            bool: True if diagram image is visible
        """
        # Look for stImage in the main content area, not the sidebar
        # (sidebar also has images, causing strict mode violations)
        main_content = self.page.locator('[data-testid="stMainBlockContainer"]')
        return main_content.locator('[data-testid="stImage"]').is_visible()

    def get_current_part(self) -> str:
        """Get currently selected part.

        Returns:
            str: Name of the selected part
        """
        # Find the selectbox and get the selected value from the combobox display
        label_elem = self.page.locator('label:has-text("Select a part")')
        selectbox = label_elem.locator("..")
        # The combobox's first div child shows the selected value
        selected_value = selectbox.locator(
            '[role="combobox"] + div, [role="combobox"] > div'
        ).first
        try:
            text = selected_value.text_content().strip()
            # Remove any extra text like "open" and convert to lowercase
            text = text.replace("open", "").strip()
            return text.lower()
        except Exception:
            return ""

    def get_current_units(self) -> str:
        """Get currently selected rate units.

        Returns:
            str: Current units (Hz, kHz, MHz, GHz)
        """
        selectbox = self.page.locator('label:has-text("Units") + div')
        return selectbox.text_content().strip()
