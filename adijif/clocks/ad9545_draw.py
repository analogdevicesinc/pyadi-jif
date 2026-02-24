"""Drawing features for AD9545."""

from adijif.draw import Layout, Node


class ad9545_draw:
    """AD9545 drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for AD9545."""
        self.ic_diagram_node = Node(self.name)

        # Inputs
        input_block = Node("Input Refs", ntype="shell")
        self.ic_diagram_node.add_child(input_block)

        # PLL0
        pll0 = Node("PLL0", ntype="pll")
        self.ic_diagram_node.add_child(pll0)

        # PLL1
        pll1 = Node("PLL1", ntype="pll")
        self.ic_diagram_node.add_child(pll1)

        # Outputs
        output_block = Node("Output Q Dividers", ntype="shell")
        self.ic_diagram_node.add_child(output_block)

        # Connections
        self.ic_diagram_node.add_connection({"from": input_block, "to": pll0})
        self.ic_diagram_node.add_connection({"from": input_block, "to": pll1})
        self.ic_diagram_node.add_connection({"from": pll0, "to": output_block})
        self.ic_diagram_node.add_connection({"from": pll1, "to": output_block})

    def draw(self, lo: Layout = None) -> str:
        """Draw diagram.

        Args:
            lo (Layout): Layout object to add to. Defaults to None.

        Returns:
            str: Diagram in d2 language
        """
        system_draw = lo is not None
        if not system_draw:
            lo = Layout(f"{self.name} Example")
            lo.show_rates = self.show_rates

        lo.add_node(self.ic_diagram_node)

        # Draw actual used inputs/outputs dynamically based on config would be ideal
        # But for now, basic structure.

        if system_draw:
            return lo.draw()

        return lo.draw()
