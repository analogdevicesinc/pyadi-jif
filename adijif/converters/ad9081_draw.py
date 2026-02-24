"""Drawing features for AD9081."""

from typing import Dict

from adijif.draw import Layout, Node


class ad9081_draw:
    """AD9081 drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for AD9081."""
        self.ic_diagram_node = Node(self.name)

        # ---------------------------------------------------------------------
        # RX Path (ADCs)
        # ---------------------------------------------------------------------
        # AD9081 has 4 ADCs
        num_adcs = 4
        # It has 4 Coarse DDCs (CDDCs) and 8 Fine DDCs (FDDCs)
        num_cddcs = 4
        num_fddcs = 8

        # Create RX Nodes
        rx_container = Node("RX Path", ntype="shell")
        self.ic_diagram_node.add_child(rx_container)

        # ADCs
        for i in range(num_adcs):
            adc_node = Node(f"ADC{i}", ntype="adc")
            adc_node.shape = "parallelogram"
            rx_container.add_child(adc_node)

        # Crossbar (Mux) between ADC and CDDC
        cddc_mux = Node("CDDC Mux", ntype="crossbar")
        rx_container.add_child(cddc_mux)

        # CDDCs
        for i in range(num_cddcs):
            cddc_node = Node(f"CDDC{i}", ntype="ddc")
            rx_container.add_child(cddc_node)

        # Crossbar between CDDC and FDDC
        fddc_mux = Node("FDDC Mux", ntype="crossbar")
        rx_container.add_child(fddc_mux)

        # FDDCs
        for i in range(num_fddcs):
            fddc_node = Node(f"FDDC{i}", ntype="ddc")
            rx_container.add_child(fddc_node)

        # JESD204 Framer (RX)
        framer = Node("JESD204 Framer", ntype="jesd204framer")
        rx_container.add_child(framer)

        # RX Connections
        # ADC -> CDDC Mux
        for i in range(num_adcs):
            rx_container.add_connection(
                {"from": rx_container.get_child(f"ADC{i}"), "to": cddc_mux}
            )

        # CDDC Mux -> CDDC
        for i in range(num_cddcs):
            rx_container.add_connection(
                {"from": cddc_mux, "to": rx_container.get_child(f"CDDC{i}")}
            )

        # CDDC -> FDDC Mux
        for i in range(num_cddcs):
            rx_container.add_connection(
                {"from": rx_container.get_child(f"CDDC{i}"), "to": fddc_mux}
            )

        # FDDC Mux -> FDDC
        for i in range(num_fddcs):
            rx_container.add_connection(
                {"from": fddc_mux, "to": rx_container.get_child(f"FDDC{i}")}
            )

        # FDDC -> Framer
        for i in range(num_fddcs):
            rx_container.add_connection(
                {"from": rx_container.get_child(f"FDDC{i}"), "to": framer}
            )

        # ---------------------------------------------------------------------
        # TX Path (DACs)
        # ---------------------------------------------------------------------
        # AD9081 has 4 DACs
        num_dacs = 4
        # 4 Coarse DUCs (CDUCs) and 8 Fine DUCs (FDUCs)
        num_cducs = 4
        num_fducs = 8

        tx_container = Node("TX Path", ntype="shell")
        self.ic_diagram_node.add_child(tx_container)

        # JESD204 Deframer (TX)
        deframer = Node("JESD204 Deframer", ntype="jesd204deframer")
        tx_container.add_child(deframer)

        # FDUCs
        for i in range(num_fducs):
            fduc_node = Node(f"FDUC{i}", ntype="duc")
            tx_container.add_child(fduc_node)

        # Crossbar between FDUC and CDUC
        cduc_mux = Node("CDUC Mux", ntype="crossbar")
        tx_container.add_child(cduc_mux)

        # CDUCs
        for i in range(num_cducs):
            cduc_node = Node(f"CDUC{i}", ntype="duc")
            tx_container.add_child(cduc_node)

        # Crossbar between CDUC and DAC
        dac_mux = Node("DAC Mux", ntype="crossbar")
        tx_container.add_child(dac_mux)

        # DACs
        for i in range(num_dacs):
            dac_node = Node(f"DAC{i}", ntype="dac")
            dac_node.shape = "parallelogram"
            tx_container.add_child(dac_node)

        # TX Connections
        # Deframer -> FDUC
        for i in range(num_fducs):
            tx_container.add_connection(
                {"from": deframer, "to": tx_container.get_child(f"FDUC{i}")}
            )

        # FDUC -> CDUC Mux
        for i in range(num_fducs):
            tx_container.add_connection(
                {"from": tx_container.get_child(f"FDUC{i}"), "to": cduc_mux}
            )

        # CDUC Mux -> CDUC
        for i in range(num_cducs):
            tx_container.add_connection(
                {"from": cduc_mux, "to": tx_container.get_child(f"CDUC{i}")}
            )

        # CDUC -> DAC Mux
        for i in range(num_cducs):
            tx_container.add_connection(
                {"from": tx_container.get_child(f"CDUC{i}"), "to": dac_mux}
            )

        # DAC Mux -> DAC
        for i in range(num_dacs):
            tx_container.add_connection(
                {"from": dac_mux, "to": tx_container.get_child(f"DAC{i}")}
            )

        # ---------------------------------------------------------------------
        # Clock Generation
        # ---------------------------------------------------------------------
        clk_gen = Node("Clock Gen", ntype="shell")
        self.ic_diagram_node.add_child(clk_gen)

        # PLL Components
        ref_div = Node("R", ntype="divider")
        clk_gen.add_child(ref_div)

        pfd = Node("PFD", ntype="phase-frequency-detector")
        clk_gen.add_child(pfd)

        vco = Node("VCO", ntype="voltage-controlled-oscillator")
        vco.shape = "circle"
        clk_gen.add_child(vco)

        feed_div_m = Node("M", ntype="divider")  # M divider (VCO output)
        clk_gen.add_child(feed_div_m)

        feed_div_n = Node("N", ntype="divider")  # N divider (Feedback)
        clk_gen.add_child(feed_div_n)

        out_div_d = Node("D", ntype="divider")  # D divider (Output)
        clk_gen.add_child(out_div_d)

        # Connections
        # Ref -> R -> PFD
        clk_gen.add_connection({"from": ref_div, "to": pfd})
        # PFD -> VCO (simplified, skip Loop Filter for compactness or add if desired)
        clk_gen.add_connection({"from": pfd, "to": vco})
        # VCO -> M -> N -> PFD
        clk_gen.add_connection({"from": vco, "to": feed_div_m})
        clk_gen.add_connection({"from": feed_div_m, "to": feed_div_n})
        clk_gen.add_connection({"from": feed_div_n, "to": pfd})
        # VCO -> M -> D -> Distribution
        clk_gen.add_connection({"from": feed_div_m, "to": out_div_d})

    def _update_diagram(self, config: Dict) -> None:
        pass

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
        if not hasattr(self, "solution") or not self.solution:
            pass

        system_draw = lo is not None
        if not system_draw:
            lo = Layout(f"{self.name} Example")
            lo.show_rates = self.show_rates

        lo.add_node(self.ic_diagram_node)

        # Get References
        clk_gen = self.ic_diagram_node.get_child("Clock Gen")

        # ---------------------------------------------------------------------
        # External Connections
        # ---------------------------------------------------------------------
        ref_clk_name = f"{self.name.lower()}_ref_clk"

        if not system_draw:
            ref_in = Node("REF_IN", ntype="input")
            lo.add_node(ref_in)
            ref_rate = clocks.get(ref_clk_name, 0)
        else:
            to_node = lo.get_node(ref_clk_name)
            from_node_conn = lo.get_connection(to=to_node.name)
            if from_node_conn:
                ref_in = from_node_conn[0]["from"]
                ref_rate = clocks.get(ref_clk_name, 0)
                lo.remove_node(to_node.name)
            else:
                ref_in = Node("REF_IN", ntype="input")
                lo.add_node(ref_in)
                ref_rate = clocks.get(ref_clk_name, 0)

        # Connect Ref to Clock Gen
        lo.add_connection(
            {"from": ref_in, "to": clk_gen.get_child("R"), "rate": ref_rate}
        )

        if system_draw:
            return lo.draw()

        return lo.draw()
