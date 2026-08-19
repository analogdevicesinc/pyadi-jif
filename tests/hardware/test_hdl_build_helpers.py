"""Unit tests for the xcvr_wizard HDL build helpers (no Vivado needed)."""

from __future__ import annotations

from adijif.fpgas.xilinx.xgt_wizard import XgtWizardConfig, XgtWizardLink

from .hdl_build import wizard_builds


def _cfg(tx=None, rx=None, jesd_mode="64B66B", gt="GTHE4"):
    return XgtWizardConfig(
        jesd_mode=jesd_mode, tx=tx, rx=rx, transceiver_type=gt
    )


def _link(rate, ref, pll, lanes=4):
    return XgtWizardLink(
        lane_rate_gbps=rate, ref_clk_mhz=ref, pll_type=pll, num_lanes=lanes
    )


def test_asymmetric_config_yields_two_builds():
    cfg = _cfg(
        tx=_link(23.925, 362.5, "QPLL0"), rx=_link(11.9625, 362.5, "QPLL1")
    )
    builds = wizard_builds(cfg, "/opt/hdl", carrier="zcu102")

    assert len(builds) == 2
    tx, rx = builds
    assert tx.argv == [
        "make",
        "-C",
        "/opt/hdl/projects/xcvr_wizard/zcu102",
        "LANE_RATE=23.925",
        "REF_CLK=362.5",
        "PLL_TYPE=QPLL0",
    ]
    assert rx.argv[3:] == [
        "LANE_RATE=11.9625",
        "REF_CLK=362.5",
        "PLL_TYPE=QPLL1",
    ]
    # The make wrapper builds into a parameter-token subdirectory (e.g.
    # RATE23_925_REFCLK362_5_PLLTYPEQPLL1/), so the artifact is located by
    # globbing under the project dir rather than by a fixed path.
    assert str(tx.project_dir) == "/opt/hdl/projects/xcvr_wizard/zcu102"
    assert tx.cfng_name == "GTHE4_cfng.txt"


def test_symmetric_config_yields_one_build():
    link = _link(10.0, 250.0, "QPLL0")
    cfg = _cfg(tx=link, rx=link, jesd_mode="8B10B")
    builds = wizard_builds(cfg, "/opt/hdl")
    assert len(builds) == 1
    assert builds[0].argv[3:] == [
        "LANE_RATE=10",
        "REF_CLK=250",
        "PLL_TYPE=QPLL0",
    ]


def test_single_direction_config_yields_one_build():
    cfg = _cfg(rx=_link(9.8304, 245.76, "CPLL"), jesd_mode="8B10B")
    builds = wizard_builds(cfg, "/opt/hdl")
    assert len(builds) == 1
    assert builds[0].argv[3:] == [
        "LANE_RATE=9.8304",
        "REF_CLK=245.76",
        "PLL_TYPE=CPLL",
    ]
