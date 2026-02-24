"""Drawing features for AD9528."""

from adijif.draw import Layout, Node


class ad9528_draw:
    """AD9528 drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for AD9528."""
        self.ic_diagram_node = Node(self.name)

        # PLL2 Loop
        # VCXO -> R1 -> PFD2
        r1_div = Node("R1", ntype="divider")
        pfd2 = Node("PFD2", ntype="phase-frequency-detector")
        lf2 = Node("LF2", ntype="filter")
        vco = Node("VCO", ntype="voltage-controlled-oscillator")
        vco.shape = "circle"
        n2_div = Node("N2", ntype="divider")

        m1_div = Node("M1", ntype="divider")

        self.ic_diagram_node.add_child(r1_div)
        self.ic_diagram_node.add_child(pfd2)
        self.ic_diagram_node.add_child(lf2)
        self.ic_diagram_node.add_child(vco)
        self.ic_diagram_node.add_child(n2_div)
        self.ic_diagram_node.add_child(m1_div)

        # Connections
        self.ic_diagram_node.add_connection({"from": r1_div, "to": pfd2})
        self.ic_diagram_node.add_connection({"from": pfd2, "to": lf2})
        self.ic_diagram_node.add_connection({"from": lf2, "to": vco})
        self.ic_diagram_node.add_connection({"from": vco, "to": n2_div})
        self.ic_diagram_node.add_connection({"from": n2_div, "to": pfd2})

        # Output Path
        self.ic_diagram_node.add_connection({"from": vco, "to": m1_div})

        out_divs = Node("Output Dividers", ntype="shell")
        self.ic_diagram_node.add_child(out_divs)
        self.ic_diagram_node.add_connection({"from": m1_div, "to": out_divs})

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
        ref_in = Node("VCXO_IN", ntype="input")
        lo.add_node(ref_in)

        ref_rate = 0
        if hasattr(self, "vcxo") and isinstance(self.vcxo, (int, float)):
            ref_rate = self.vcxo

        lo.add_connection(
            {
                "from": ref_in,
                "to": self.ic_diagram_node.get_child("R1"),
                "rate": ref_rate,
            }
        )

        if system_draw:
            return lo.draw()

        return lo.draw()
