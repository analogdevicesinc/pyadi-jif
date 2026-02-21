"""Drawing features for LTC6953."""

from adijif.draw import Layout, Node


class ltc6953_draw:
    """LTC6953 drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for LTC6953."""
        self.ic_diagram_node = Node(self.name)

        # Distribution only: Ref -> Output Dividers

        out_divs = Node("Output Dividers", ntype="shell")
        self.ic_diagram_node.add_child(out_divs)

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

        # External Connections
        ref_in = Node("REF_IN", ntype="input")
        lo.add_node(ref_in)

        ref_rate = 0
        if hasattr(self, "input_ref") and isinstance(self.input_ref, (int, float)):
            ref_rate = self.input_ref

        out_divs = self.ic_diagram_node.get_child("Output Dividers")
        lo.add_connection({"from": ref_in, "to": out_divs, "rate": ref_rate})

        if system_draw:
            return lo.draw()

        return lo.draw()
