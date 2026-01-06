"""Page object for Clock Configurator tool."""

from .base_page import BasePage


class ClockConfiguratorPage(BasePage):
    """Page object for Clock Configurator.

    Provides methods to interact with Clock Configurator UI including
    clock chip selection, reference clock configuration, and solver.
    """

    def __init__(self, page, base_url, navigate: bool = True):
        """Initialize Clock Configurator page.

        Args:
            page: Playwright Page object
            base_url: Base URL of the app
            navigate: Whether to navigate to the tool (default True)
        """
        super().__init__(page, base_url)
        # BasePage.__init__ already waits for the app and sidebar to be ready
        if navigate:
            self.navigate_to_tool("Clock Configurator")

    def select_clock_part(self, part_name: str) -> None:
        """Select a clock chip part.

        Args:
            part_name: Name of the clock chip (e.g., "hmc7044")
        """
        self.set_selectbox("Select a part", part_name)

    def set_reference_clock(self, frequency: int) -> None:
        """Set reference clock frequency.

        Args:
            frequency: Frequency in Hz
        """
        self.set_number_input("Reference Clock", frequency)

    def is_no_solution_warning(self) -> bool:
        """Check if "No valid configuration found" warning is visible.

        Returns:
            bool: True if warning is visible
        """
        return self.is_visible("No valid configuration found")

    def is_internal_config_visible(self) -> bool:
        """Check if internal clock configuration section is visible.

        Returns:
            bool: True if section is visible
        """
        return self.is_visible("Internal Clock Configuration")

    def expand_internal_config(self) -> None:
        """Expand internal clock configuration section."""
        self.expand_expander("Internal Clock Configuration")

    def get_current_clock_part(self) -> str:
        """Get currently selected clock part.

        Returns:
            str: Name of the selected clock part
        """
        selectbox = self.page.locator('label:has-text("Select a part") + div')
        return selectbox.text_content().strip()

    def get_reference_clock_value(self) -> str:
        """Get current reference clock value.

        Returns:
            str: Current reference clock frequency value
        """
        return self.get_text_value("Reference Clock")

    def is_solution_displayed(self) -> bool:
        """Check if solution/results are displayed.

        Returns:
            bool: True if results section is visible
        """
        return self.is_visible("Solution") or self.is_visible("Configuration")

    def is_configuration_visible(self) -> bool:
        """Check if solution configuration is visible.

        Returns:
            bool: True if Found Configuration section is visible
        """
        return self.is_visible("Found Configuration")
