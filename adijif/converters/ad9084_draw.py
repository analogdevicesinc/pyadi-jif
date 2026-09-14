"""Drawing features for AD9084."""

from typing import Dict

from adijif.draw import Layout, Node  # type: ignore # isort: skip  # noqa: I202


class ad9084_draw:
    """AD9084 drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for AD9084 alone."""
        self.ic_diagram_node = None
        self._diagram_output_dividers = []

        name = self.name
        N = 4 if "9084" in self.name else 8

        self.ic_diagram_node = Node(name)

        # External
        self.clk_node = Node("CLK", ntype="clk")
        self.ic_diagram_node.add_child(self.clk_node)
        clk_rx = Node("CLK_RX", ntype="input")
        self.clk_node.add_child(clk_rx)
        clk_rx.arrowhead = "triangle"

        pll_rx = Node("PLL_RX", ntype="input")
        self.clk_node.add_child(pll_rx)
        clk_rx.arrowhead = "triangle"

        # Add 1x path
        clk_1x = Node("CLK_1X", ntype="shell")
        self.clk_node.add_child(clk_1x)
        self.clk_node.add_connection({"from": clk_rx, "to": clk_1x})

        # Add PLL
        vco = Node("PLL", ntype="voltage-controlled-oscillator")
        vco.shape = "circle"
        self.clk_node.add_child(vco)
        self.clk_node.add_connection({"from": pll_rx, "to": vco})

        clk_conv_mux = Node("CLK_CONV_MUX", ntype="crossbar")
        self.clk_node.add_child(clk_conv_mux)
        self.clk_node.add_connection({"from": clk_1x, "to": clk_conv_mux})
        self.clk_node.add_connection({"from": vco, "to": clk_conv_mux})

        crossbar = Node("MUX0", ntype="crossbar")
        crossbar_rm = Node("Router MUX", ntype="crossbar")

        self.ic_diagram_node.add_child(crossbar)
        self.ic_diagram_node.add_child(crossbar_rm)

        for adc in range(N):
            adc_node = Node(f"ADC{adc}", ntype="adc")
            self.ic_diagram_node.add_child(adc_node)
            adc_node.shape = "parallelogram"
            self.ic_diagram_node.add_connection(
                {"from": clk_conv_mux, "to": adc_node}
            )
            self.ic_diagram_node.add_connection(
                {"from": adc_node, "to": crossbar}
            )

        for cddc in range(N):
            cddc_node = Node(f"CDDC{cddc}", ntype="ddc")
            self.ic_diagram_node.add_child(cddc_node)
            self.ic_diagram_node.add_connection(
                {"from": crossbar, "to": cddc_node}
            )
            self.ic_diagram_node.add_connection(
                {"from": cddc_node, "to": crossbar_rm}
            )

        for fddc in range(N * 2):
            fddc_node = Node(f"FDDC{fddc}", ntype="ddc")
            self.ic_diagram_node.add_child(fddc_node)
            self.ic_diagram_node.add_connection(
                {"from": crossbar_rm, "to": fddc_node}
            )

        jesd204_framer = Node("JESD204 Framer", ntype="jesd204framer")
        self.ic_diagram_node.add_child(jesd204_framer)

        for ddc in range(N * 2):
            fddc = self.ic_diagram_node.get_child(f"FDDC{ddc}")
            self.ic_diagram_node.add_connection(
                {"from": fddc, "to": jesd204_framer}
            )

    def _update_diagram(self, config: Dict) -> None:
        """Update diagram with configuration.

        Args:
            config (Dict): Configuration dictionary

        Raises:
            Exception: If key is not D followed by a number
        """
        # Add output dividers
        keys = config.keys()
        output_dividers = self.ic_diagram_node.get_child("Output Dividers")
        for key in keys:
            if key.startswith("D"):
                div = Node(key, ntype="divider")
                output_dividers.add_child(div)
                self.ic_diagram_node.add_connection(
                    {"from": output_dividers, "to": div}
                )
            else:
                raise Exception(
                    f"Unknown key {key}. Must be of for DX where X is a number"
                )

    def draw(
        self, clocks: Dict, lo: Layout = None, clock_chip_node: Node = None
    ) -> str:
        """Draw diagram in d2 language for IC alone with reference clock.

        Args:
            clocks (Dict): Dictionary of clocks
            lo (Layout): Layout object to add to. Defaults to None.
            clock_chip_node (Node): Node to connect to. Defaults to None.

        Returns:
            str: Diagram in d2 language

        Raises:
            Exception: If no solution is saved
        """
        if not self._last_config:
            raise Exception("No solution to draw. Must call solve first.")

        system_draw = lo is not None

        N = 4 if "9084" in self.name else 8

        if not system_draw:
            name = "AD9084" if "9084" in self.name else "AD9088"
            lo = Layout(f"{name} Example", theme=self.diagram_theme)
            lo.show_rates = self.show_rates
        else:
            name = self.name
            # Verify lo is a Layout object
            assert isinstance(lo, Layout), "lo must be a Layout object"
        lo.add_node(self.ic_diagram_node)

        ref_clk_name = f"{name}_ref_clk"
        if not system_draw:
            ref_in = Node("REF_IN", ntype="input")
            lo.add_node(ref_in)
        else:
            if f"{name}_ref_clk_from_ext_pll" in clocks:
                ref_clk_name = f"{name}_ref_clk_from_ext_pll"

            to_node = lo.get_node(ref_clk_name)

            # Locate node connected to this one
            from_node = lo.get_connection(to=to_node.name)
            assert from_node, f"No connection found to {to_node.name}"
            assert isinstance(from_node, list), "Connection must be a list"
            assert len(from_node) == 1, "Only one connection allowed"
            ref_in = from_node[0]["from"]
            # Remove to_node since it is not needed
            lo.remove_node(to_node.name)

        if self.clocking_option == "direct":
            rate = clocks[ref_clk_name]
            # Connect Ref In to Apollo Clk RX
            apollo_ref_in = self.clk_node.get_child("CLK_RX")
            lo.add_connection(
                {"from": ref_in, "to": apollo_ref_in, "rate": rate}
            )
            self.clk_node.update_connection("CLK_RX", "CLK_1X", rate)
            self.clk_node.update_connection("CLK_1X", "CLK_CONV_MUX", rate)
            self.clk_node.update_connection("PLL_RX", "PLL", 0)
            self.clk_node.update_connection("PLL", "CLK_CONV_MUX", 0)
        elif self.clocking_option == "integrated_pll":
            in_rate = clocks[ref_clk_name]
            rate = self.converter_clock
            # Connect Ref In to Apollo Clk RX
            apollo_ref_in = self.clk_node.get_child("PLL_RX")
            lo.add_connection(
                {"from": ref_in, "to": apollo_ref_in, "rate": in_rate}
            )
            self.clk_node.update_connection("CLK_RX", "CLK_1X", 0)
            self.clk_node.update_connection("CLK_1X", "CLK_CONV_MUX", 0)
            self.clk_node.update_connection("PLL_RX", "PLL", in_rate)
            self.clk_node.update_connection("PLL", "CLK_CONV_MUX", rate)

        for i in range(N):
            self.ic_diagram_node.update_connection(
                "CLK_CONV_MUX", f"ADC{i}", rate
            )

        # Update Node values
        fddc_index = 0
        for cddc in range(N):
            self.ic_diagram_node.update_connection("MUX0", f"CDDC{cddc}", rate)

            cddc_node = self.ic_diagram_node.get_child(f"CDDC{cddc}")
            cddc_node.value = str(self.datapath.cddc_decimations[cddc])
            drate = rate / self.datapath.cddc_decimations[cddc]

            self.ic_diagram_node.update_connection(
                f"CDDC{cddc}", "Router MUX", drate
            )

            self.ic_diagram_node.update_connection(
                "Router MUX", f"FDDC{fddc_index}", drate
            )
            fddc_rate_out = drate / self.datapath.fddc_decimations[fddc_index]
            self.ic_diagram_node.update_connection(
                f"FDDC{fddc_index}", "JESD204 Framer", fddc_rate_out
            )
            fddc_index += 1

            self.ic_diagram_node.update_connection(
                "Router MUX", f"FDDC{fddc_index}", drate
            )
            fddc_rate_out = drate / self.datapath.fddc_decimations[fddc_index]
            self.ic_diagram_node.update_connection(
                f"FDDC{fddc_index}", "JESD204 Framer", fddc_rate_out
            )
            fddc_index += 1

        # Connect SYSREF clock to framer
        if not system_draw:
            sysref_in = Node("SYSREF_IN", ntype="input")

            lo.add_connection(
                {
                    "from": sysref_in,
                    "to": self.ic_diagram_node.get_child("JESD204 Framer"),
                    "rate": clocks[f"{name}_sysref"],
                }
            )
        else:
            to_node = lo.get_node(f"{name}_sysref")
            # Locate node connected to this one
            from_node = lo.get_connection(to=to_node.name)
            assert from_node, "No connection found"
            assert isinstance(from_node, list), "Connection must be a list"
            assert len(from_node) == 1, "Only one connection allowed"
            sysref_in = from_node[0]["from"]
            # Remove to_node since it is not needed
            lo.remove_node(to_node.name)

            lo.add_connection(
                {
                    "from": sysref_in,
                    "to": self.ic_diagram_node.get_child("JESD204 Framer"),
                    "rate": clocks[f"{name}_sysref"],
                }
            )

        # Connect Remote Deframer
        remote_deframer = Node("JESD204 Deframer", ntype="deframer")
        lo.add_node(remote_deframer)

        # Add connect for each lane
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
