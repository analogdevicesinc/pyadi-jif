"""Utility functions for ADF4030 architecture calculations."""

from math import ceil, floor

from adijif.draw import Layout, Node


def convert_sec_into_hms(time: float) -> str:
    """Convert time in seconds into hours, minutes, seconds, and milliseconds format.

    Args:
        time (float): Time in seconds to be converted.

    Returns:
        str: Formatted string in the format "HH:MM:SS:mmm".
    """
    hours = floor(time / 3600)
    minutes = floor((time % 3600) / 60)
    remaining_sec = floor(time % 60)
    remaining_msec = time - hours * 3600 - minutes * 60 - remaining_sec
    return "%02d:%02d:%02d:%.3f" % (hours, minutes, remaining_sec, remaining_msec)


def Apollo_per_Aion_cascade(N_Apollo: int, N_Aion_UB_cascade: int) -> list:
    """Calculate the number of Apollo devices per Aion in a cascade architecture.

    For a cascade architecture, this function distributes Apollo devices among Aion
    devices on the Unit Board.

    Args:
        N_Apollo (int): The number of Apollo devices per Unit Board.
        N_Aion_UB_cascade (int): The number of Aion devices per Unit Board.

    Returns:
        list: A list containing the number of Apollo devices per Aion on the Unit Board.
    """
    N_Apollo_per_Aion_cascade = []
    temp = 0
    temp0 = ceil(N_Apollo / N_Aion_UB_cascade)
    if temp0 == 8:
        N_Apollo_per_Aion_cascade.append(7)
        temp = temp + 7
    else:
        N_Apollo_per_Aion_cascade.append(temp0)
        temp = temp + temp0

    for _ in range(1, N_Aion_UB_cascade - 1):
        temp = temp + temp0
        N_Apollo_per_Aion_cascade.append(temp0)

    N_Apollo_per_Aion_cascade.append(N_Apollo - temp)

    return N_Apollo_per_Aion_cascade


def Apollo_per_Aion_tree(N_Apollo: int, N_Aion_UB_tree: int) -> list:
    """Calculate the number of Apollo devices per Aion in a tree architecture.

    For a tree architecture, this function distributes Apollo devices among Aion
    devices on the Unit Board.

    Args:
        N_Apollo (int): The number of Apollo devices per Unit Board.
        N_Aion_UB_tree (int): The number of Aion devices per Unit Board.

    Returns:
        list: A list containing the number of Apollo devices per Aion on the Unit Board.
    """
    N_Apollo_per_Aion_tree = []
    temp = 0
    temp0 = ceil(N_Apollo / N_Aion_UB_tree)
    if temp0 == 9:
        N_Apollo_per_Aion_tree.append(8)
        temp = temp + 8
    else:
        N_Apollo_per_Aion_tree.append(temp0)
        temp = temp + temp0

    for _ in range(1, N_Aion_UB_tree - 1):
        temp = temp + temp0
        N_Apollo_per_Aion_tree.append(temp0)

    N_Apollo_per_Aion_tree.append(N_Apollo - temp)

    return N_Apollo_per_Aion_tree


def Aion_per_FPGA_cascade(N_Aion_UB_cascade: int, N_FPGA: int) -> tuple[list, int]:
    """Calculate Aion device distribution among FPGAs in a cascade architecture.

    This function determines how many Aion devices are managed by each FPGA
    on the Unit Board and finds the maximum number of Aion devices per FPGA.

    Args:
        N_Aion_UB_cascade (int): Number of Aion devices per Unit Board.
        N_FPGA (int): Number of FPGA devices on a Unit Board.

    Returns:
        tuple: A tuple containing:
            - list: How many Aion devices are managed by each FPGA on the Unit
              Board.
            - int: The maximum number of Aion devices managed by any FPGA on the
              Unit Board.
    """
    N_Aion_per_FPGA_cascade = []
    if (ceil(N_Aion_UB_cascade / N_FPGA) - 1) != 0:
        X = int((N_Aion_UB_cascade - N_FPGA) / (ceil(N_Aion_UB_cascade / N_FPGA) - 1))
        for _ in range(0, X):
            N_Aion_per_FPGA_cascade.append(ceil(N_Aion_UB_cascade / N_FPGA))
        for _ in range(X, N_FPGA):
            N_Aion_per_FPGA_cascade.append(
                int(
                    (N_Aion_UB_cascade - ceil(N_Aion_UB_cascade / N_FPGA) * X)
                    / (N_FPGA - X)
                )
            )
    else:
        for _ in range(0, N_Aion_UB_cascade):
            N_Aion_per_FPGA_cascade.append(1)
    Max_Aion_per_FPGA_cascade = 0
    for index in range(0, N_FPGA):
        Max_Aion_per_FPGA_cascade = max(
            Max_Aion_per_FPGA_cascade, N_Aion_per_FPGA_cascade[index]
        )
    return (N_Aion_per_FPGA_cascade, Max_Aion_per_FPGA_cascade)


