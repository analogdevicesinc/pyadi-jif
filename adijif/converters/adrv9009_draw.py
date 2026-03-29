"""Drawing features for ADRV9009."""

from typing import Dict

from adijif.draw import Layout, Node  # type: ignore # isort: skip  # noqa: I202


class adrv9009_rx_draw:
    """ADRV9009 RX drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for ADRV9009 RX."""
        self.ic_diagram_node = None
        self._diagram_output_dividers = []

        name = self.name
        self.ic_diagram_node = Node(name)

        adc_node = Node("ADC", ntype="adc")
        adc_node.shape = "parallelogram"
        self.ic_diagram_node.add_child(adc_node)

        dec_filter = Node("Decimation Filter", ntype="ddc")
        self.ic_diagram_node.add_child(dec_filter)
        self.ic_diagram_node.add_connection(
            {"from": adc_node, "to": dec_filter}
        )

        jesd204_framer = Node("JESD204 Framer", ntype="jesd204framer")
        self.ic_diagram_node.add_child(jesd204_framer)
        self.ic_diagram_node.add_connection(
            {"from": dec_filter, "to": jesd204_framer}
        )

    def draw(
        self, clocks: Dict, lo: Layout = None, clock_chip_node: Node = None
    ) -> str:
        """Draw diagram in d2 language for ADRV9009 RX.

        Args:
            clocks (Dict): Dictionary of clocks
            lo (Layout): Layout object to add to. Defaults to None.
            clock_chip_node (Node): Node to connect to. Defaults to None.

        Returns:
            str: Diagram in d2 language
        """
        system_draw = lo is not None
        name = self.name

        if not system_draw:
            lo = Layout(f"{name} Example")
            lo.show_rates = self.show_rates
        else:
            assert isinstance(lo, Layout), "lo must be a Layout object"
        lo.add_node(self.ic_diagram_node)

        # Find clock keys dynamically
        name_lower = name.lower()
        ref_clk_key = None
        sysref_key = None
        for key in clocks.keys():
            if key.lower().endswith(f"{name_lower}_ref_clk"):
                ref_clk_key = key
            if key.lower().endswith(f"{name_lower}_sysref"):
                sysref_key = key

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

        converter_clock = clocks[ref_clk_key]
        adc = self.ic_diagram_node.get_child("ADC")
        lo.add_connection({"from": ref_in, "to": adc, "rate": converter_clock})

        # Update decimation filter
        dec_filter = self.ic_diagram_node.get_child("Decimation Filter")
        dec_filter.value = str(self.decimation)

        adc_rate = self.decimation * self.sample_clock
        sample_rate = self.sample_clock
        self.ic_diagram_node.update_connection(
            "ADC", "Decimation Filter", adc_rate
        )
        self.ic_diagram_node.update_connection(
            "Decimation Filter", "JESD204 Framer", sample_rate
        )

        # SYSREF
        if not system_draw:
            sysref_in = Node("SYSREF_IN", ntype="input")
            lo.add_connection(
                {
                    "from": sysref_in,
                    "to": self.ic_diagram_node.get_child("JESD204 Framer"),
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
                    "to": self.ic_diagram_node.get_child("JESD204 Framer"),
                    "rate": clocks[sysref_key],
                }
            )

        # Connect Remote Deframer
        remote_deframer = Node("JESD204 Deframer", ntype="deframer")
        lo.add_node(remote_deframer)

        for _ in range(self.L):
            lane_rate = self.bit_clock
            lo.add_connection(
                {
                    "from": self.ic_diagram_node.get_child("JESD204 Framer"),
                    "to": remote_deframer,
                    "rate": lane_rate,
                }
            )

        if not system_draw:
            return lo.draw()


class adrv9009_tx_draw:
    """ADRV9009 TX drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for ADRV9009 TX."""
        self.ic_diagram_node = None
        self._diagram_output_dividers = []

        name = self.name
        self.ic_diagram_node = Node(name)

        jesd204_deframer = Node("JESD204 Deframer", ntype="jesd204deframer")
        self.ic_diagram_node.add_child(jesd204_deframer)

        interp_filter = Node("Interpolation Filter", ntype="duc")
        self.ic_diagram_node.add_child(interp_filter)
        self.ic_diagram_node.add_connection(
            {"from": jesd204_deframer, "to": interp_filter}
        )

        dac_node = Node("DAC", ntype="dac")
        dac_node.shape = "parallelogram"
        self.ic_diagram_node.add_child(dac_node)
        self.ic_diagram_node.add_connection(
            {"from": interp_filter, "to": dac_node}
        )

    def draw(
        self, clocks: Dict, lo: Layout = None, clock_chip_node: Node = None
    ) -> str:
        """Draw diagram in d2 language for ADRV9009 TX.

        Args:
            clocks (Dict): Dictionary of clocks
            lo (Layout): Layout object to add to. Defaults to None.
            clock_chip_node (Node): Node to connect to. Defaults to None.

        Returns:
            str: Diagram in d2 language
        """
        system_draw = lo is not None
        name = self.name

        if not system_draw:
            lo = Layout(f"{name} Example")
            lo.show_rates = self.show_rates
        else:
            assert isinstance(lo, Layout), "lo must be a Layout object"
        lo.add_node(self.ic_diagram_node)

        # Find clock keys dynamically
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
        sample_rate = self.sample_clock
        interp_filter = self.ic_diagram_node.get_child("Interpolation Filter")
        interp_filter.value = str(self.interpolation)

        self.ic_diagram_node.update_connection(
            "JESD204 Deframer", "Interpolation Filter", sample_rate
        )
        self.ic_diagram_node.update_connection(
            "Interpolation Filter", "DAC", dac_clock
        )

        # Connect ref clock to DAC
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

        dac_node = self.ic_diagram_node.get_child("DAC")
        lo.add_connection({"from": dac_node, "to": ref_in, "rate": dac_clock})

        if not system_draw:
            return lo.draw()
