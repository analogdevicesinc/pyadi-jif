from turtle import bgcolor
import graphviz
from typing import List
import os
from jinja2 import Environment, FileSystemLoader
import lxml.etree as ET


class graph:

    connections: dict = {}
    inputs: List[str] = []
    show_label_MHz = True
    ref_loc = [0, 0]
    place_source_nodes = True

    def _get_rate(self, node_description, cfg, input):
        if node_description["type"] == "rate":
            node_output_rates = cfg
        elif node_description["type"] in ["mult", "feedbackdiv"]:
            node_output_rates = input * cfg
        elif node_description["type"] == "div":
            node_output_rates = input / cfg
        elif node_description["type"] == "pass":
            node_output_rates = input
        else:
            raise ValueError(f"Unknown node type {node_description['type']}")
        return node_output_rates

    def _get_node_config(self, connected_node, cfg):
        if "cfg_alternative_name" in self.g_nodes[connected_node]:
            return cfg[self.g_nodes[connected_node]["cfg_alternative_name"]]
        else:
            return cfg[connected_node]

    def _get_node_cfg_rate(self, node_name, connected_node, cfg, input_rate):

        settings = self._get_node_config(connected_node, cfg)

        if not isinstance(settings, list):
            settings = [settings]

        rates = []
        for setting in settings:
            rates.append(
                self._get_rate(
                    self.g_nodes[connected_node],
                    setting,
                    input_rate,
                )
            )
        return rates

    def label_edges(self, cfg, e_labels=None):
        """Traverse graph and label edges"""

        node_output_rates = {}

        # Labels edges connected to inputs first
        if self.place_source_nodes:
            u_cfg = cfg
        else:
            u_cfg = e_labels

        for input in self.inputs:
            node_output_rates[input] = u_cfg[input]
            for connected_node in self.inputs[input]:
                source_input_rate = node_output_rates[input]

                solver_result = self._get_node_config(
                    connected_node, cfg
                )  # Handle name if different in solver config
                desc = self.g_nodes[connected_node]

                out_rate = self._get_rate(desc, solver_result, source_input_rate)

                node_output_rates[connected_node] = out_rate

        # print(f"{node_output_rates=}")

        # Loop through all edges until all edges are labeled
        while True:
            updated_nodes = 0
            for node in self.g_nodes:
                if self.g_nodes[node]["edges"]:
                    for connected_node in self.g_nodes[node]["edges"]:
                        if not connected_node:
                            continue
                        if connected_node not in node_output_rates:
                            if (
                                "variable_node" in self.g_nodes[connected_node]
                                and self.g_nodes[connected_node]["variable_node"]
                            ):
                                node_output_rates[
                                    connected_node
                                ] = self._get_node_cfg_rate(
                                    node, connected_node, cfg, node_output_rates[node]
                                )
                            else:

                                node_info = self.g_nodes[connected_node]
                                if connected_node in cfg or (
                                    "cfg_alternative_name" in node_info
                                    and node_info["cfg_alternative_name"] in cfg
                                ):
                                    solver_result = self._get_node_config(
                                        connected_node, cfg
                                    )
                                else:
                                    solver_result = None
                                source_input_rate = node_output_rates[node]

                                node_output_rates[connected_node] = self._get_rate(
                                    node_info,
                                    solver_result,
                                    source_input_rate,
                                )
                            updated_nodes += 1

            if updated_nodes == 0:
                break

        # Remove feedback nodes as we don't want to display them in the graph
        final_output_rates = {}
        for node in node_output_rates:
            # Remove label out of feedback nodes

            # Remove label to feedback node
            if node in self.g_nodes:
                if "show_out_rate" in self.g_nodes[node]:
                    show = self.g_nodes[node]["show_out_rate"]
                else:
                    show = True
                if self.g_nodes[node]["type"] != "feedbackdiv" and show:
                    final_output_rates[node] = node_output_rates[node]
            else:
                final_output_rates[node] = node_output_rates[node]

        # Flatten variable nodes
        final_output_rates_flat = {}
        for node in final_output_rates:
            if isinstance(final_output_rates[node], list):
                for i, rate in enumerate(final_output_rates[node]):
                    final_output_rates_flat[f"{node}_{i}"] = rate
            else:
                final_output_rates_flat[node] = final_output_rates[node]

        # print(final_output_rates_flat)

        return final_output_rates_flat

    def update_svg(self, svg):
        root = ET.fromstring(bytes(svg, encoding="utf-8"))

        tag_prefix = "{http://www.w3.org/2000/svg}"

        for element in root.iter():
            c = element.get("class")
            if c == "edge":
                for c_element in element.iter():
                    if c_element.tag == tag_prefix + "path":
                        # c_element.set("stroke","red")
                        # c_element.set("stroke-width","20px")
                        c_element.set(
                            "onmousemove", "showTooltip(evt, 'This is blue');"
                        )
                        c_element.set("onmouseout", "hideTooltip();")

        svg_str = ET.tostring(root)
        svg_str = svg_str.decode("utf-8")

        return root, svg_str

    def generate_html(self, filename, output_filename):

        with open(filename, "r") as f:
            svg = f.read()

        root, svg = self.update_svg(svg)

        # Import template
        loc = os.path.dirname(__file__)
        loc = os.path.join(loc)
        file_loader = FileSystemLoader(loc)
        env = Environment(loader=file_loader)

        template = env.get_template("template.html")
        output = template.render(svg=svg)

        with open(output_filename, "w") as f:
            f.write(output)
        return root

    def _pretty_label(self, rate):

        if self.show_label_MHz:
            rate = rate / 1e6
            return f"{rate:.2f} MHz"
        else:
            return f"{rate:.2f} Hz"

    def create_component_graph(
        self, g: graphviz.Digraph, source_name: str, e_labels, cfg: dict
    ):

        with g.subgraph(
            name="cluster" + self.name
        ) as sg:  # Must use name cluster to get styling

            sg.attr(
                color="blue",
                label=self.name,
                labelloc="bl",
                margin="1,1",
                fontsize="20",
            )


            connections = self.g_nodes.copy()
            labels = [con.replace("_", "\n") for con in connections]

            scale_x = 2
            scale_y = 2
            locations_x = []
            locations_y = []

            # Add all nodes
            for node, label in zip(connections, labels):
                loc = connections[node]["location"]
                if (
                    "variable_node" in connections[node]
                    and connections[node]["variable_node"]
                ):
                    count = len(self._get_node_config(node, cfg))
                    xe, ye = connections[node]["variable_node_extend_location"]
                    for c in range(count):
                        sg.node(
                            f"{node}_{c}",
                            label=f"{label}_{c}",
                            shape="square",
                            pos=f"{self.ref_loc[0]+loc[0]*scale_x+xe*c},{self.ref_loc[1]+loc[1]*scale_y+ye*c}!",
                            width="1",
                            style="filled",
                            bgcolor="grey",
                            id=node,
                        )
                        locations_x.append(self.ref_loc[0] + loc[0] * scale_x + xe * c)
                        locations_y.append(self.ref_loc[1] + loc[1] * scale_y + ye * c)

                else:
                    sg.node(
                        node,
                        label=label,
                        shape="square",
                        pos=f"{self.ref_loc[0]+loc[0]*scale_x},{self.ref_loc[1]+loc[1]*scale_y}!",
                        width="1",
                        style="filled",
                        bgcolor="grey",
                        id=node,
                    )
                    locations_x.append(self.ref_loc[0] + loc[0] * scale_x)
                    locations_y.append(self.ref_loc[1] + loc[1] * scale_y)

            # Add hidden nodes to create margin around subgraph
            margin = 0.5
            x = min(locations_x)
            y = max(locations_y)
            a = max(locations_x)
            b = min(locations_y)
            sg.node(
                f"EDGE0_{self.name}",
                shape="square",
                pos=f"{x-margin},{y+margin}!",
                width="1",
                style="invis",
            )
            sg.node(
                f"EDGE1_{self.name}",
                shape="square",
                pos=f"{a+margin},{b-margin}!",
                width="1",
                style="invis",
            )

            # Connect nodes together
            for node in connections:
                if connections[node]["edges"]:
                    for connected_node in connections[node]["edges"]:
                        if not connected_node:
                            continue
                        splines = (
                            "ortho"
                            if self.g_nodes[connected_node]["type"] == "feedbackdiv"
                            else "line"
                        )
                        splines="line"
                        show_label = (
                            self.g_nodes[connected_node]["type"] != "feedbackdiv"
                        )

                        if (
                            "variable_node" in connections[connected_node]
                            and connections[connected_node]["variable_node"]
                        ):
                            count = len(self._get_node_config(connected_node, cfg))
                        else:
                            count = 1

                        if count == 1:
                            if node in e_labels and show_label:
                                # print(
                                #     f"{node} -> {connected_node} : {e_labels[node]} {self.g_nodes[node]['type']}"
                                # )
                                sg.edge(
                                    node,
                                    connected_node,
                                    splines=splines,
                                    label=self._pretty_label(e_labels[node]),
                                )
                            else:
                                sg.edge(node, connected_node)

                        else:
                            for c in range(count):
                                if node in e_labels and show_label:
                                    # print(
                                    #     f"{node} -> {connected_node}_{c} : {e_labels[node][c]} {self.g_nodes[node]['type']}"
                                    # )
                                    sg.edge(
                                        node,
                                        f"{connected_node}_{c}",
                                        splines=splines,
                                        label=self._pretty_label(e_labels[node]),
                                    )
                                else:
                                    sg.edge(
                                        node, f"{connected_node}_{c}", splines=splines
                                    )

        # Connect input
        for input in self.inputs:
            for connected_input in self.inputs[input]:
                if input in e_labels:
                    label=self._pretty_label(e_labels[input])
                else:
                    label=None
                print(f"{input} -> {connected_input} : {label}")
                g.edge(input+":w", connected_input+":w", label=label, constraint="false")
            # if input in e_labels:
            #     g.edge(
            #         input,
            #         self.inputs[input],
            #         label=self._pretty_label(e_labels[input]),
            #     )
            # else:
            #     for connected_input in self.inputs[input]:
            #         g.edge(input, connected_input)

        return g

    def place_sources(self, g: graphviz.Digraph):
        for i, input in enumerate(self.inputs):
            g.node(input, pos=f"{self.ref_loc[0]},{self.ref_loc[1]+i}!")

    def create_graph(self, cfg, g=None, e_labels=None):
        if g is None:
            g = graphviz.Digraph("G", filename=f"{self.name}.svg")
            g.engine = "neato"
            g.attr(rankdir="LR")

        if self.place_source_nodes:
            self.place_sources(g)

        # Determine rates between all nodes aka the edge labels
        e_labels = self.label_edges(cfg, e_labels)

        g = self.create_component_graph(g, "vcxo", e_labels, cfg)

        return g, e_labels


