"""Drawing features for ADRV9009."""

from typing import Dict

from adijif.draw import Layout, Node


class adrv9009_draw:
    """ADRV9009 drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for ADRV9009."""
        self.ic_diagram_node = Node(self.name)

        # ---------------------------------------------------------------------
        # RX Path (ADCs)
        # ---------------------------------------------------------------------
        # ADRV9009 has 2 RX channels usually
        num_rx = 2

        rx_container = Node("RX Path", ntype="shell")
        self.ic_diagram_node.add_child(rx_container)

        # ADC
        for i in range(num_rx):
            adc_node = Node(f"ADC{i}", ntype="adc")
            adc_node.shape = "parallelogram"
            rx_container.add_child(adc_node)

        # Filters: RHB3 -> RHB2 -> RHB1 -> RFIR
        # Since these are per channel, we might want to group them or show flow
        # for each channel
        # Simplified: Show blocks.

        rhb3 = Node("RHB3", ntype="filter")
        rhb2 = Node("RHB2", ntype="filter")
        rhb1 = Node("RHB1", ntype="filter")
        rfir = Node("RFIR", ntype="filter")

        rx_container.add_child(rhb3)
        rx_container.add_child(rhb2)
        rx_container.add_child(rhb1)
        rx_container.add_child(rfir)

        # JESD Framer
        framer = Node("JESD204 Framer", ntype="jesd204framer")
        rx_container.add_child(framer)

        # Connections
        # ADC -> RHB3 -> RHB2 -> RHB1 -> RFIR -> Framer
        for i in range(num_rx):
            rx_container.add_connection(
                {"from": rx_container.get_child(f"ADC{i}"), "to": rhb3}
            )

        rx_container.add_connection({"from": rhb3, "to": rhb2})
        rx_container.add_connection({"from": rhb2, "to": rhb1})
        rx_container.add_connection({"from": rhb1, "to": rfir})
        rx_container.add_connection({"from": rfir, "to": framer})

        # ---------------------------------------------------------------------
        # TX Path (DACs)
        # ---------------------------------------------------------------------
        # ADRV9009 has 2 TX channels
        num_tx = 2

        tx_container = Node("TX Path", ntype="shell")
        self.ic_diagram_node.add_child(tx_container)

        # JESD Deframer
        deframer = Node("JESD204 Deframer", ntype="jesd204deframer")
        tx_container.add_child(deframer)

        # Filters: TFIR -> THB1 -> THB2 -> THB3
        tfir = Node("TFIR", ntype="filter")
        thb1 = Node("THB1", ntype="filter")
        thb2 = Node("THB2", ntype="filter")
        thb3 = Node("THB3", ntype="filter")

        tx_container.add_child(tfir)
        tx_container.add_child(thb1)
        tx_container.add_child(thb2)
        tx_container.add_child(thb3)

        # DAC
        for i in range(num_tx):
            dac_node = Node(f"DAC{i}", ntype="dac")
            dac_node.shape = "parallelogram"
            tx_container.add_child(dac_node)

        # Connections
        # Deframer -> TFIR -> THB1 -> THB2 -> THB3 -> DAC
        tx_container.add_connection({"from": deframer, "to": tfir})
        tx_container.add_connection({"from": tfir, "to": thb1})
        tx_container.add_connection({"from": thb1, "to": thb2})
        tx_container.add_connection({"from": thb2, "to": thb3})

        for i in range(num_tx):
            tx_container.add_connection(
                {"from": thb3, "to": tx_container.get_child(f"DAC{i}")}
            )

        # ---------------------------------------------------------------------
        # Clock Generation
        # ---------------------------------------------------------------------
        # ADRV9009 has onboard PLLs.
        clk_gen = Node("Clock Gen", ntype="shell")
        self.ic_diagram_node.add_child(clk_gen)

        # Internal PLL representation
        ref_div = Node("Ref Div", ntype="divider")
        pll_core = Node("PLL Core", ntype="pll")

        clk_gen.add_child(ref_div)
        clk_gen.add_child(pll_core)

        clk_gen.add_connection({"from": ref_div, "to": pll_core})

        # Connect PLL to RX/TX paths
        # This is logical flow, effectively clocking the converters
        # But in diagram, we might just leave it as generating the clocks.

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
        ref_clk_name = "adrv9009_ref_clk"
        ref_rate = 0

        if not system_draw:
            ref_in = Node("REF_IN", ntype="input")
            lo.add_node(ref_in)
            ref_rate = clocks.get(ref_clk_name, 0)
        else:
            to_node = lo.get_node(ref_clk_name)
            if to_node:
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

        if system_draw:
            return lo.draw()

        return lo.draw()
