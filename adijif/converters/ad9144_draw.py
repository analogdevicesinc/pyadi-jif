"""Drawing features for AD9144."""

from typing import Dict

from adijif.draw import Layout, Node


class ad9144_draw:
    """AD9144 drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for AD9144."""
        self.ic_diagram_node = Node(self.name)

        # ---------------------------------------------------------------------
        # TX Path (DACs)
        # ---------------------------------------------------------------------
        # AD9144 is a Quad DAC
        num_dacs = 4

        tx_container = Node("TX Path", ntype="shell")
        self.ic_diagram_node.add_child(tx_container)

        # JESD204 Deframer
        deframer = Node("JESD204 Deframer", ntype="jesd204deframer")
        tx_container.add_child(deframer)

        # Interpolation Stages (Simplified as one block or split if desired)
        # For drawing, a single "Interpolation" block often suffices unless we know
        # stage details dynamically
        interpolation = Node("Interpolation", ntype="filter")
        tx_container.add_child(interpolation)

        # Crossbar (Inverse Mux) - Optional but good for visualizing routing
        mux = Node("Crossbar", ntype="crossbar")
        tx_container.add_child(mux)

        # DAC Cores
        for i in range(num_dacs):
            dac_node = Node(f"DAC{i}", ntype="dac")
            dac_node.shape = "parallelogram"
            tx_container.add_child(dac_node)

        # Connections
        # Deframer -> Interpolation
        tx_container.add_connection({"from": deframer, "to": interpolation})
        # Interpolation -> Mux
        tx_container.add_connection({"from": interpolation, "to": mux})
        # Mux -> DACs
        for i in range(num_dacs):
            tx_container.add_connection(
                {"from": mux, "to": tx_container.get_child(f"DAC{i}")}
            )

        # ---------------------------------------------------------------------
        # Clock Generation
        # ---------------------------------------------------------------------
        clk_gen = Node("Clock Gen", ntype="shell")
        self.ic_diagram_node.add_child(clk_gen)

        # Structure: Ref -> Div -> PFD -> VCO -> Out Div
        ref_div = Node("Ref Div", ntype="divider")
        clk_gen.add_child(ref_div)

        pfd = Node("PFD", ntype="phase-frequency-detector")
        clk_gen.add_child(pfd)

        vco = Node("VCO", ntype="voltage-controlled-oscillator")
        vco.shape = "circle"
        clk_gen.add_child(vco)

        # "BCount = floor( dac_clk/(2 * ref_clk/ref_div ) )"
        # This implies feedback N = 2 * BCount.

        feedback_div = Node("Feedback Div", ntype="divider")
        clk_gen.add_child(feedback_div)

        # Output divider (LO_DIV_MODE)
        out_div = Node("LO Div", ntype="divider")
        clk_gen.add_child(out_div)

        # Connections
        clk_gen.add_connection({"from": ref_div, "to": pfd})
        clk_gen.add_connection({"from": pfd, "to": vco})
        clk_gen.add_connection({"from": vco, "to": out_div})

        # Feedback path
        clk_gen.add_connection({"from": vco, "to": feedback_div})
        clk_gen.add_connection({"from": feedback_div, "to": pfd})

    def draw(
        self, clocks: Dict, lo: Layout = None, clock_chip_node: Node = None
    ) -> str:
        """Draw diagram.

        Args:
            clocks (Dict): Dictionary of clocks
            lo (Layout): Layout object to add to. Defaults to None.
            clock_chip_node (Node): Node to connect to. Defaults to None.

        Returns:
            str: Diagram in d2 language
        """
        system_draw = lo is not None
        if not system_draw:
            lo = Layout(f"{self.name} Example")
            lo.show_rates = self.show_rates

        lo.add_node(self.ic_diagram_node)

        # ---------------------------------------------------------------------
        # External Connections
        # ---------------------------------------------------------------------
        ref_clk_name = "ad9144_ref_clk"
        ref_rate = 0

        if not system_draw:
            ref_in = Node("REF_IN", ntype="input")
            lo.add_node(ref_in)
            ref_rate = clocks.get(ref_clk_name, 0)
        else:
            to_node = lo.get_node(ref_clk_name)
            if to_node:  # Should exist if created by system draw
                from_node_conn = lo.get_connection(to=to_node.name)
                if from_node_conn:
                    ref_in = from_node_conn[0]["from"]
                    ref_rate = clocks.get(ref_clk_name, 0)
                    lo.remove_node(to_node.name)
                else:
                    ref_in = Node("REF_IN", ntype="input")
                    lo.add_node(ref_in)
            else:
                ref_in = Node("REF_IN", ntype="input")
                lo.add_node(ref_in)

        # Connect Ref to Clock Gen
        clk_gen = self.ic_diagram_node.get_child("Clock Gen")
        lo.add_connection(
            {"from": ref_in, "to": clk_gen.get_child("Ref Div"), "rate": ref_rate}
        )

        # ---------------------------------------------------------------------
        # Update values if available
        # ---------------------------------------------------------------------
        # Try to update dividers based on config
        # config keys: ref_div_factor, BCount, lo_div_mode_p2

        if hasattr(self, "config"):
            # These might be solver variables, so formatted string or value
            pass

        if system_draw:
            return lo.draw()

        return lo.draw()
