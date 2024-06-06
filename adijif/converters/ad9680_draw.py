"""Drawing features for AD9680."""
from typing import Dict

from adijif.draw import Layout, Node  # type: ignore # isort: skip  # noqa: I202

class ad9680_draw:

    def _init_diagram(self) -> None:
        """Initialize diagram for AD9680 alone."""
        self.ic_diagram_node = None
        self._diagram_output_dividers = []


        self.ic_diagram_node = Node("AD9680")

        # External
        # ref_in = Node("REF_IN", ntype="input")
        # lo.add_node(ref_in)

        crossbar = Node("Crossbar", ntype="crossbar")
        self.ic_diagram_node.add_child(crossbar)
        for adc in range(2):
            adc_node = Node(f"ADC{adc}", ntype="adc")
            self.ic_diagram_node.add_child(adc_node)
            adc_node.shape = "parallelogram"
            self.ic_diagram_node.add_connection({"from": adc_node, "to": crossbar})

        for ddc in range(4):
            ddc_node = Node(f"DDC{ddc}", ntype="ddc")
            self.ic_diagram_node.add_child(ddc_node)
            self.ic_diagram_node.add_connection({"from": crossbar, "to": ddc_node})

        jesd204_framer = Node("JESD204 Framer", ntype="jesd204framer")
        self.ic_diagram_node.add_child(jesd204_framer)

        for ddc in range(4):
            ddc = self.ic_diagram_node.get_child(f"DDC{ddc}")
            self.ic_diagram_node.add_connection({"from": ddc, "to": jesd204_framer})


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

    def draw(self, clocks) -> str:
        """Draw diagram in d2 language for IC alone with reference clock.

        Args:
            clocks (Dict): Dictionary of clocks

        Returns:
            str: Diagram in d2 language

        Raises:
            Exception: If no solution is saved
        """
        if not self._saved_solution:
            raise Exception("No solution to draw. Must call solve first.")
        lo = Layout("AD9680 Example")
        lo.add_node(self.ic_diagram_node)

        static_options = self.get_config()

        ref_in = Node("REF_IN", ntype="input")
        lo.add_node(ref_in)
        for i in range(2):
            adc = self.ic_diagram_node.get_child(f"ADC{i}")
            lo.add_connection({"from": ref_in, "to": adc, "rate": clocks["ad9680_adc_clock"]})

        # Update Node values
        for ddc in range(4):
            rate =  clocks["ad9680_adc_clock"]
            self.ic_diagram_node.update_connection("Crossbar", f"DDC{ddc}", rate)
            
            ddc_node = self.ic_diagram_node.get_child(f"DDC{ddc}")
            ddc_node.value = str(static_options["decimation"])
            drate = rate/static_options["decimation"]

            self.ic_diagram_node.update_connection(f"DDC{ddc}", "JESD204 Framer", drate)

        # Connect clock to framer
        sysref_in = Node("SYSREF_IN", ntype="input")

        lo.add_connection(
            {
                "from": sysref_in,
                "to": self.ic_diagram_node.get_child("JESD204 Framer"),
                "rate": clocks["ad9680_sysref"],
            }
        )

        # Connect Remote Deframer
        remote_deframer = Node("JESD204 Deframer", ntype="deframer")

        # Add connect for each lane
        for i in range(self.L):
            lane_rate = self.bit_clock
            lo.add_connection({"from": self.ic_diagram_node.get_child("JESD204 Framer"), "to": remote_deframer, "rate": lane_rate})


        return lo.draw()