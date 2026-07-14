"""Diagram drawing for System level."""

import copy
from contextlib import contextmanager
from typing import Iterator

from adijif.draw import Layout, Node  # type: ignore # isort: skip  # noqa: I202


class system_draw:
    """Drawing features for system level models."""

    def _init_diagram(self) -> None:
        """Initialize diagram for system."""
        self.ic_diagram_node = None

        self.ic_diagram_node = Node("System")

    def _drawing_components(self) -> list:
        """Return components whose diagram state participates in a system render."""
        components = [self.clock, self.converter, self.fpga]
        for value in (self.plls, getattr(self, "plls_sysref", None)):
            if isinstance(value, list):
                components.extend(value)
            elif value is not None:
                components.append(value)
        for name in getattr(self.converter, "_nested", []) or []:
            components.append(getattr(self.converter, name))
        return components

    @contextmanager
    def _preserve_component_diagrams(self) -> Iterator[None]:
        """Keep rendering from changing reusable solved component state."""
        snapshots = []
        for component in self._drawing_components():
            state = {
                name: copy.deepcopy(value)
                for name, value in vars(component).items()
                if name == "ic_diagram_node" or name.startswith("_diagram_")
            }
            snapshots.append((component, state))
        try:
            yield
        finally:
            for component, state in snapshots:
                for name, value in state.items():
                    setattr(component, name, value)

    def draw(self, config: dict, theme: str = "dark") -> str:
        """Draw clocking model for system.

        Args:
            config (dict): Configuration to draw
            theme (str): JIF palette, either ``"light"`` or ``"dark"``.

        Returns:
            str: Drawn diagram
        """
        with self._preserve_component_diagrams():
            return self._draw(config, theme)

    def _draw(self, config: dict, theme: str) -> str:
        """Build one system diagram while public ``draw`` owns state cleanup."""
        lo = Layout("System Diagram", theme=theme)
        if hasattr(self, "use_d2_cli"):
            lo.use_d2_cli = self.use_d2_cli
        self._init_diagram()

        self.ic_diagram_node.add_child(lo)

        # Clocking
        assert self.clock is not None
        assert not isinstance(self.clock, list), "Only one clocking supported"

        self.clock.draw(lo)
        self.clock.ic_diagram_node.ntype = "jif-container-clock"

        # External PLLs (SYSREF and/or Direct)
        if self.plls is not None:
            if not isinstance(self.plls, list):
                plls = [self.plls]
            else:
                plls = self.plls

            for pll in plls:
                pll.draw(lo)
                pll.ic_diagram_node.ntype = "jif-container-clock"

        if hasattr(self, "plls_sysref") and self.plls_sysref is not None:
            if not isinstance(self.plls_sysref, list):
                plls_sysref = [self.plls_sysref]
            else:
                plls_sysref = self.plls_sysref

            for pll in plls_sysref:
                pll.draw(lo)
                pll.ic_diagram_node.ntype = "jif-container-clock"

        # Converter
        assert self.converter is not None
        assert not isinstance(self.converter, list), (
            "Only one converter supported"
        )

        cnv_clocking = config["clock"]["output_clocks"].copy()
        if "plls" in config:
            for pll_cfg in config["plls"]:
                if "output_clocks" in pll_cfg:
                    cnv_clocking.update(pll_cfg["output_clocks"])

        # Also grab output_clocks from any ext plls in config directly
        for key in config:
            if (
                "pll" in key
                and isinstance(config[key], dict)
                and "output_clocks" in config[key]
            ):
                cnv_clocking.update(config[key]["output_clocks"])

        for clk in cnv_clocking:
            rate = cnv_clocking[clk]["rate"]
            cnv_clocking[clk] = rate

        self.converter.draw(cnv_clocking, lo, self.clock.ic_diagram_node)
        self.converter.ic_diagram_node.ntype = "jif-container-converter"

        # FPGA
        assert self.fpga is not None
        assert not isinstance(self.fpga, list), "Only one FPGA supported"

        fpga_clocking = {
            "clocks": cnv_clocking,
            "fpga": config[f"fpga_{self.converter.name}"],
        }
        if not isinstance(self.converter, list):
            cnvers = [self.converter]
        self.fpga.draw(fpga_clocking, lo, cnvers)
        self.fpga.ic_diagram_node.ntype = "jif-container-fpga"

        # Draw the diagram
        return lo.draw()