class sys_graph:
    ...

    component_connections = {}
    converter_ref_loc = [0, 10]
    clock_ref_loc = [10, 0]

    def connect_component(self, src, dst):
        if src not in self.component_connections:
            self.component_connections[src] = []
        self.component_connections[src].append(dst)

    def create_graph(self, cfg):
        # Create blank graph
        g = graphviz.Digraph("G", filename=f"system.svg")
        g.engine = "neato"
        g.attr(rankdir="LR")
        # g.graph_attr['splines'] = 'true'
        # g.graph_attr['sep'] = '1'
        # g.attr(splines='true')
        # g.attr(sep= '1')

        # Add clock component
        self.clock.ref_loc = self.clock_ref_loc
        g, e_labels = self.clock.create_graph(cfg["clock"], g)

        # Update generic input node names of converter to reflect clock source names
        inputs = self.converter.inputs
        renamed_inputs = {}
        for input in inputs:
            clk_output = self.component_connections[input]
            input_name = f"{clk_output[0][0]}_{clk_output[0][1]}"
            renamed_inputs[input_name] = inputs[input]

        self.converter.inputs = renamed_inputs

        # Add converter(s)
        self.converter.ref_loc = self.converter_ref_loc
        self.converter.place_source_nodes = False
        g, e_labels_c = self.converter.create_graph(
            cfg[f"converter_{self.converter.name}"], g, e_labels
        )

        # Connect converter and clock chip

        # Add FPGA

        print("------------------------------")
        print("e_labels", e_labels)
        print("e_labels_c", e_labels_c)

        return g


