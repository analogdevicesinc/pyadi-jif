"""Drawing features for AD9081."""

from typing import Dict

from adijif.draw import Layout, Node  # type: ignore # isort: skip  # noqa: I202


class ad9081_rx_draw:
    """AD9081 RX drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for AD9081 RX."""
        self.ic_diagram_node = None
        self._diagram_output_dividers = []

        name = self.name
        N = 4  # AD9081 always has 4 ADCs

        self.ic_diagram_node = Node(name)

        crossbar = Node("MUX0", ntype="crossbar")
        crossbar_rm = Node("Router MUX", ntype="crossbar")

        self.ic_diagram_node.add_child(crossbar)
        self.ic_diagram_node.add_child(crossbar_rm)

        for adc in range(N):
            adc_node = Node(f"ADC{adc}", ntype="adc")
            self.ic_diagram_node.add_child(adc_node)
            adc_node.shape = "parallelogram"
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

    def draw(
        self, clocks: Dict, lo: Layout = None, clock_chip_node: Node = None
    ) -> str:
        """Draw diagram in d2 language for AD9081 RX.

        Args:
            clocks (Dict): Dictionary of clocks
            lo (Layout): Layout object to add to. Defaults to None.
            clock_chip_node (Node): Node to connect to. Defaults to None.

        Returns:
            str: Diagram in d2 language
        """
        system_draw = lo is not None
        name = self.name
        N = 4

        if not system_draw:
            lo = Layout(f"{name} Example")
            lo.show_rates = self.show_rates
        else:
            assert isinstance(lo, Layout), "lo must be a Layout object"
        lo.add_node(self.ic_diagram_node)

        # Find clock keys dynamically (handles case differences)
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

        for i in range(N):
            adc = self.ic_diagram_node.get_child(f"ADC{i}")
            lo.add_connection(
                {"from": ref_in, "to": adc, "rate": clocks[ref_clk_key]}
            )

        # Update Node values
        fddc_index = 0
        for cddc in range(N):
            rate = clocks[ref_clk_key]
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

        # Connect clock to framer
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


