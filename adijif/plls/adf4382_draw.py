"""Drawing features for ADF4382."""

from adijif.draw import Layout, Node


class adf4382_draw:
    """ADF4382 drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for ADF4382."""
        self.ic_diagram_node = Node(self.name)

        # Structure: Ref -> D (Doubler) -> R -> PFD
        d_doubler = Node("D (Doubler)", ntype="doubler")
        r_div = Node("R Divider", ntype="divider")
        pfd = Node("PFD", ntype="phase-frequency-detector")

        self.ic_diagram_node.add_child(d_doubler)
        self.ic_diagram_node.add_child(r_div)
        self.ic_diagram_node.add_child(pfd)

        lf = Node("Loop Filter", ntype="filter")
        vco = Node("VCO", ntype="voltage-controlled-oscillator")
        vco.shape = "circle"

        self.ic_diagram_node.add_child(lf)
        self.ic_diagram_node.add_child(vco)

        # Output: O Divider
        o_div = Node("O Divider", ntype="divider")
        self.ic_diagram_node.add_child(o_div)

        # Feedback: N Divider
        n_div = Node("N Divider", ntype="divider")
        self.ic_diagram_node.add_child(n_div)

        # Connections
        self.ic_diagram_node.add_connection({"from": d_doubler, "to": r_div})
        self.ic_diagram_node.add_connection({"from": r_div, "to": pfd})
        self.ic_diagram_node.add_connection({"from": pfd, "to": lf})
        self.ic_diagram_node.add_connection({"from": lf, "to": vco})
        self.ic_diagram_node.add_connection({"from": vco, "to": o_div})

        # Feedback
        self.ic_diagram_node.add_connection({"from": vco, "to": n_div})
        self.ic_diagram_node.add_connection({"from": n_div, "to": pfd})

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

        lo.add_connection(
            {
                "from": ref_in,
                "to": self.ic_diagram_node.get_child("D (Doubler)"),
                "rate": ref_rate,
            }
        )

        if system_draw:
            return lo.draw()

        return lo.draw()
