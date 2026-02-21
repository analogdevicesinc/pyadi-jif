"""Drawing features for AD9523."""

from typing import Dict

from adijif.draw import Layout, Node


class ad9523_draw:
    """AD9523 drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for AD9523."""
        self.ic_diagram_node = Node(self.name)

        # PLL2 Loop
        # VCXO (External usually, but input to PLL2) -> R2 -> PFD2
        r2_div = Node("R2", ntype="divider")
        pfd2 = Node("PFD2", ntype="phase-frequency-detector")
        lf2 = Node("LF2", ntype="filter")
        vco = Node("VCO", ntype="voltage-controlled-oscillator")
        vco.shape = "circle"
        n2_div = Node("N2", ntype="divider")

        m1_div = Node("M1", ntype="divider")  # VCO divider path 1

        self.ic_diagram_node.add_child(r2_div)
        self.ic_diagram_node.add_child(pfd2)
        self.ic_diagram_node.add_child(lf2)
        self.ic_diagram_node.add_child(vco)
        self.ic_diagram_node.add_child(n2_div)
        self.ic_diagram_node.add_child(m1_div)

        # Connections
        self.ic_diagram_node.add_connection({"from": r2_div, "to": pfd2})
        self.ic_diagram_node.add_connection({"from": pfd2, "to": lf2})
        self.ic_diagram_node.add_connection({"from": lf2, "to": vco})
        self.ic_diagram_node.add_connection({"from": vco, "to": n2_div})
        self.ic_diagram_node.add_connection({"from": n2_div, "to": pfd2})

        # Output Path
        self.ic_diagram_node.add_connection({"from": vco, "to": m1_div})

        # Output Dividers (Shell)
        out_divs = Node("Output Dividers", ntype="shell")
        self.ic_diagram_node.add_child(out_divs)
        self.ic_diagram_node.add_connection({"from": m1_div, "to": out_divs})

    def _update_diagram(self, config: Dict) -> None:
        """Update diagram with configuration.

        Args:
            config (Dict): Configuration dictionary
        """
        # Add output dividers dynamically based on usage
        keys = config.keys()
        # output_dividers = self.ic_diagram_node.get_child("Output Dividers")
        for key in keys:
            # Check if key format implies a divider (e.g., "d_clkname")
            # But usually update_diagram is called with specific keys like "D0", "D1"
            if key.startswith("d_"):
                # This logic depends on how set_requested_clocks names things.
                # In ad9523.py, it uses "d_" + clk_name.
                pass

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
        # Ref for PLL2 is usually VCXO
        ref_in = Node("VCXO_IN", ntype="input")
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

        # Add specific output dividers if they exist in config["out_dividers"]
        # In ad9523.py, config["out_dividers"] is a list of solver vars/vals.
        # And _clk_names stores names.
        if hasattr(self, "_clk_names"):
            out_divs_node = self.ic_diagram_node.get_child("Output Dividers")
            for _i, name in enumerate(self._clk_names):
                # We create a node for the divider
                div_node = Node(f"Div_{name}", ntype="divider")
                out_divs_node.add_child(div_node)
                self.ic_diagram_node.add_connection(
                    {"from": out_divs_node, "to": div_node}
                )

                # And a node for the output clock (external) if system_draw?
                # If system_draw, the 'to' node exists in 'lo'.
                if system_draw:
                    # connect div_node to external node
                    pass

        if system_draw:
            return lo.draw()

        return lo.draw()
