"""Drawing features for Xilinx FPGA designs."""
from typing import Dict, List, Tuple

from adijif.draw import Layout, Node


class xilinx_draw:
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
            {"from": jesd204_transport, "to": jesd204_application}
        )

    def _draw_phy(self, config: Dict) -> None:

        cfg = {
            "clocks": {"FPGA_REF": 500000000.0, "LINK_OUT_REF": 125000000.0},
            "fpga": {
                "type": "cpll",
                "m": 2,
                "d": 1,
                "n1": 5,
                "n2": 4,
                "vco": 5000000000.0,
                "sys_clk_select": "XCVR_CPLL",
                "progdiv": 40.0,
                "out_clk_select": "XCVR_PROGDIV_CLK",
                "separate_device_clock_required": 1,
                "transport_samples_per_clock": 8,
            },
        }

        phy = Node("JESD204-PHY-IP", ntype="phy")
        self.ic_diagram_node.add_child(phy)

        # PLL
        if config['fpga']['type'] == 'cpll':
            cpll = Node("CPLL", ntype="cpll")
            phy.add_child(cpll)

            # Put stuff in CPLL
            m = Node("M", ntype="divider")
            cpll.add_child(m)
            m.value = config['fpga']['m']

            pfd = Node("PFD", ntype="phase-frequency-detector")
            cpll.add_child(pfd)
            cpll.add_connection({"from": m, "to": pfd, "rate": config['clocks']['FPGA_REF']})

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
            d.value = config['fpga']['d']
            cpll.add_connection({"from": vco, "to": d, "rate": config['fpga']['vco']})

            n1 = Node("N1", ntype="divider")
            cpll.add_child(n1)
            n1.value = config['fpga']['n1']
            cpll.add_connection({"from": vco, "to": n1})

            n2 = Node("N2", ntype="divider")
            cpll.add_child(n2)
            n2.value = config['fpga']['n2']
            cpll.add_connection({"from": n1, "to": n2})
            cpll.add_connection({"from": n2, "to": pfd})

            transceiver = Node("Transceiver", ntype="transceiver")
            phy.add_child(transceiver)
            phy.add_connection({"from": d, "to": transceiver})


            in_c = m
            xcvr_out = d
            xcvr_out_rate = config['fpga']['vco'] / config['fpga']['d']

        else:

            qpll = Node("QPLL", ntype="qpll")
            phy.add_child(qpll)

            xcvr_out = qpll
            xcvr_out_rate = config['fpga']['vco']

            in_c = qpll


        # Divider complex
        trx_dividers = Node("Transceiver Dividers", ntype="trx-dividers")
        phy.add_child(trx_dividers)

        if config['fpga']['out_clk_select'] == "XCVR_OUTCLK_PCS":
            raise Exception("Only XCVR_PROGDIV_CLK supported for now")
        elif config['fpga']['out_clk_select'] == "XCVR_OUTCLK_PMA":
            raise Exception("Only XCVR_PROGDIV_CLK supported for now")
        elif config['fpga']['out_clk_select'] == "XCVR_REF_CLK":
            # raise Exception("Only XCVR_PROGDIV_CLK supported")

            div_ref_clk = Node("DIV_REF_CLK", ntype="divider")
            trx_dividers.add_child(div_ref_clk)
            div_ref_clk.value = 1
            trx_dividers.add_connection({"from": xcvr_out, "to": div_ref_clk, "rate": xcvr_out_rate})

            out_rate = xcvr_out_rate
            out = div_ref_clk

        elif config['fpga']['out_clk_select'] == "XCVR_REFCLK_DIV2":
            raise Exception("Only XCVR_PROGDIV_CLK supported")
        
        elif config['fpga']['out_clk_select'] == "XCVR_PROGDIV_CLK":

            mux = Node("PLLCLKSEL-Mux", ntype="mux")
            mux.value = config['fpga']['type']
            trx_dividers.add_child(mux)
            phy.add_connection({"from": xcvr_out, "to": mux, "rate": xcvr_out_rate})

            cdr = Node("CDR", ntype="cdr")
            trx_dividers.add_child(cdr)
            trx_dividers.add_connection({"from": mux, "to": cdr})

            progdiv = Node("ProgDiv", ntype="divider")
            trx_dividers.add_child(progdiv)
            progdiv.value = int(config['fpga']['progdiv'])
            trx_dividers.add_connection({"from": cdr, "to": progdiv})

            out_rate = xcvr_out_rate / config['fpga']['progdiv']
            out = progdiv
        else:
            raise Exception(f"Unknown out_clk_select: {config['fpga']['out_clk_select']}")
            

        out_mux = Node("OUTCLKSEL-Mux", ntype="mux")
        trx_dividers.add_child(out_mux)
        trx_dividers.add_connection({"from": out, "to": out_mux, "rate": out_rate})
         
        return in_c, out_mux

    def draw(self, config, lo=None) -> str:
        """Draw diagram in d2 language for IC alone with reference clock.

        Args:
            clocks (Dict): Clock settings

        Returns:
            str: SVG data
        """
        if not self._saved_solution:
            raise Exception("No solution to draw. Must call solve first.")
        
        system_draw = lo is not None

        if not system_draw:
            lo = Layout(f"{self.name} Example")
        else:
            # Verify lo is a Layout object
            assert isinstance(lo, Layout), "lo must be a Layout object"

        lo.add_node(self.ic_diagram_node)

        clocks = config["clocks"]

        if not system_draw:
            ref_in = Node("REF_IN", ntype="input")
        else:
            to_node = lo.get_node("AD9680_fpga_ref_clk")
            # Locate node connected to this one
            from_node = lo.get_connection(to=to_node.name)
            assert from_node, "No connection found"
            assert isinstance(from_node, list), "Connection must be a list"
            ref_in = from_node[0]["from"]
            lo.remove_node(to_node.name)
        lo.add_node(ref_in)

        in_c, out_c = self._draw_phy(config)
        self.ic_diagram_node.add_connection({"from": ref_in, "to": in_c, "rate": clocks["AD9680_ref_clk"]})
        # Delete Transceiver node
        self.ic_diagram_node.remove_child("Transceiver")

        # Connect out_c to JESD204-Link-IP
        self.ic_diagram_node.add_connection(
            {
                "from": out_c,
                "to": self.ic_diagram_node.get_child("JESD204-Link-IP"),
                "rate": clocks["AD9680_fpga_link_out_clk"],
            }
        )

        # Connect device clock to JESD204-Link-IP
        if not system_draw:
            device_clock = Node("Device Clock", ntype="input")
        else:
            to_node = lo.get_node("AD9680_fpga_link_out_clk")
            # Locate node connected to this one
            from_node = lo.get_connection(to=to_node.name)
            assert from_node, "No connection found"
            assert isinstance(from_node, list), "Connection must be a list"
            device_clock = from_node[0]["from"]
            lo.remove_node(to_node.name)
        lo.add_node(device_clock)
        self.ic_diagram_node.add_connection(
            {
                "from": device_clock,
                "to": self.ic_diagram_node.get_child("JESD204-Link-IP"),
                "rate": clocks["AD9680_fpga_link_out_clk"],
            }
        )

        # Connect SYSREF to JESD204-Link-IP
        if not system_draw:
            sysref = Node("SYSREF", ntype="input")
        else:
            parent = lo.get_node("AD9680")
            to_node = parent.get_child("JESD204 Framer")
            # Locate node connected to this one
            from_node = lo.get_connection(to=to_node.name)
            assert from_node, "No connection found"
            assert isinstance(from_node, list), "Connection must be a list"
            sysref = from_node[0]["from"]
            # lo.remove_node(to_node.name)
        lo.add_node(sysref)
        self.ic_diagram_node.add_connection(
            {
                "from": sysref,
                "to": self.ic_diagram_node.get_child("JESD204-Link-IP"),
            }
        )

        # Update with config settings

        return lo.draw()
