"""Unit tests for the Adf4030Architecture wrapper class."""

from math import ceil

import pytest

from adijif.draw import Node
from adijif.plls.utils.adf4030_arch import (
    Adf4030Architecture,
    Aion_per_FPGA_cascade,
    Aion_per_FPGA_tree,
    Apollo_per_Aion_cascade,
    Apollo_per_Aion_tree,
    _connect_aions_cascade,
    _connect_aions_hybrid,
    _connect_aions_hybrid2,
    _connect_aions_tree,
)


def test_cascade_partition_matches_free_functions():
    """Class partition for cascade must equal the legacy free functions."""
    N, N_Apollo, N_FPGA = 64, 8, 1
    arch = Adf4030Architecture(
        N=N, N_Apollo=N_Apollo, N_FPGA=N_FPGA, architecture="cascade"
    )

    expected_N_Aion_UB = ceil((N_Apollo - 7) / 8) + 1
    expected_apollo_per_aion = Apollo_per_Aion_cascade(N_Apollo, expected_N_Aion_UB)
    expected_aion_per_fpga, expected_max = Aion_per_FPGA_cascade(
        expected_N_Aion_UB, N_FPGA
    )

    p = arch.partition
    assert p["N_Aion_UB"] == expected_N_Aion_UB
    assert p["N_Apollo_per_Aion"] == expected_apollo_per_aion
    assert p["N_Aion_per_FPGA"] == expected_aion_per_fpga
    assert p["Max_Aion_per_FPGA"] == expected_max
    assert p["N_UB"] == ceil(N / N_Apollo)
    assert p["N_Aion_system"] == p["N_UB"] * p["N_Aion_UB"]


def test_invalid_architecture_raises():
    with pytest.raises(ValueError, match="architecture"):
        Adf4030Architecture(N=64, N_Apollo=8, N_FPGA=1, architecture="banana")


def test_n_branch_required_for_tree():
    with pytest.raises(ValueError, match="N_branch"):
        Adf4030Architecture(
            N=64, N_Apollo=8, N_FPGA=1, architecture="tree", N_branch=None
        )


def test_n_branch_required_for_hybrid2():
    with pytest.raises(ValueError, match="N_branch"):
        Adf4030Architecture(
            N=64, N_Apollo=8, N_FPGA=1, architecture="hybrid2", N_branch=None
        )


def test_n_branch_rejected_for_cascade():
    with pytest.raises(ValueError, match="N_branch"):
        Adf4030Architecture(
            N=64, N_Apollo=8, N_FPGA=1, architecture="cascade", N_branch=3
        )


def test_n_branch_required_for_hybrid():
    with pytest.raises(ValueError, match="N_branch"):
        Adf4030Architecture(
            N=64, N_Apollo=8, N_FPGA=1, architecture="hybrid", N_branch=None
        )


def test_n_branch_must_be_positive():
    with pytest.raises(ValueError, match="positive"):
        Adf4030Architecture(
            N=64, N_Apollo=8, N_FPGA=1, architecture="tree", N_branch=0
        )


def test_tree_partition_matches_free_functions():
    N, N_Apollo, N_FPGA, N_branch = 64, 9, 1, 2
    arch = Adf4030Architecture(
        N=N, N_Apollo=N_Apollo, N_FPGA=N_FPGA,
        architecture="tree", N_branch=N_branch,
    )
    expected_N_Aion_UB = ceil((N_Apollo - 8) / 9) + 1
    p = arch.partition
    assert p["N_Aion_UB"] == expected_N_Aion_UB
    assert p["N_Apollo_per_Aion"] == Apollo_per_Aion_tree(
        N_Apollo, expected_N_Aion_UB
    )
    expected_aion_per_fpga, expected_max = Aion_per_FPGA_tree(
        expected_N_Aion_UB, N_FPGA
    )
    assert p["N_Aion_per_FPGA"] == expected_aion_per_fpga
    assert p["Max_Aion_per_FPGA"] == expected_max


def test_hybrid_partition_uses_tree_math():
    """hybrid (cascade-of-trees) shares the tree math for per-UB sizing."""
    arch = Adf4030Architecture(
        N=128, N_Apollo=9, N_FPGA=1, architecture="hybrid", N_branch=2
    )
    p = arch.partition
    assert p["N_Aion_UB"] == ceil((9 - 8) / 9) + 1


def test_hybrid2_partition_uses_tree_math_with_branches():
    arch = Adf4030Architecture(
        N=128, N_Apollo=9, N_FPGA=1, architecture="hybrid2", N_branch=2
    )
    p = arch.partition
    assert p["N_Aion_UB"] == ceil((9 - 8) / 9) + 1
    # hybrid2 carries N_branch through for the later drawing step.
    assert arch.N_branch == 2


