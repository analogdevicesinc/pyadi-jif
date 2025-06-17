"""Drawing features for Xilinx FPGA designs."""

from typing import Dict, List

from adijif.converters.converter import converter as Converter
from adijif.draw import Layout, Node


class xilinx_draw:
    """Xilinx drawing features."""

    def _init_diagram(self) -> None:
        """Initialize the diagram for a Xilinx FPGA alone."""
        self.ic_diagram_node = None

        self.ic_diagram_node = Node(self.name)

        # Add generic transceiver since we don't know what is used until later
        transceiver = Node("Transceiver", ntype="transceiver")
        self.ic_diagram_node.add_child(transceiver)

        # Add Link layer JESD204 core
        jesd204_link = Node("JESD204-Link-IP", ntype="ip")
        self.ic_diagram_node.add_child(jesd204_link)

        # Add Transport Layer JESD204 core
        jesd204_transport = Node("JESD204-Transport-IP", ntype="ip")
        self.ic_diagram_node.add_child(jesd204_transport)

        # Add Application layer JESD204 core
        jesd204_application = Node("JESD204-Application-IP", ntype="ip")
        self.ic_diagram_node.add_child(jesd204_application)

        # Add connections
        self.ic_diagram_node.add_connection({"from": transceiver, "to": jesd204_link})
        self.ic_diagram_node.add_connection(
            {"from": jesd204_link, "to": jesd204_transport}
        )
        self.ic_diagram_node.add_connection(
            {"from": jesd204_transport, "to": jesd204_application, "type": "data"}
        )

    def _draw_phy(self, config: Dict, converter: Converter = None) -> tuple:
        """Draw the PHY layer for the Xilinx FPGA.

        Args:
            config (Dict): Configuration dictionary
            converter (Converter): Converter object (optional)

        Returns:
            tuple: Tuple of in_c, out_c, connect_to_input

        Raises:
            Exception: If unknown out_clk_select
        """
        # cfg = {
        #     "clocks": {"FPGA_REF": 500000000.0, "LINK_OUT_REF": 125000000.0},
        #     "fpga": {
        #         "type": "cpll",
        #         "m": 2,
        #         "d": 1,
        #         "n1": 5,
        #         "n2": 4,
        #         "vco": 5000000000.0,
        #         "sys_clk_select": "XCVR_CPLL",
        #         "progdiv": 40.0,
        #         "out_clk_select": "XCVR_PROGDIV_CLK",
        #         "separate_device_clock_required": 1,
        #         "transport_samples_per_clock": 8,
        #     },
        # }

        if converter:
            name = f"{self.name}_{converter.name.upper()}_ref_clk"
            ref_in_rate = config["clocks"][name]
        else:
            ref_in_rate = config["clocks"]["FPGA_REF"]

        phy = Node("JESD204-PHY-IP", ntype="phy")
        self.ic_diagram_node.add_child(phy)

        # PLL
        if config["fpga"]["type"] == "cpll":
            cpll = Node("CPLL", ntype="cpll")
            phy.add_child(cpll)

            # Put stuff in CPLL
            m = Node("M", ntype="divider")
            cpll.add_child(m)
            m.value = config["fpga"]["m"]

            pfd = Node("PFD", ntype="phase-frequency-detector")
            cpll.add_child(pfd)
            cpll.add_connection({"from": m, "to": pfd, "rate": ref_in_rate})

            cp = Node("CP", ntype="charge-pump")
            cpll.add_child(cp)
            cpll.add_connection({"from": pfd, "to": cp})

            lpf = Node("LPF", ntype="loop-filter")
            cpll.add_child(lpf)
            cpll.add_connection({"from": cp, "to": lpf})

            vco = Node("VCO", ntype="vco")
            cpll.add_child(vco)
            cpll.add_connection({"from": lpf, "to": vco})

            d = Node("D", ntype="divider")
            cpll.add_child(d)
            d.value = config["fpga"]["d"]
            cpll.add_connection({"from": vco, "to": d, "rate": config["fpga"]["vco"]})

            n1 = Node("N1", ntype="divider")
            cpll.add_child(n1)
            n1.value = config["fpga"]["n1"]
            cpll.add_connection({"from": vco, "to": n1})

            n2 = Node("N2", ntype="divider")
            cpll.add_child(n2)
            n2.value = config["fpga"]["n2"]
            cpll.add_connection({"from": n1, "to": n2})
            cpll.add_connection({"from": n2, "to": pfd})

            transceiver = Node("Transceiver", ntype="transceiver")
            phy.add_child(transceiver)
            phy.add_connection({"from": d, "to": transceiver})

            # Define common in/out
            in_c = m
            xcvr_out = d
            xcvr_out_rate = config["fpga"]["vco"] / config["fpga"]["d"]

        else:

            qpll = Node("QPLL", ntype="qpll")
            phy.add_child(qpll)

            # Put stuff in QPLL
            m = Node("M", ntype="divider")
            m.value = config["fpga"]["m"]
            qpll.add_child(m)

            pfd = Node("PFD", ntype="phase-frequency-detector")
            qpll.add_child(pfd)

            cp = Node("CP", ntype="charge-pump")
            qpll.add_child(cp)

            lpf = Node("LPF", ntype="loop-filter")
            qpll.add_child(lpf)

            vco = Node("VCO", ntype="vco")
            qpll.add_child(vco)

            n = Node("N", ntype="divider")
            n.value = config["fpga"]["n"]
            qpll.add_child(n)

            # d2 = Node("/2", ntype="divider")
            # qpll.add_child(d2)

            d = Node("D", ntype="divider")
            d.value = config["fpga"]["d"]
            qpll.add_child(d)

            # Connect
            phy.add_connection({"from": m, "to": pfd})
            phy.add_connection({"from": pfd, "to": cp})
            phy.add_connection({"from": cp, "to": lpf})
            phy.add_connection({"from": lpf, "to": vco})
            phy.add_connection({"from": vco, "to": n})
            # TRX is DDR devices so it uses both clock edges
            #   (skipping /2 and *2 dividers)
            # phy.add_connection({"from": vco, "to": d2,
            #   "rate": config['fpga']['vco']})
            # phy.add_connection({"from": d2, "to": d,
            #   "rate": config['fpga']['vco'] / 2})
            phy.add_connection({"from": vco, "to": d, "rate": config["fpga"]["vco"]})
            phy.add_connection({"from": n, "to": pfd})

            xcvr_out = d
            xcvr_out_rate = config["fpga"]["vco"] / config["fpga"]["d"]

            in_c = m

        # Divider complex
        trx_dividers = Node("Transceiver Dividers", ntype="trx-dividers")
        phy.add_child(trx_dividers)

        if config["fpga"]["out_clk_select"] == "XCVR_OUTCLK_PCS":
            raise Exception("Only XCVR_PROGDIV_CLK supported for now")
        elif config["fpga"]["out_clk_select"] == "XCVR_OUTCLK_PMA":
            raise Exception("Only XCVR_PROGDIV_CLK supported for now")
        elif config["fpga"]["out_clk_select"] == "XCVR_REFCLK":

            rmux = Node("REFCLKSEL-Mux", ntype="mux")
            trx_dividers.add_child(rmux)
            connect_to_input = [rmux]

            smux = Node("SYSCLKSEL-Mux", ntype="mux")
            trx_dividers.add_child(smux)
            trx_dividers.add_connection({"from": rmux, "to": smux, "rate": ref_in_rate})

            out_rate = ref_in_rate
            out = smux

        elif config["fpga"]["out_clk_select"] == "XCVR_REFCLK_DIV2":

            rmux = Node("REFCLKSEL-Mux", ntype="mux")
            trx_dividers.add_child(rmux)
            # trx_dividers.add_connection(
            #     {"from": in_c, "to": rmux, "rate": ref_in_rate}
            # )
            connect_to_input = [rmux]

            smux = Node("SYSCLKSEL-Mux", ntype="mux")
            trx_dividers.add_child(smux)
            trx_dividers.add_connection({"from": rmux, "to": smux, "rate": ref_in_rate})

            div2 = Node("DIV2", ntype="divider")
            trx_dividers.add_child(div2)
            div2.value = 2
            trx_dividers.add_connection({"from": smux, "to": div2, "rate": ref_in_rate})

            out_rate = ref_in_rate / 2
            out = div2

        elif config["fpga"]["out_clk_select"] == "XCVR_PROGDIV_CLK":

            mux = Node("PLLCLKSEL-Mux", ntype="mux")
            mux.value = config["fpga"]["type"]
            trx_dividers.add_child(mux)
            phy.add_connection({"from": xcvr_out, "to": mux, "rate": xcvr_out_rate})

            cdr = Node("CDR", ntype="cdr")
            trx_dividers.add_child(cdr)
            trx_dividers.add_connection({"from": mux, "to": cdr})

            progdiv = Node("ProgDiv", ntype="divider")
            trx_dividers.add_child(progdiv)
            progdiv.value = int(config["fpga"]["progdiv"])
            trx_dividers.add_connection({"from": cdr, "to": progdiv})

            out_rate = xcvr_out_rate / config["fpga"]["progdiv"]
            out = progdiv
            connect_to_input = []
        else:
            raise Exception(
                f"Unknown out_clk_select: {config['fpga']['out_clk_select']}"
            )

        out_mux = Node("OUTCLKSEL-Mux", ntype="mux")
        trx_dividers.add_child(out_mux)
        trx_dividers.add_connection({"from": out, "to": out_mux, "rate": out_rate})

        return in_c, out_mux, connect_to_input, xcvr_out

    def draw(
        self, config: Dict, lo: Layout = None, converters: List[Converter] = None
    ) -> str:
        """Draw diagram in d2 language for IC alone with reference clock.

        Args:
            config (Dict): Clock settings
            lo (Layout): Layout object to draw on (optional)
            converters (List): List of converters to draw (optional)

        Returns:
            str: SVG data

        Raises:
            Exception: If no solution is saved
            Exception: If no converter is found
        """
        if not self._saved_solution:
            raise Exception("No solution to draw. Must call solve first.")

        system_draw = lo is not None

        if not system_draw:
            lo = Layout(f"{self.name} Example")
            converters = []
        else:
            # Verify lo is a Layout object
            assert isinstance(lo, Layout), "lo must be a Layout object"
            assert len(converters) == 1, "Only one converter supported"

        lo.add_node(self.ic_diagram_node)

        clocks = config["clocks"]
        device_clock_source = config["fpga"]["device_clock_source"]

        if not system_draw:
            ref_in = Node("REF_IN", ntype="input")
            lo.add_node(ref_in)
        else:
            for converter in converters:
                to_node = lo.get_node(f"{self.name}_{converter.name.upper()}_ref_clk")
                # Locate node connected to this one
                from_node = lo.get_connection(to=to_node.name)
                assert from_node, "No connection found"
                assert isinstance(from_node, list), "Connection must be a list"
                ref_in = from_node[0]["from"]
                lo.remove_node(to_node.name)

        # TO DO, ADD PHY PER CONVERTER
        if not converters:
            converters_first = None
        else:
            converters_first = converters[0]
        in_c, out_c, connect_to_input, xcvr_out = self._draw_phy(
            config, converters_first
        )

        if not system_draw:
            self.ic_diagram_node.add_connection(
                {"from": ref_in, "to": in_c, "rate": clocks["FPGA_REF"]}
            )

        else:
            for converter in converters:
                rcn = f"{self.name}_{converter.name.upper()}_ref_clk"
                assert rcn in clocks, f"Missing clock {rcn}"
                self.ic_diagram_node.add_connection(
                    {"from": ref_in, "to": in_c, "rate": clocks[rcn]}
                )
                if connect_to_input:
                    for c in connect_to_input:
                        self.ic_diagram_node.add_connection(
                            {"from": ref_in, "to": c, "rate": clocks[rcn]}
                        )

        # Delete Transceiver node
        self.ic_diagram_node.remove_child("Transceiver")

        # Connect out_c to JESD204-Link-IP
        if not system_draw:
            self.ic_diagram_node.add_connection(
                {
                    "from": out_c,
                    "to": self.ic_diagram_node.get_child("JESD204-Link-IP"),
                    "rate": clocks["LINK_OUT_REF"],
                }
            )
        else:
            for converter in converters:
                self.ic_diagram_node.add_connection(
                    {
                        "from": out_c,
                        "to": self.ic_diagram_node.get_child("JESD204-Link-IP"),
                        "rate": clocks[
                            f"{self.name}_{converter.name.upper()}_device_clk"
                        ],
                    }
                )

        # Connect device clock to JESD204-Link-IP and JESD204-Transport-IP
        if not system_draw:
            if device_clock_source == "external":
                device_clock = Node("Device Clock", ntype="input")
                lo.add_node(device_clock)
            elif device_clock_source == "link_clock":
                device_clock = out_c
            elif device_clock_source == "ref_clock":
                device_clock = ref_in
            else:
                raise Exception(f"Unknown device clock source: {device_clock_source}")
            self.ic_diagram_node.add_connection(
                {
                    "from": device_clock,
                    "to": self.ic_diagram_node.get_child("JESD204-Link-IP"),
                    "rate": clocks["LINK_OUT_REF"],
                }
            )
            self.ic_diagram_node.add_connection(
                {
                    "from": device_clock,
                    "to": self.ic_diagram_node.get_child("JESD204-Transport-IP"),
                    "rate": clocks["LINK_OUT_REF"],
                }
            )

        else:
            for converter in converters:

                c_name = f"{self.name}_{converter.name.upper()}_device_clk"
                to_node = lo.get_node(c_name)
                # Locate node connected to this one
                from_node = lo.get_connection(to=to_node.name)
                assert from_node, "No connection found"
                assert isinstance(from_node, list), "Connection must be a list"
                lo.remove_node(to_node.name)

                if device_clock_source == "external":
                    device_clock = from_node[0]["from"]
                elif device_clock_source == "link_clock":
                    device_clock = out_c
                elif device_clock_source == "ref_clock":
                    device_clock = ref_in
                else:
                    raise Exception(
                        f"Unknown device clock source: {device_clock_source}"
                    )

                self.ic_diagram_node.add_connection(
                    {
                        "from": device_clock,
                        "to": self.ic_diagram_node.get_child("JESD204-Link-IP"),
                        "rate": clocks[c_name],
                    }
                )
                self.ic_diagram_node.add_connection(
                    {
                        "from": device_clock,
                        "to": self.ic_diagram_node.get_child("JESD204-Transport-IP"),
                        "rate": clocks[c_name],
                    }
                )

        # Connect SYSREF to JESD204-Link-IP
        if not system_draw:
            sysref = Node("SYSREF", ntype="input")
            lo.add_node(sysref)
        else:
            for converter in converters:
                parent = lo.get_node(converter.name.upper())
                to_node = parent.get_child("JESD204 Framer")
                # Locate node connected to this one
                from_node = lo.get_connection(to=to_node.name)
                assert from_node, "No connection found"
                assert isinstance(from_node, list), "Connection must be a list"
                sysref = from_node[0]["from"]
                # lo.remove_node(to_node.name)

        self.ic_diagram_node.add_connection(
            {
                "from": sysref,
                "to": self.ic_diagram_node.get_child("JESD204-Link-IP"),
            }
        )

        # Update with config settings

        # Datapath

        # Get deframer
        if system_draw:
            deframer = lo.get_node("JESD204 Deframer")
            assert deframer, "No JESD204 Deframer found in layout"
            parent = lo.get_node(converter.name.upper())
            framer = parent.get_child("JESD204 Framer")
            assert framer, "No JESD204 Framer found in layout"

            # Replace deframer with a new one inside the FPGA IC diagram
            lo.remove_node("JESD204 Deframer")
            phy_parent = self.ic_diagram_node.get_child("JESD204-PHY-IP")
            new_deframer = Node("DESERIALIZER", ntype="serdes")
            phy_parent.add_child(new_deframer)
            lo.add_connection(
                {
                    "from": xcvr_out,
                    "to": new_deframer,
                    "rate": converter.bit_clock,
                }
            )
            # Add connect for each lane
            for _ in range(converter.L):
                lane_rate = converter.bit_clock
                lo.add_connection(
                    {
                        "from": framer,
                        "to": new_deframer,
                        "rate": lane_rate,
                        "type": "data",
                    }
                )
        if system_draw:
            # Connect DESERIALIZER to link layer decoder
            link_layer = self.ic_diagram_node.get_child("JESD204-Link-IP")
            assert link_layer, "No JESD204-Link-IP found in layout"
            decoder = Node("Link Layer Decoder", ntype="decoder")
            link_layer.add_child(decoder)
            div = 40 if converter.encoding == "8b10b" else 66
            for _ in range(converter.L):
                # Add connect for each lane
                lo.add_connection(
                    {
                        "from": new_deframer,
                        "to": decoder,
                        "rate": converter.bit_clock / div,
                        "type": "data",
                    }
                )

        if system_draw:
            # Add deframer in transport layer
            transport_layer = self.ic_diagram_node.get_child("JESD204-Transport-IP")
            assert transport_layer, "No JESD204-Transport-IP found in layout"
            deframer = Node("JESD204 Deframer", ntype="deframer")
            transport_layer.add_child(deframer)
            # Connect to link layer decoder
            lo.add_connection(
                {
                    "from": decoder,
                    "to": deframer,
                    "rate": converter.bit_clock
                    / (40 if converter.encoding == "8b10b" else 66),
                    "type": "data",
                }
            )
            # Remove connection between link and transport layers
            self.ic_diagram_node.remove_connection(
                from_s=link_layer.name, to=transport_layer.name
            )

        return lo.draw()