def Aion_per_FPGA_tree(N_Aion_UB_tree: int, N_FPGA: int) -> tuple[list, int]:
    """Calculate Aion device distribution among FPGAs in a tree architecture.

    This function determines how many Aion devices are managed by each FPGA
    on the Unit Board and finds the maximum number of Aion devices per FPGA.

    Args:
        N_Aion_UB_tree (int): Number of Aion devices per Unit Board.
        N_FPGA (int): Number of FPGA devices on a Unit Board.

    Returns:
        tuple: A tuple containing:
            - list: How many Aion devices are managed by each FPGA on the Unit
              Board.
            - int: The maximum number of Aion devices managed by any FPGA on
              the Unit Board.
    """
    N_Aion_per_FPGA_tree = []
    if (ceil(N_Aion_UB_tree / N_FPGA) - 1) != 0:
        X = int((N_Aion_UB_tree - N_FPGA) / (ceil(N_Aion_UB_tree / N_FPGA) - 1))
        for _ in range(0, X):
            N_Aion_per_FPGA_tree.append(ceil(N_Aion_UB_tree / N_FPGA))
        for _ in range(X, N_FPGA):
            N_Aion_per_FPGA_tree.append(
                int((N_Aion_UB_tree - ceil(N_Aion_UB_tree / N_FPGA) * X) / (N_FPGA - X))
            )
    else:
        for _ in range(0, N_Aion_UB_tree):
            N_Aion_per_FPGA_tree.append(1)
    Max_Aion_per_FPGA_tree = 0
    for index in range(0, N_FPGA):
        Max_Aion_per_FPGA_tree = max(
            Max_Aion_per_FPGA_tree, N_Aion_per_FPGA_tree[index]
        )
    return (N_Aion_per_FPGA_tree, Max_Aion_per_FPGA_tree)


def _connect_aions_cascade(aions: list) -> list:
    """Linear daisy chain: Aion_i -> Aion_{i+1}."""
    return [
        {"from": aions[i], "to": aions[i + 1]}
        for i in range(len(aions) - 1)
    ]


def _split_branches(n_leaves: int, N_branch: int) -> list[int]:
    """Distribute ``n_leaves`` across ``N_branch`` branches (ceil/floor split)."""
    base, extra = divmod(n_leaves, N_branch)
    return [base + (1 if i < extra else 0) for i in range(N_branch)]


def _connect_aions_tree(aions: list, N_branch: int) -> list:
    """One root Aion (index 0); remaining Aions split across N_branch branches.

    Each branch is a linear cascade hanging off the root.
    """
    if not aions:
        return []
    root = aions[0]
    leaves = aions[1:]
    branch_lens = _split_branches(len(leaves), N_branch)
    conns: list = []
    cursor = 0
    for length in branch_lens:
        if length == 0:
            continue
        branch = leaves[cursor : cursor + length]
        conns.append({"from": root, "to": branch[0]})
        for i in range(len(branch) - 1):
            conns.append({"from": branch[i], "to": branch[i + 1]})
        cursor += length
    return conns


