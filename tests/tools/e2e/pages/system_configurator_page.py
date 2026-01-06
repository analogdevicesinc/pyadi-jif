"""Page object for System Configurator tool."""

from .base_page import BasePage


class SystemConfiguratorPage(BasePage):
    """Page object for System Configurator.

    Provides methods to interact with System Configurator UI including
    component selection (converter, clock, FPGA) and system solver.
    """

    def __init__(self, page, base_url, navigate: bool = True):
        """Initialize System Configurator page.

        Args:
            page: Playwright Page object
            base_url: Base URL of the app
            navigate: Whether to navigate to the tool (default True)
        """
        super().__init__(page, base_url)
        # BasePage.__init__ already waits for the app and sidebar to be ready
        if navigate:
            self.navigate_to_tool("System Configurator")

    def select_converter(self, part_name: str) -> None:
        """Select a converter part.

        Args:
            part_name: Name of the converter (e.g., "ad9680")
        """
        self.set_selectbox("Select a converter part", part_name)

    def select_clock(self, part_name: str) -> None:
        """Select a clock chip part.

        Args:
            part_name: Name of the clock chip (e.g., "hmc7044")
        """
        self.set_selectbox("Select a clock part", part_name)

    def select_fpga_kit(self, kit_name: str) -> None:
        """Select an FPGA development kit.

        Args:
            kit_name: Name of the FPGA kit (e.g., "zc706")
        """
        self.set_selectbox("Select an FPGA development kit", kit_name)

    def expand_converter_settings(self) -> None:
        """Expand converter settings section."""
        self.expand_expander("Converter Settings")

    def expand_fpga_settings(self) -> None:
        """Expand FPGA settings section."""
        self.expand_expander("FPGA Settings")

    def expand_clocking_settings(self) -> None:
        """Expand clocking settings section."""
        self.expand_expander("Clocking Settings")

    def is_converter_settings_visible(self) -> bool:
        """Check if converter settings section is visible.

        Returns:
            bool: True if section is visible
        """
        return self.is_visible("Converter Settings")

    def is_fpga_settings_visible(self) -> bool:
        """Check if FPGA settings section is visible.

        Returns:
            bool: True if section is visible
        """
        return self.is_visible("FPGA Settings")

    def is_system_configuration_visible(self) -> bool:
        """Check if system configuration section is visible.

        Returns:
            bool: True if System Configuration expander is visible
        """
        return self.is_visible("System Configuration")
