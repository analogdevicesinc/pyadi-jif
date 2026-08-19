"""Helpers to drive the HDL repo xcvr_wizard sub-build from a jif export.

The ADI HDL repo's ``projects/xcvr_wizard/<carrier>`` sub-project runs the
Xilinx GT wizard generation (``get_diff_params``) for the full parameter
set — ``LANE_RATE``/``REF_CLK``/``PLL_TYPE``/``JESD_MODE`` plus
``XCVR_RX_*`` overrides — and writes the parsed configuration to a
``<GT_TYPE>_cfng.txt`` inside a parameter-token build subdirectory (e.g.
``RATE11_9625_REFCLK362_5_PLLTYPEQPLL1/``). These helpers turn an
:class:`XgtWizardConfig` into that make invocation and locate the
artifact by glob.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from adijif.fpgas.xilinx.xgt_wizard import XgtWizardConfig


@dataclass(frozen=True)
class WizardBuild:
    """One xcvr_wizard sub-build invocation and its expected artifact.

    The HDL make wrapper builds into a parameter-token subdirectory of
    ``project_dir``, so the artifact is found by globbing for
    ``cfng_name`` under ``project_dir`` rather than at a fixed path.
    """

    argv: List[str]
    project_dir: Path
    cfng_name: str

    def find_cfng(self) -> List[Path]:
        """Locate generated cfng artifacts under the project directory.

        Returns:
            All ``cfng_name`` files below ``project_dir``.
        """
        return sorted(self.project_dir.rglob(self.cfng_name))


def wizard_builds(
    cfg: XgtWizardConfig,
    hdl_dir: str,
    carrier: str = "zcu102",
    gt_type: Optional[str] = None,
) -> List[WizardBuild]:
    """Build the make invocation for an exported wizard configuration.

    Args:
        cfg: Exported xgt_wizard configuration.
        hdl_dir: Root of an ADI HDL repo checkout.
        carrier: Carrier folder under ``projects/xcvr_wizard``.
        gt_type: GT type for the artifact name; defaults to
            ``cfg.transceiver_type``.

    Returns:
        A single-element list (kept as a list for call-site symmetry)
        with the full-parameter make invocation, TX primary and
        ``XCVR_RX_*`` overrides only where RX differs.
    """
    gt = gt_type or cfg.transceiver_type or "GTHE4"
    project_dir = Path(hdl_dir) / "projects" / "xcvr_wizard" / carrier
    argv = ["make", "-C", str(project_dir)] + [
        f"{key}={value}" for key, value in cfg._project_params()
    ]
    return [
        WizardBuild(
            argv=argv,
            project_dir=project_dir,
            cfng_name=f"{gt}_cfng.txt",
        )
    ]