def test_summary_contains_key_fields():
    arch = Adf4030Architecture(N=64, N_Apollo=8, N_FPGA=1, architecture="cascade")
    s = arch.summary
    assert isinstance(s, str) and s
    assert "cascade" in s
    assert "N_Aion_UB" in s
    assert "N_Apollo_per_Aion" in s
    assert "N_UB" in s


def _make_aions(n):
    return [Node(f"Aion_{i}", ntype="ic") for i in range(n)]


def test_connect_aions_cascade_is_linear():
    aions = _make_aions(4)
    conns = _connect_aions_cascade(aions)
    assert [(c["from"].name, c["to"].name) for c in conns] == [
        ("Aion_0", "Aion_1"),
        ("Aion_1", "Aion_2"),
        ("Aion_2", "Aion_3"),
    ]


def test_connect_aions_tree_one_root_n_branches():
    aions = _make_aions(5)  # 1 root + 4 leaves
    conns = _connect_aions_tree(aions, N_branch=2)
    edges = sorted((c["from"].name, c["to"].name) for c in conns)
    assert edges == [
        ("Aion_0", "Aion_1"),
        ("Aion_0", "Aion_3"),
        ("Aion_1", "Aion_2"),
        ("Aion_3", "Aion_4"),
    ]


def test_connect_aions_hybrid_is_cascade_of_trees():
    aions = _make_aions(7)
    conns = _connect_aions_hybrid(aions, N_branch=2)
    edges = {(c["from"].name, c["to"].name) for c in conns}
    assert ("Aion_0", "Aion_4") in edges
    assert len(conns) == 6


def test_connect_aions_hybrid2_is_tree_of_cascades():
    aions = _make_aions(7)
    conns = _connect_aions_hybrid2(aions, N_branch=2)
    edges = {(c["from"].name, c["to"].name) for c in conns}
    assert ("Aion_0", "Aion_1") in edges
    assert ("Aion_0", "Aion_4") in edges
    assert ("Aion_1", "Aion_2") in edges
    assert len(conns) == 6


def test_draw_ub_builds_layout_with_expected_structure(monkeypatch):
    """Build the UB layout and inspect its node/connection tree,
    without invoking the d2 renderer (which requires the d2 binding).
    """
    arch = Adf4030Architecture(
        N=8, N_Apollo=8, N_FPGA=1, architecture="cascade"
    )

    # Intercept Layout.draw() so we can grab the built Layout object
    # before rendering. We still need to exercise the construction
    # path, just not the SVG step.
    from adijif.draw import Layout
    captured = {}

    def fake_draw(self):
        captured["layout"] = self
        return "<svg/>"
    monkeypatch.setattr(Layout, "draw", fake_draw)

    svg = arch.draw(scope="ub", theme="light")
    assert svg == "<svg/>"

    lo = captured["layout"]
    assert lo.theme == "light"
    # Top-level container plus its descendants.
    assert len(lo.nodes) == 1
    ub = lo.nodes[0]
    assert ub.name.startswith("UnitBoard")
    fpgas = ub.children
    assert len(fpgas) == 1
    aions = fpgas[0].children
    expected_N_Aion_UB = arch.partition["N_Aion_UB"]
    assert len(aions) == expected_N_Aion_UB
    # Each Aion has its Apollo children.
    for aion, n_apollo in zip(aions, arch.partition["N_Apollo_per_Aion"], strict=True):
        assert len(aion.children) == n_apollo
    # Cascade -> N_Aion_UB - 1 intra-FPGA connections.
    intra_fpga = [
        c for c in fpgas[0].connections
        if c["from"].name.startswith("Aion") and c["to"].name.startswith("Aion")
    ]
    assert len(intra_fpga) == expected_N_Aion_UB - 1


def test_draw_system_contains_N_UB_unit_boards(monkeypatch):
    arch = Adf4030Architecture(
        N=64, N_Apollo=8, N_FPGA=1, architecture="cascade"
    )

    from adijif.draw import Layout
    captured = {}

    def fake_draw(self):
        captured["layout"] = self
        return "<svg/>"
    monkeypatch.setattr(Layout, "draw", fake_draw)

    arch.draw(scope="system")
    lo = captured["layout"]
    assert len(lo.nodes) == 1
    system = lo.nodes[0]
    assert system.name.startswith("System")
    # One UnitBoard subtree per N_UB.
    assert len(system.children) == arch.partition["N_UB"]
    # Each UnitBoard has its FPGA children.
    for ub in system.children:
        assert len(ub.children) == arch.N_FPGA


def test_draw_writes_svg_to_path(tmp_path, monkeypatch):
    arch = Adf4030Architecture(
        N=8, N_Apollo=8, N_FPGA=1, architecture="cascade"
    )
    from adijif.draw import Layout
    monkeypatch.setattr(Layout, "draw", lambda self: "<svg>fake</svg>")

    out = tmp_path / "ub.svg"
    svg = arch.draw(scope="ub", path=str(out))
    assert out.read_text() == "<svg>fake</svg>"
    assert svg == "<svg>fake</svg>"
