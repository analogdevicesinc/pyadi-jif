"""Unit tests for the Adf4030Architecture wrapper class."""

from math import ceil

import pytest

from adijif.plls.utils.adf4030_arch import (
    Adf4030Architecture,
    Aion_per_FPGA_cascade,
    Aion_per_FPGA_tree,
    Apollo_per_Aion_cascade,
    Apollo_per_Aion_tree,
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
