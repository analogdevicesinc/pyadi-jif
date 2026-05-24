"""Utility functions for ADF4030 architecture calculations."""

from math import ceil, floor


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

    def _compute_partition(self) -> dict:
        if self.architecture == "cascade":
            N_Aion_UB = ceil((self.N_Apollo - 7) / 8) + 1
            N_Apollo_per_Aion = Apollo_per_Aion_cascade(self.N_Apollo, N_Aion_UB)
            N_Aion_per_FPGA, Max_Aion_per_FPGA = Aion_per_FPGA_cascade(
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
        raise NotImplementedError(
            f"Architecture {self.architecture!r} not yet implemented"
        )
