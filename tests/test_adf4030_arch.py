"""Unit tests for the Adf4030Architecture wrapper class."""

from math import ceil

import pytest

from adijif.plls.utils.adf4030_arch import (
    Adf4030Architecture,
    Aion_per_FPGA_cascade,
    Apollo_per_Aion_cascade,
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
