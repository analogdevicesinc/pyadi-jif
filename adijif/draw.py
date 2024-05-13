"""Diagraming functions for different componets."""
import os


class Node:
    def __init__(self, name, ntype=None, parent=None):
        self.name = name
        self.parent = parent
        self.ntype = ntype
        self.children = []
        self.connections = []
        self.shape = "rectangle"
        self.use_unit_conversion_for_rate = True
        self._value = None

    def __repr__(self):
        return f"Node({self.name})"

    @property
    def value(self):
        return f"{self.name} = {self._value}" if self._value else None

    @value.setter
    def value(self, value):
        self._value = value

    def add_connection(self, connection: dict):
        if "rate" in connection and self.use_unit_conversion_for_rate:
            units = ["Hz", "kHz", "MHz", "GHz"]
            rate = connection["rate"]
            # Convert to unit based on rate scale
            for i, unit in enumerate(units):
                if rate < 1000:
                    break
                rate /= 1000
            connection["rate"] = f"{rate:.2f} {unit}"

        self.connections.append(connection)

    def get_connection(self, from_s, to):
        for conn in self.connections:
            if conn["from"].name == from_s and conn["to"].name == to:
                return conn
        raise ValueError(f"Connection from {from_s} to {to} not found.")

    def update_connection(self, from_s, to, rate):
        for conn in self.connections:
            if conn["from"].name == from_s and conn["to"].name == to:
                units = ["Hz", "kHz", "MHz", "GHz"]
                # Convert to unit based on rate scale
                for i, unit in enumerate(units):
                    if rate < 1000:
                        break
                    rate /= 1000
                conn["rate"] = f"{rate:.2f} {unit}"
                return

        raise ValueError(f"Connection from {from_s} to {to} not found.")

    def add_child(self, child):
        if not isinstance(child, list):
            child = [child]
        for c in child:
            c.parent = self
            self.children.append(c)

    def get_child(self, name: str):
        for child in self.children:
            if child.name == name:
                return child
        raise ValueError(f"Child with name {name} not found.")


class Layout:

    si = "    "

    def __init__(self, name: str):
        self.name = name
        self.nodes = []
        self.connections = []
        self.use_unit_conversion_for_rate = True
        self.output_filename = "clocks.d2"
        self.output_image_filename = "clocks.png"
        self.layout_engine = "elk"

    def add_node(self, node: Node):
        self.nodes.append(node)

    def add_connection(self, connection: dict):
        if "rate" in connection and self.use_unit_conversion_for_rate:
            units = ["Hz", "kHz", "MHz", "GHz"]
            rate = connection["rate"]
            # Convert to unit based on rate scale
            for i, unit in enumerate(units):
                if rate < 1000:
                    break
                rate /= 1000
            connection["rate"] = f"{rate:.2f} {unit}"
        self.connections.append(connection)

    def draw(self):
        """Draw diagram in d2 language."""

        diag = "direction: right\n\n"

        def get_parents_names(node):
            parents = []
            while node.parent:
                parents.append(node.parent.name)
                node = node.parent
            if not parents:
                return ""
            return ".".join(parents[::-1]) + "."

        def draw_subnodes(node, spacing="    "):
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
            label = f"{connection['rate']}" if "rate" in connection else None
            diag += f"{from_p_name}{connection['from'].name} -> {to_p_name}{connection['to'].name}"
            diag += ": " + label if label else ""
            diag += "\n"

        for node in self.nodes:
            for connection in node.connections:
                from_p_name = get_parents_names(connection["from"])
                to_p_name = get_parents_names(connection["to"])
                label = f"{connection['rate']}" if "rate" in connection else ""
                diag += f"{from_p_name}{connection['from'].name} -> {to_p_name}{connection['to'].name}"
                diag += ": " + label if label else ""
                diag += "\n"

        with open(self.output_filename, "w") as f:
            f.write(diag)

        os.system(
            f"d2 -l {self.layout_engine} {self.output_filename} {self.output_image_filename}"
        )

        return self.output_image_filename
