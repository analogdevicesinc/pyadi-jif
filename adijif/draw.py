"""Diagraming functions for different components."""

from __future__ import annotations

import os
from typing import Union

connection_style_types = {
    "data": {"stroke": "blue", "stroke-width": 2},
}


class Node:
    """Node model for diagraming which can have children and connections."""

    def __init__(self, name: str, ntype: str = None, parent: Node = None) -> None:
        """Initialize node with name, type and parent node.

        Args:
            name (str): Name of the node.
            ntype (str): Type of the node.
            parent (Node): Parent node of the node.
        """
        self.name = name
        self.parent = parent
        self.ntype = ntype
        self.children = []
        self.connections = []
        self.shape = "rectangle"
        self.use_unit_conversion_for_rate = True
        self._value = None

    def __repr__(self) -> str:
        """Get string representation of the node.

        Returns:
            str: String representation of the node.
        """
        return f"Node({self.name})"

    @property
    def value(self) -> str:
        """Get value of the node.

        Returns:
            str: Value of the node.
        """
        return f"{self.name} = {self._value}" if self._value else None

    @value.setter
    def value(self, value: Union(int, float, str)) -> None:
        """Set value of the node."""
        self._value = value

    def add_connection(self, connection: dict) -> None:
        """Add connection between this node and another node.

        Args:
            connection (dict): Connection dictionary with keys "from", "to",
                optionally "rate" and "style".
        """
        if "rate" in connection and self.use_unit_conversion_for_rate:
            units = ["Hz", "kHz", "MHz", "GHz"]
            rate = connection["rate"]
            # Convert to unit based on rate scale
            for unit in units:
                if rate < 1000:
                    connection["rate"] = f"{rate:.2f} {unit}"
                    break
                rate /= 1000

        self.connections.append(connection)

    def get_connection(self, from_s: str, to: str) -> dict:
        """Get connection between this node and another node.

        Args:
            from_s (str): Name of the node from which connection originates.
            to (str): Name of the node to which connection goes.

        Returns:
            dict: Connection dictionary with keys "from", "to" and optionally "rate".

        Raises:
            ValueError: If connection not found.
        """
        for conn in self.connections:
            if conn["from"].name == from_s and conn["to"].name == to:
                return conn
        raise ValueError(f"Connection from {from_s} to {to} not found.")

    def remove_connection(self, from_s: str, to: str) -> None:
        """Remove connection between this node and another node.

        Args:
            from_s (str): Name of the node from which connection originates.
            to (str): Name of the node to which connection goes.

        Raises:
            ValueError: If connection not found.
        """
        conn_to_remove = None
        for conn in self.connections:
            if conn["from"].name == from_s and conn["to"].name == to:
                conn_to_remove = conn
                break
        if conn_to_remove:
            self.connections.remove(conn_to_remove)
            return
        raise ValueError(f"Connection from {from_s} to {to} not found.")

    def update_connection(self, from_s: str, to: str, rate: Union(int, float)) -> None:
        """Update connection rate between this node and another node.

        Args:
            from_s (str): Name of the node from which connection originates.
            to (str): Name of the node to which connection goes.
            rate (float): Rate of the connection.

        Raises:
            ValueError: If connection not found.
        """
        for conn in self.connections:
            if conn["from"].name == from_s and conn["to"].name == to:
                units = ["Hz", "kHz", "MHz", "GHz"]
                # Convert to unit based on rate scale
                for unit in units:
                    if rate < 1000:
                        conn["rate"] = f"{rate:.2f} {unit}"
                        return
                    rate /= 1000

        raise ValueError(f"Connection from {from_s} to {to} not found.")

    def add_child(self, child: Node) -> None:
        """Add child node to this node.

        Args:
            child (Node): Child node to add.
        """
        if not isinstance(child, list):
            child = [child]
        for c in child:
            c.parent = self
            self.children.append(c)

    def get_child(self, name: str) -> Node:
        """Get child node by name.

        Args:
            name (str): Name of the child node.

        Returns:
            Node: Child node with the given name.

        Raises:
            ValueError: If child node not found.
        """
        for child in self.children:
            if child.name == name:
                return child
        raise ValueError(f"Child with name {name} not found.")

    def remove_child(self, name: str) -> None:
        """Remove child node by name.

        Args:
            name (str): Name of the child node to remove.
        """
        # Remove connections with the child first
        connections_to_keep = []
        for conn in self.connections:
            if conn["to"].name != name:
                connections_to_keep.append(conn)
        self.connections = connections_to_keep
        connections_to_keep = []
        for conn in self.connections:
            if conn["from"].name != name:
                connections_to_keep.append(conn)
        self.connections = connections_to_keep

        children_to_keep = []
        for child in self.children:
            if child.name != name:
                children_to_keep.append(child)
        self.children = children_to_keep