class ad9081_tx_draw:
    """AD9081 TX drawing features."""

    _system_draw = False
    show_rates = True

    def _init_diagram(self) -> None:
        """Initialize diagram for AD9081 TX."""
        self.ic_diagram_node = None
        self._diagram_output_dividers = []

        name = self.name
        N = 4  # AD9081 always has 4 DACs

        self.ic_diagram_node = Node(name)

        # TX datapath: Deframer -> FDUCs -> Router MUX -> CDUCs -> MUX -> DACs
        jesd204_deframer = Node("JESD204 Deframer", ntype="jesd204deframer")
        self.ic_diagram_node.add_child(jesd204_deframer)

        for fduc in range(N * 2):
            fduc_node = Node(f"FDUC{fduc}", ntype="duc")
            self.ic_diagram_node.add_child(fduc_node)
            self.ic_diagram_node.add_connection(
                {"from": jesd204_deframer, "to": fduc_node}
            )

        crossbar_rm = Node("Router MUX", ntype="crossbar")
        self.ic_diagram_node.add_child(crossbar_rm)

        for fduc in range(N * 2):
            fduc_node = self.ic_diagram_node.get_child(f"FDUC{fduc}")
            self.ic_diagram_node.add_connection(
                {"from": fduc_node, "to": crossbar_rm}
            )

        for cduc in range(N):
            cduc_node = Node(f"CDUC{cduc}", ntype="duc")
            self.ic_diagram_node.add_child(cduc_node)
            self.ic_diagram_node.add_connection(
                {"from": crossbar_rm, "to": cduc_node}
            )

        crossbar = Node("MUX0", ntype="crossbar")
        self.ic_diagram_node.add_child(crossbar)

        for cduc in range(N):
            cduc_node = self.ic_diagram_node.get_child(f"CDUC{cduc}")
            self.ic_diagram_node.add_connection(
                {"from": cduc_node, "to": crossbar}
            )

        for dac in range(N):
            dac_node = Node(f"DAC{dac}", ntype="dac")
            self.ic_diagram_node.add_child(dac_node)
            dac_node.shape = "parallelogram"
            self.ic_diagram_node.add_connection(
                {"from": crossbar, "to": dac_node}
            )

    def draw(
        self, clocks: Dict, lo: Layout = None, clock_chip_node: Node = None
    ) -> str:
        """Draw diagram in d2 language for AD9081 TX.

        Args:
            clocks (Dict): Dictionary of clocks
            lo (Layout): Layout object to add to. Defaults to None.
            clock_chip_node (Node): Node to connect to. Defaults to None.

        Returns:
            str: Diagram in d2 language
        """
        system_draw = lo is not None
        name = self.name
        N = 4

        if not system_draw:
            lo = Layout(f"{name} Example")
            lo.show_rates = self.show_rates
        else:
            assert isinstance(lo, Layout), "lo must be a Layout object"
        lo.add_node(self.ic_diagram_node)

        # Find clock keys dynamically (handles case differences)
        name_lower = name.lower()
        ref_clk_key = None
        sysref_key = None
        for key in clocks.keys():
            if key.lower().endswith(f"{name_lower}_ref_clk"):
                ref_clk_key = key
            if key.lower().endswith(f"{name_lower}_sysref"):
                sysref_key = key

        # Compute rates: DAC clock = interpolation * sample_clock
        # sample_clock -> FDUC (x fduc_interpolation) -> CDUC (x cduc_interpolation) -> DAC clock
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

        # Update rates through the TX datapath
        # Data flows: Deframer -> FDUC -> Router MUX -> CDUC -> MUX -> DAC
        # The sample rate at the input is dac_clock / total_interpolation
        sample_rate = dac_clock / self.interpolation
        fduc_interp = self.datapath.fduc_interpolation
        cduc_interp = self.datapath.cduc_interpolation

        fduc_index = 0
        for cduc in range(N):
            # FDUC output rate = sample_rate * fduc_interpolation
            fduc_out_rate = sample_rate * fduc_interp

            self.ic_diagram_node.update_connection(
                "JESD204 Deframer", f"FDUC{fduc_index}", sample_rate
            )
            fduc_node = self.ic_diagram_node.get_child(f"FDUC{fduc_index}")
            fduc_node.value = str(fduc_interp)
            self.ic_diagram_node.update_connection(
                f"FDUC{fduc_index}", "Router MUX", fduc_out_rate
            )
            fduc_index += 1

            self.ic_diagram_node.update_connection(
                "JESD204 Deframer", f"FDUC{fduc_index}", sample_rate
            )
            fduc_node = self.ic_diagram_node.get_child(f"FDUC{fduc_index}")
            fduc_node.value = str(fduc_interp)
            self.ic_diagram_node.update_connection(
                f"FDUC{fduc_index}", "Router MUX", fduc_out_rate
            )
            fduc_index += 1

            # CDUC output rate = fduc_out_rate * cduc_interpolation
            cduc_out_rate = fduc_out_rate * cduc_interp
            self.ic_diagram_node.update_connection(
                "Router MUX", f"CDUC{cduc}", fduc_out_rate
            )
            cduc_node = self.ic_diagram_node.get_child(f"CDUC{cduc}")
            cduc_node.value = str(cduc_interp)
            self.ic_diagram_node.update_connection(
                f"CDUC{cduc}", "MUX0", cduc_out_rate
            )

        # DAC output rate = dac_clock
        for dac in range(N):
            self.ic_diagram_node.update_connection(
                "MUX0", f"DAC{dac}", dac_clock
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

        for i in range(N):
            dac_node = self.ic_diagram_node.get_child(f"DAC{i}")
            lo.add_connection(
                {"from": dac_node, "to": ref_in, "rate": dac_clock}
            )

        if not system_draw:
            return lo.draw()
