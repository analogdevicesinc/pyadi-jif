"""Helpers to drive the HDL repo xcvr_wizard sub-build from a jif export.

The ADI HDL repo's ``projects/xcvr_wizard/<carrier>`` sub-project runs the
Xilinx GT wizard generation (``get_diff_params``) for one
``LANE_RATE``/``REF_CLK``/``PLL_TYPE`` triple and writes the parsed
configuration to
``xcvr_wizard_<carrier>.gen/sources_1/ip/<GT_TYPE>_cfng.txt``. These
helpers turn an :class:`XgtWizardConfig` into the make invocations (one
per distinct direction) and the expected artifact paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from adijif.fpgas.xilinx.xgt_wizard import XgtWizardConfig, _fmt


@dataclass(frozen=True)
class WizardBuild:
    """One xcvr_wizard sub-build invocation and its expected artifact."""

    argv: List[str]
    cfng_path: Path


def _params(link) -> tuple:
    return (_fmt(link.lane_rate_gbps), _fmt(link.ref_clk_mhz), link.pll_type)


def wizard_builds(
    cfg: XgtWizardConfig,
    hdl_dir: str,
    carrier: str = "zcu102",
    gt_type: Optional[str] = None,
) -> List[WizardBuild]:
    """Build the make invocations for each distinct link direction.

    Args:
        cfg: Exported xgt_wizard configuration.
        hdl_dir: Root of an ADI HDL repo checkout.
        carrier: Carrier folder under ``projects/xcvr_wizard``.
        gt_type: GT type for the artifact name; defaults to
            ``cfg.transceiver_type``.

    Returns:
        One :class:`WizardBuild` per distinct (lane rate, ref clk, PLL)
        triple, primary (TX) direction first.
    """
    gt = gt_type or cfg.transceiver_type or "GTHE4"
    project_dir = Path(hdl_dir) / "projects" / "xcvr_wizard" / carrier
    cfng = (
        project_dir
        / f"xcvr_wizard_{carrier}.gen"
        / "sources_1"
        / "ip"
        / f"{gt}_cfng.txt"
    )

    builds: List[WizardBuild] = []
    seen = set()
    for link in (cfg.tx, cfg.rx):
        if link is None:
            continue
        params = _params(link)
        if params in seen:
            continue
        seen.add(params)
        lane_rate, ref_clk, pll = params
        builds.append(
            WizardBuild(
                argv=[
                    "make",
                    "-C",
                    str(project_dir),
                    f"LANE_RATE={lane_rate}",
                    f"REF_CLK={ref_clk}",
                    f"PLL_TYPE={pll}",
                ],
                cfng_path=cfng,
            )
        )
    return builds
