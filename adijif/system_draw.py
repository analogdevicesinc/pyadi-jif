"""Diagram drawing for System level."""

from typing import Dict

from adijif.draw import Layout, Node  # type: ignore # isort: skip  # noqa: I202


class system_draw:
    """Drawing features for system level models."""

    def _init_diagram(self) -> None:
        """Initialize diagram for system."""
        self.ic_diagram_node = None

        self.ic_diagram_node = Node("System")

    def draw(self, config: Dict) -> str:
        """Draw clocking model for system.

        Args:
            config(Dict): System solution configuration

        Returns:
            str: Drawn diagram
        """
        lo = Layout("System Diagram")
        if hasattr(self, "use_d2_cli"):
            lo.use_d2_cli = self.use_d2_cli
        self._init_diagram()

        self.ic_diagram_node.add_child(lo)

        # Clocking
        assert self.clock is not None
        assert not isinstance(self.clock, list), "Only one clocking supported"

        self.clock.draw(lo)

        # Converter
        assert self.converter is not None
        assert not isinstance(self.converter, list), "Only one converter supported"

        cnv_clocking = config["clock"]["output_clocks"].copy()
        for clk in cnv_clocking:
            rate = cnv_clocking[clk]["rate"]
            cnv_clocking[clk] = rate

        self.converter.draw(cnv_clocking, lo, self.clock.ic_diagram_node)

        # FPGA
        assert self.fpga is not None
        assert not isinstance(self.fpga, list), "Only one FPGA supported"

        print(config)

        fpga_clocking = {
            "clocks": cnv_clocking,
            "fpga": config[f"fpga_{self.converter.name}"],
        }
        if not isinstance(self.converter, list):
            cnvers = [self.converter]
        self.fpga.draw(fpga_clocking, lo, cnvers)

        # Draw the diagram
        return lo.draw()
