from turtle import bgcolor
import graphviz
from typing import List
import os
from jinja2 import Environment, FileSystemLoader
import lxml.etree as ET


class graph:

    connections: dict = {}
    inputs: List[str] = []

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

    def create_component_graph(self, g: graphviz.Digraph, source_name: str):

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
                sg.node(
                    node,
                    label=label,
                    shape="square",
                    pos=f"{loc[0]*scale_x},{loc[1]*scale_y}!",
                    width="1",
                    style="filled",
                    bgcolor="grey",
                    id=node,
                )
                locations_x.append(loc[0] * scale_x)
                locations_y.append(loc[1] * scale_y)

            # Add hidden nodes to create margin around subgraph
            margin = 0.5
            x = min(locations_x)
            y = max(locations_y)
            a = max(locations_x)
            b = min(locations_y)
            sg.node(
                "EDGE0",
                shape="square",
                pos=f"{x-margin},{y+margin}!",
                width="1",
                style="invis",
            )
            sg.node(
                "EDGE1",
                shape="square",
                pos=f"{a+margin},{b-margin}!",
                width="1",
                style="invis",
            )

            # Connect nodes together
            for node in connections:
                if connections[node]["edges"]:
                    for connected_node in connections[node]["edges"]:
                        sg.edge(node, connected_node, label="100 MHz")

        # Connect input
        g.edge(source_name, "vcxo_doubler")

        return g


class hmc7044_graph(graph):

    name = "HMC7044"

    g_nodes = {
        "vcxo_doubler": {"edges": ["r2"], "location": [1, 0]},
        "r2": {"edges": ["vco"], "location": [2, 0]},
        "vco": {"edges": ["d", "n2"], "location": [3, 0]},
        "d": {"edges": None, "location": [4, 0]},
        "n2": {"edges": ["r2"], "location": [2, -1]},
    }

    # connections = {
    #     "vcxo": ["vcxo_doubler"],
    #     "vcxo_doubler": ["r2"],
    #     "r2": ["vco"],
    #     "vco": ["d", "n2"],
    #     "n2": ["r2"],
    # }

    inputs = ["vcxo"]


if __name__ == "__main__":

    g = graphviz.Digraph("G", filename="hmc7044.svg")
    g.engine = "neato"
    g.attr(rankdir="LR")

    n = g.node("vcxo", pos="0,0!")
    print(n)

    clk = hmc7044_graph()
    g = clk.create_component_graph(g, "vcxo")
    print(g.source)
    # g.view()
    g.format = "svg"
    g.render(directory="doctest-output", view=True)

    root = clk.generate_html("doctest-output/hmc7044.svg.svg", "hmc7044.html")

    # Create styled html
