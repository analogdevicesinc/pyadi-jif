"""Vivado build validation for the jif adi.xgt-wizard export (AD9081+ZCU102).

Solves the AD9081 + ZCU102 system that mirrors the ``mini2`` lab rig
(m8_l4, HMC7044 vcxo 122.88 MHz), exports the ``adi.xgt-wizard``
parameters, and runs the HDL repo's ``projects/xcvr_wizard/zcu102``
sub-build with them. This proves the jif-emitted ``LANE_RATE`` /
``REF_CLK`` / ``PLL_TYPE`` triples are accepted by the real Xilinx GT
wizard generation and produce the parsed ``GTHE4_cfng.txt`` artifact.

Requirements (skipped otherwise): ``--run-hdl-build``, an ADI HDL repo
checkout at ``$HDL_DIR``, and ``vivado`` on ``PATH``.

Run: HDL_DIR=~/dev/hdl pytest --run-hdl-build \
    tests/hardware/test_hdl_xcvr_wizard_build.py -v
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

import adijif

from .hdl_build import wizard_builds

pytestmark = pytest.mark.hdl_build

CARRIER = "zcu102"
BUILD_TIMEOUT_S = 40 * 60


@pytest.fixture(scope="module")
def hdl_dir() -> Path:
    """The ADI HDL repo checkout, from $HDL_DIR; skip when unusable."""
    raw = os.environ.get("HDL_DIR")
    if not raw:
        pytest.skip("HDL_DIR not set; point it at an ADI hdl repo checkout")
    path = Path(raw).expanduser()
    if not (path / "projects" / "xcvr_wizard" / CARRIER).is_dir():
        pytest.skip(f"{path} has no projects/xcvr_wizard/{CARRIER}")
    if shutil.which("vivado") is None:
        pytest.skip("vivado not on PATH; source settings64.sh first")
    return path


@pytest.fixture(scope="module")
def wizard_config() -> "adijif.fpgas.xilinx.xgt_wizard.XgtWizardConfig":
    """Solve the mini2-rig-like AD9081+ZCU102 system and export it."""
    cddc, fddc = 6, 4
    sys = adijif.system(
        "ad9081", "hmc7044", "xilinx", 122.88e6, solver="CPLEX"
    )
    sys.fpga.setup_by_dev_kit_name(CARRIER)
    sys.fpga.ref_clock_constraint = "Unconstrained"
    sys.fpga.sys_clk_select = "XCVR_QPLL0"
    sys.fpga.out_clk_select = "XCVR_PROGDIV_CLK"
    sys.converter.clocking_option = "integrated_pll"
    sys.converter.adc.sample_clock = 2900000000 / (cddc * fddc)
    sys.converter.dac.sample_clock = 5800000000 / (cddc * fddc)
    sys.converter.adc.datapath.cddc_decimations = [cddc] * 4
    sys.converter.adc.datapath.fddc_decimations = [fddc] * 8
    sys.converter.adc.datapath.fddc_enabled = [True] * 8
    sys.converter.dac.datapath.cduc_interpolation = cddc
    sys.converter.dac.datapath.fduc_interpolation = fddc
    sys.converter.dac.datapath.fduc_enabled = [True] * 8
    sys.converter.dac.set_quick_configuration_mode("0", "jesd204c")
    sys.converter.adc.set_quick_configuration_mode("1.0", "jesd204c")
    return sys.export_config(format="adi.xgt-wizard")


def test_xcvr_wizard_subbuild_accepts_jif_parameters(hdl_dir, wizard_config):
    """Every jif-emitted parameter triple survives the GT wizard build."""
    builds = wizard_builds(wizard_config, str(hdl_dir), carrier=CARRIER)
    assert builds, "exporter produced no build directions"

    for index, build in enumerate(builds):
        if build.cfng_path.exists():
            build.cfng_path.unlink()
        log_path = Path.cwd() / f"hdl_xcvr_wizard_build_{index}.log"
        with open(log_path, "w") as log:
            # argv is a fixed make invocation built from validated
            # XgtWizardConfig fields; no shell, no untrusted input.
            result = subprocess.run(  # noqa: S603
                build.argv,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=BUILD_TIMEOUT_S,
            )
        assert result.returncode == 0, (
            f"{' '.join(build.argv)} failed; see {log_path}"
        )
        assert build.cfng_path.is_file(), (
            f"wizard build produced no {build.cfng_path}"
        )
        assert build.cfng_path.stat().st_size > 0, (
            f"{build.cfng_path} is empty"
        )