def _connect_aions_hybrid(aions: list, N_branch: int) -> list:
    """Cascade-of-trees: outer linear chain between branch roots.

    Within each branch, a linear cascade from the branch root.

    The inner "tree" is degenerate (one inner branch == linear), which
    is the natural fit when N_branch only controls the outer count.
    """
    if not aions:
        return []
    branch_lens = _split_branches(len(aions), N_branch)
    conns: list = []
    branch_roots: list = []
    cursor = 0
    for length in branch_lens:
        if length == 0:
            continue
        branch = aions[cursor : cursor + length]
        branch_roots.append(branch[0])
        # Inside the branch, treat it as a tree with a single inner
        # branch: root -> all leaves linearly.
        for i in range(len(branch) - 1):
            conns.append({"from": branch[i], "to": branch[i + 1]})
        cursor += length
    # Outer cascade between branch roots.
    for i in range(len(branch_roots) - 1):
        conns.append({"from": branch_roots[i], "to": branch_roots[i + 1]})
    return conns


def _connect_aions_hybrid2(aions: list, N_branch: int) -> list:
    """Tree-of-cascades: outer tree (root fans out to branch heads).

    Within each branch, a linear cascade.
    """
    if not aions:
        return []
    root = aions[0]
    rest = aions[1:]
    branch_lens = _split_branches(len(rest), N_branch)
    conns: list = []
    cursor = 0
    for length in branch_lens:
        if length == 0:
            continue
        branch = rest[cursor : cursor + length]
        conns.append({"from": root, "to": branch[0]})
        for i in range(len(branch) - 1):
            conns.append({"from": branch[i], "to": branch[i + 1]})
        cursor += length
    return conns


ARCHITECTURES = ("cascade", "tree", "hybrid", "hybrid2")


