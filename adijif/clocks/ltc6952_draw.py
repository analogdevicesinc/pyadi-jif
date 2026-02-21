"""Drawing features for LTC6952."""

from adijif.draw import Layout, Node


class ltc6952_draw:
    """LTC6952 drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for LTC6952."""
        self.ic_diagram_node = Node(self.name)

        # Ref -> R2 -> PFD -> LF -> VCO -> N2 -> PFD
        r2_div = Node("R2", ntype="divider")
        pfd = Node("PFD", ntype="phase-frequency-detector")
        lf = Node("LF", ntype="filter")
        vco = Node("VCO", ntype="voltage-controlled-oscillator")
        vco.shape = "circle"
        n2_div = Node("N2", ntype="divider")

        self.ic_diagram_node.add_child(r2_div)
        self.ic_diagram_node.add_child(pfd)
        self.ic_diagram_node.add_child(lf)
        self.ic_diagram_node.add_child(vco)
        self.ic_diagram_node.add_child(n2_div)

        # Connections
        self.ic_diagram_node.add_connection({"from": r2_div, "to": pfd})
        self.ic_diagram_node.add_connection({"from": pfd, "to": lf})
        self.ic_diagram_node.add_connection({"from": lf, "to": vco})
        self.ic_diagram_node.add_connection({"from": vco, "to": n2_div})
        self.ic_diagram_node.add_connection({"from": n2_div, "to": pfd})

        # Output Dividers
        out_divs = Node("Output Dividers", ntype="shell")
        self.ic_diagram_node.add_child(out_divs)
        self.ic_diagram_node.add_connection({"from": vco, "to": out_divs})

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
        if hasattr(self, "vcxo") and isinstance(self.vcxo, (int, float)):
            ref_rate = self.vcxo

        lo.add_connection(
            {
                "from": ref_in,
                "to": self.ic_diagram_node.get_child("R2"),
                "rate": ref_rate,
            }
        )

        if system_draw:
            return lo.draw()

        return lo.draw()