class hmc7044_graph(graph):

    name = "HMC7044"

    g_nodes = {
        "vcxo_doubler": {"edges": ["r2"], "location": [1, 0], "type": "mult"},
        "r2": {"edges": ["pfd"], "location": [2, 0], "type": "div"},
        "pfd": {
            "edges": ["vco"],
            "location": [3, 0],
            "type": "pass",
            "show_out_rate": False,
        },
        "vco": {"edges": ["d", "n2"], "location": [4, 0], "type": "rate"},
        "d": {
            "edges": None,
            "location": [5, 0],
            "type": "div",
            "variable_node": True,
            "variable_node_extend_location": [0, -2],
            "cfg_alternative_name": "out_dividers",
        },
        "n2": {"edges": ["pfd"], "location": [3, -1], "type": "feedbackdiv"},
    }

    inputs = {"vcxo": ["vcxo_doubler"]}


if __name__ == "__main__":

    clk = hmc7044_graph()

    cfg = {
        "vcxo": 125e6,
        "r2": 3,
        "n2": 20,
        "out_dividers": [1, 2, 3, 4],
        "vcxo_doubler": 2,
        "vco": 200e6,
    }
    g = clk.create_graph(cfg)

    g.format = "svg"
    g.render(directory="doctest-output", view=True)
    print(g.source)
    # g.view()

    root = clk.generate_html("doctest-output/hmc7044.svg.svg", "hmc7044.html")

    # Create styled html