class Adf4030Architecture:
    """Partition descriptor for an ADF4030 (Aion) clock-distribution system.

    Wraps the free-function partition helpers in this module with a
    single cached object exposing the resulting partition dict, a
    human-readable summary string, and a ``draw(scope=...)`` method
    that returns a d2-rendered SVG diagram.
    """

    def __init__(
        self,
        N: int,
        N_Apollo: int,
        N_FPGA: int,
        architecture: str,
        N_branch: int | None = None,
    ) -> None:
        """Initialize an architecture descriptor.

        Args:
            N: Total Apollo devices in the system.
            N_Apollo: Apollo devices per Unit Board.
            N_FPGA: FPGA devices per Unit Board.
            architecture: One of ``"cascade"``, ``"tree"``, ``"hybrid"``,
                ``"hybrid2"``.
            N_branch: Number of branches; required (and must be >= 1) for
                ``"tree"``, ``"hybrid"``, and ``"hybrid2"``; rejected
                otherwise.
        """
        if architecture not in ARCHITECTURES:
            raise ValueError(
                f"Unknown architecture {architecture!r}. "
                f"Must be one of {ARCHITECTURES}."
            )
        requires_branches = architecture in ("tree", "hybrid", "hybrid2")
        if requires_branches and (N_branch is None or N_branch < 1):
            raise ValueError(
                f"N_branch must be a positive integer for "
                f"architecture={architecture!r} (got {N_branch!r})."
            )
        if not requires_branches and N_branch is not None:
            raise ValueError(
                f"N_branch must be None for architecture={architecture!r}."
            )
        self.N = N
        self.N_Apollo = N_Apollo
        self.N_FPGA = N_FPGA
        self.architecture = architecture
        self.N_branch = N_branch
        self._partition: dict | None = None

    @property
    def partition(self) -> dict:
        """Lazily compute and cache the partition dict."""
        if self._partition is None:
            self._partition = self._compute_partition()
        return self._partition

    @property
    def summary(self) -> str:
        """Plain-text summary of the partition.

        Mirrors the rough shape of the textual report the example
        script produces, formatted as one fact per line.
        """
        p = self.partition
        lines = [
            f"Architecture: {self.architecture}",
            f"N (total Apollo devices): {self.N}",
            f"N_Apollo (per Unit Board): {self.N_Apollo}",
            f"N_FPGA (per Unit Board): {self.N_FPGA}",
            f"N_Aion_UB: {p['N_Aion_UB']}",
            f"N_Apollo_per_Aion: {p['N_Apollo_per_Aion']}",
            f"N_Aion_per_FPGA: {p['N_Aion_per_FPGA']}",
            f"Max_Aion_per_FPGA: {p['Max_Aion_per_FPGA']}",
            f"N_UB: {p['N_UB']}",
            f"N_Aion_system: {p['N_Aion_system']}",
        ]
        if self.N_branch is not None:
            lines.insert(1, f"N_branch: {self.N_branch}")
        return "\n".join(lines)

    _AION_CONNECT_DISPATCH = {
        "cascade": (_connect_aions_cascade, False),
        "tree":    (_connect_aions_tree,    True),
        "hybrid":  (_connect_aions_hybrid,  True),
        "hybrid2": (_connect_aions_hybrid2, True),
    }

    def _build_unit_board_node(self, name: str) -> Node:
        """Construct one UnitBoard subtree (FPGAs / Aions / Apollos).

        Builds the hierarchy with intra-FPGA Aion connections per the chosen
        architecture.
        """
        p = self.partition
        ub = Node(name, ntype="board")
        helper, needs_branch = self._AION_CONNECT_DISPATCH[self.architecture]
        aion_cursor = 0
        for fpga_i in range(self.N_FPGA):
            fpga = Node(f"FPGA_{fpga_i}", ntype="fpga")
            ub.add_child(fpga)
            n_aions_here = p["N_Aion_per_FPGA"][fpga_i]
            aions: list = []
            for _j in range(n_aions_here):
                aion = Node(f"Aion_{aion_cursor}", ntype="ic")
                aions.append(aion)
                fpga.add_child(aion)
                n_apollo = p["N_Apollo_per_Aion"][aion_cursor]
                for k in range(n_apollo):
                    apollo = Node(
                        f"Apollo_{aion_cursor}_{k}", ntype="converter"
                    )
                    aion.add_child(apollo)
                    aion.add_connection({"from": aion, "to": apollo})
                aion_cursor += 1
            # FPGA -> first (root) Aion: reference clock edge.
            if aions:
                fpga.add_connection({"from": fpga, "to": aions[0]})
            # Intra-FPGA Aion topology.
            if needs_branch:
                conns = helper(aions, N_branch=self.N_branch)
            else:
                conns = helper(aions)
            for c in conns:
                fpga.add_connection(c)
        return ub

    def draw(self, scope: str = "ub", path: str | None = None) -> str:
        """Render the architecture as an SVG diagram.

        Args:
            scope: ``"ub"`` for one Unit Board, ``"system"`` for the
                full multi-Unit-Board diagram.
            path: If set, also write the rendered SVG to this file.

        Returns:
            SVG content as a string.

        Raises:
            ValueError: ``scope`` is not ``"ub"`` or ``"system"``.
        """
        if scope not in ("ub", "system"):
            raise ValueError(
                f"scope must be 'ub' or 'system', got {scope!r}"
            )
        lo = Layout(f"ADF4030 {self.architecture} ({scope})")
        if scope == "ub":
            lo.add_node(self._build_unit_board_node("UnitBoard"))
        else:
            # scope == "system": filled in by Task 7.
            raise NotImplementedError("system scope not yet implemented")
        svg = lo.draw()
        if path is not None:
            with open(path, "w") as f:
                f.write(svg)
        return svg

    def _compute_partition(self) -> dict:
        if self.architecture == "cascade":
            N_Aion_UB = ceil((self.N_Apollo - 7) / 8) + 1
            N_Apollo_per_Aion = Apollo_per_Aion_cascade(self.N_Apollo, N_Aion_UB)
            N_Aion_per_FPGA, Max_Aion_per_FPGA = Aion_per_FPGA_cascade(
                N_Aion_UB, self.N_FPGA
            )
        else:
            # tree, hybrid, and hybrid2 all use the tree-shaped per-UB
            # sizing (each Aion has 9 usable channels, not 8).
            N_Aion_UB = ceil((self.N_Apollo - 8) / 9) + 1
            N_Apollo_per_Aion = Apollo_per_Aion_tree(self.N_Apollo, N_Aion_UB)
            N_Aion_per_FPGA, Max_Aion_per_FPGA = Aion_per_FPGA_tree(
                N_Aion_UB, self.N_FPGA
            )
        N_UB = ceil(self.N / self.N_Apollo)
        return {
            "N_Aion_UB": N_Aion_UB,
            "N_Apollo_per_Aion": N_Apollo_per_Aion,
            "N_Aion_per_FPGA": N_Aion_per_FPGA,
            "Max_Aion_per_FPGA": Max_Aion_per_FPGA,
            "N_UB": N_UB,
            "N_Aion_system": N_UB * N_Aion_UB,
        }