class Layout:
    """Layout model for diagraming which contains nodes and connections."""

    si = "    "
    use_d2_cli = False
    _write_out_d2_file = True

    def __init__(self, name: str) -> None:
        """Initialize layout with name.

        Args:
            name (str): Name of the layout.
        """
        self.name = name
        self.nodes = []
        self.connections = []
        self.use_unit_conversion_for_rate = True
        self.output_filename = "clocks.d2"
        self.output_image_filename = "clocks.svg"
        self.layout_engine = "elk"
        self.show_rates = True

    def add_node(self, node: Node) -> None:
        """Add node to the layout.

        Args:
            node (Node): Node to add to the layout.
        """
        self.nodes.append(node)

    def remove_node(self, name: str) -> None:
        """Remove node by name.

        Args:
            name (str): Name of the node to remove.
        """
        # Remove connections with the node first
        connections_to_keep = []
        for conn in self.connections:
            if conn["to"].name != name:
                connections_to_keep.append(conn)
        self.connections = connections_to_keep
        connections_to_keep = []
        for conn in self.connections:
            if conn["from"].name != name:
                connections_to_keep.append(conn)
        self.connections = connections_to_keep

        nodes_to_keep = []
        for node in self.nodes:
            if node.name != name:
                nodes_to_keep.append(node)
        self.nodes = nodes_to_keep

    def add_connection(self, connection: dict) -> None:
        """Add connection between two nodes.

        Args:
            connection (dict): Connection dictionary with keys "from", "to"
                and optionally "rate".
        """
        if "rate" in connection and self.use_unit_conversion_for_rate:
            units = ["Hz", "kHz", "MHz", "GHz"]
            rate = connection["rate"]
            # Convert to unit based on rate scale
            for unit in units:
                if rate < 1000:
                    connection["rate"] = f"{rate:.2f} {unit}"
                    break
                rate /= 1000
        self.connections.append(connection)

    def get_connection(
        self, from_s: str = None, to: str = None
    ) -> Union[dict, list[dict]]:
        """Get connection between two nodes.

        Args:
            from_s (str): Name of the node from which connection originates.
            to (str): Name of the node to which connection goes.

        Returns:
            List[dict] or dict: List of or single Connection dictionary with
              keys "from", "to" and optionally "rate".

        Raises:
            ValueError: If connection not found.
        """
        if from_s is None and to is None:
            raise ValueError("Both from and to cannot be None.")
        found = []
        if from_s is None:
            for conn in self.connections:
                if conn["to"].name == to:
                    found.append(conn)
            return found
        if to is None:
            for conn in self.connections:
                if conn["from"].name == from_s:
                    found.append(conn)
            return found
        for conn in self.connections:
            if conn["from"].name == from_s and conn["to"].name == to:
                return conn

    def get_node(self, name: str) -> Node:
        """Get node by name.

        Args:
            name (str): Name of the node.

        Returns:
            Node: Node with the given name.

        Raises:
            ValueError: If node not found.
        """
        for node in self.nodes:
            if node.name == name:
                return node
        raise ValueError(f"Node with name {name} not found.")

    def draw(self) -> str:
        """Draw diagram in d2 language.

        Returns:
            str: Path to the output image file.
        """
        diag = "direction: right\n\n"

        def apply_connection_style(diag: str, connection: dict) -> str:
            """Apply style to the connection in the diagram.

            Args:
                diag (str): Current diagram string.
                connection (dict): Connection dictionary with keys "from", "to",
                    and optionally "style".

            Returns:
                str: Updated diagram string with applied style.
            """
            from_p_name = get_parents_names(connection["from"])
            to_p_name = get_parents_names(connection["to"])

            if "type" in connection and connection["type"] in connection_style_types:
                style = connection_style_types[connection["type"]]
                index = 0  # Default index but make sure its not in the diag
                for key in style:
                    while True:
                        con_str = f"({from_p_name}{connection['from'].name} -> "
                        con_str += f"{to_p_name}{connection['to'].name})[{index}]"
                        con_str += f".style.{key}: {style[key]}\n"
                        if con_str not in diag:
                            diag += con_str
                            break
                        index += 1  # Increment index to avoid duplicates
                        # Duplicates can happen if multiple connections
                        # between the same nodes

            index = 0
            if "index" in connection:
                index = connection["index"]
            if "style" in connection:
                for key in connection["style"]:
                    diag += f"({from_p_name}{connection['from'].name} -> "
                    diag += f"{to_p_name}{connection['to'].name})[{index}]"
                    diag += f".style.{key}: {connection['style'][key]}\n"
            return diag

        def get_parents_names(node: Node) -> str:
            """Get names of all parent nodes of the given node.

            Args:
                node (Node): Node for which to get parent names.

            Returns:
                str: Names of all parent nodes of the given node.
            """
            parents = []
            while node.parent:
                parents.append(node.parent.name)
                node = node.parent
            if not parents:
                return ""
            return ".".join(parents[::-1]) + "."

        def draw_subnodes(node: Node, spacing: str = "    ") -> str:
            """Draw subnodes of the given node.

            Args:
                node (Node): Node for which to draw subnodes.
                spacing (str): Spacing for indentation.

            Returns:
                str: Subnodes of the given node.
            """
            diag = " {\n"
            for child in node.children:
                if child.value:
                    diag += spacing + child.name + f": {{tooltip: {child.value} }}"
                else:
                    diag += spacing + child.name
                if child.children:
                    diag += draw_subnodes(child, spacing + "    ")
                else:
                    diag += "\n"
                diag += spacing + child.name + ".shape: " + child.shape + "\n"
            lr = len("    ")
            diag += spacing[:-lr] + "}\n"
            return diag

        # Add all nodes
        for node in self.nodes:
            diag += f"{node.name}"
            if node.children:
                diag += draw_subnodes(node)
            diag += "\n"

        diag += "\n"

        # # Set shapes
        # for node in self.nodes:
        #     parents_string = get_parents_names(node)
        #     diag += f"{parents_string}{node.name}.shape = {node.shape}\n"

        # diag += "\n"

        # Add all connections
        for connection in self.connections:
            from_p_name = get_parents_names(connection["from"])
            to_p_name = get_parents_names(connection["to"])
            if self.show_rates:
                label = f"{connection['rate']}" if "rate" in connection else None
            else:
                label = None
            diag += f"{from_p_name}{connection['from'].name} ->"
            diag += f" {to_p_name}{connection['to'].name}"
            diag += ": " + label if label else ""
            diag += "\n"
            diag = apply_connection_style(diag, connection)

        def draw_nodes_connections(nodes: list[Node], show_rates: bool) -> str:
            """Draw connections between nodes.

            Args:
                nodes (list[Node]): List of nodes to draw connections between.
                show_rates (bool): Whether to show rates in the diagram.

            Returns:
                str: Connections between nodes.
            """
            diag = ""
            for node in nodes:
                for connection in node.connections:
                    from_p_name = get_parents_names(connection["from"])
                    to_p_name = get_parents_names(connection["to"])
                    if show_rates:
                        label = f"{connection['rate']}" if "rate" in connection else ""
                    else:
                        label = ""
                    diag += f"{from_p_name}{connection['from'].name} -> "
                    diag += f"{to_p_name}{connection['to'].name}"
                    diag += ": " + label if label else ""
                    diag += "\n"
                    diag = apply_connection_style(diag, connection)

                if node.children:
                    diag += draw_nodes_connections(node.children, show_rates)

            return diag

        # for node in self.nodes:
        diag += draw_nodes_connections(self.nodes, show_rates=self.show_rates)

        # for node in self.nodes:
        #     for connection in node.connections:
        #         from_p_name = get_parents_names(connection["from"])
        #         to_p_name = get_parents_names(connection["to"])
        #         label = f"{connection['rate']}" if "rate" in connection else ""
        #         diag += f"{from_p_name}{connection['from'].name} -> "
        #         diag += f"{to_p_name}{connection['to'].name}"
        #         diag += ": " + label if label else ""
        #         diag += "\n"

        if self.use_d2_cli:
            with open(self.output_filename, "w") as f:
                f.write(diag)

            cmd = (
                f"d2 --theme=0 --dark-theme=200 -l {self.layout_engine} "
                + f"{self.output_filename} "
            )
            cmd += f"{self.output_image_filename}"
            os.system(cmd)  # noqa: S605
            return self.output_image_filename
        else:
            if self._write_out_d2_file:
                with open(self.output_filename, "w") as f:
                    f.write(diag)
                print(f"Saved to {self.output_filename}")

            # Use bindings
            from .d2 import compile

            out = compile(diag)
            # with open(self.output_image_filename, "w") as f:
            #     f.write(out)

            # return self.output_image_filename
            return out
