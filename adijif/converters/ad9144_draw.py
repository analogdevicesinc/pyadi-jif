"""Drawing features for AD9144."""

from typing import Dict

from adijif.draw import Layout, Node  # type: ignore # isort: skip  # noqa: I202


class ad9144_draw:
    """AD9144 drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for AD9144."""
        self.ic_diagram_node = None
        self._diagram_output_dividers = []

        name = self.name
        self.ic_diagram_node = Node(name)

        jesd204_deframer = Node("JESD204 Deframer", ntype="jesd204deframer")
        self.ic_diagram_node.add_child(jesd204_deframer)

        interp_node = Node("Interpolation", ntype="duc")
        self.ic_diagram_node.add_child(interp_node)
        self.ic_diagram_node.add_connection(
            {"from": jesd204_deframer, "to": interp_node}
        )

        # AD9144 has 4 DAC outputs, AD9152 has 2
        num_dacs = 2 if "9152" in name else 4
        for i in range(num_dacs):
            dac_node = Node(f"DAC{i}", ntype="dac")
            dac_node.shape = "parallelogram"
            self.ic_diagram_node.add_child(dac_node)
            self.ic_diagram_node.add_connection(
                {"from": interp_node, "to": dac_node}
            )

    def draw(
        self, clocks: Dict, lo: Layout = None, clock_chip_node: Node = None
    ) -> str:
        """Draw diagram in d2 language for AD9144/AD9152.

        Args:
            clocks (Dict): Dictionary of clocks
            lo (Layout): Layout object to add to. Defaults to None.
            clock_chip_node (Node): Node to connect to. Defaults to None.

        Returns:
            str: Diagram in d2 language
        """
        system_draw = lo is not None
        name = self.name
        num_dacs = 2 if "9152" in name else 4

        if not system_draw:
            lo = Layout(f"{name} Example")
            lo.show_rates = self.show_rates
        else:
            assert isinstance(lo, Layout), "lo must be a Layout object"
        lo.add_node(self.ic_diagram_node)

        # Find clock keys dynamically (handles both ad9144 and ad9152 naming)
        name_lower = name.lower()
        ref_clk_key = None
        sysref_key = None
        for key in clocks.keys():
            if key.lower().endswith(f"{name_lower}_ref_clk"):
                ref_clk_key = key
            if key.lower().endswith(f"{name_lower}_sysref"):
                sysref_key = key

        dac_clock = clocks[ref_clk_key]

        # Connect Remote Framer
        remote_framer = Node("JESD204 Framer", ntype="framer")
        lo.add_node(remote_framer)

        for _ in range(self.L):
            lane_rate = self.bit_clock
            lo.add_connection(
                {
                    "from": remote_framer,
                    "to": self.ic_diagram_node.get_child("JESD204 Deframer"),
                    "rate": lane_rate,
                }
            )

        # SYSREF
        if not system_draw:
            sysref_in = Node("SYSREF_IN", ntype="input")
            lo.add_connection(
                {
                    "from": sysref_in,
                    "to": self.ic_diagram_node.get_child("JESD204 Deframer"),
                    "rate": clocks[sysref_key],
                }
            )
        else:
            to_node = lo.get_node(sysref_key)
            from_node = lo.get_connection(to=to_node.name)
            assert from_node, "No connection found"
            assert isinstance(from_node, list), "Connection must be a list"
            assert len(from_node) == 1, "Only one connection allowed"
            sysref_in = from_node[0]["from"]
            lo.remove_node(to_node.name)

            lo.add_connection(
                {
                    "from": sysref_in,
                    "to": self.ic_diagram_node.get_child("JESD204 Deframer"),
                    "rate": clocks[sysref_key],
                }
            )

        # Update rates
        interp = self._interpolation
        sample_rate = dac_clock / interp if interp > 0 else dac_clock

        interp_node = self.ic_diagram_node.get_child("Interpolation")
        interp_node.value = str(interp)

        self.ic_diagram_node.update_connection(
            "JESD204 Deframer", "Interpolation", sample_rate
        )

        for i in range(num_dacs):
            self.ic_diagram_node.update_connection(
                "Interpolation", f"DAC{i}", dac_clock
            )

        # Connect ref clock to DACs
        if not system_draw:
            ref_in = Node("REF_IN", ntype="input")
            lo.add_node(ref_in)
        else:
            to_node = lo.get_node(ref_clk_key)
            from_node = lo.get_connection(to=to_node.name)
            assert from_node, "No connection found"
            assert isinstance(from_node, list), "Connection must be a list"
            assert len(from_node) == 1, "Only one connection allowed"
            ref_in = from_node[0]["from"]
            lo.remove_node(to_node.name)

        for i in range(num_dacs):
            dac_node = self.ic_diagram_node.get_child(f"DAC{i}")
            lo.add_connection(
                {"from": dac_node, "to": ref_in, "rate": dac_clock}
            )

        if not system_draw:
            return lo.draw()
