"""AD9371 transceiver clocking and profile model."""

from __future__ import annotations

from typing import Dict, List, Union

from ..solvers import GEKKO, CpoModel, CpoSolveResult
from .ad9371_util import parse_ad9371_profile
from .adrv9009 import adrv9009, adrv9009_rx, adrv9009_tx


class _ad9371_profile_mixin:
    """Common profile-driven clock behavior for AD9371 datapaths."""

    profile_device_clock = 122_880_000

    def _apply_ad9371_profile(self, profile_path: str, *, direction: str) -> None:
        self._last_config = None
        data = parse_ad9371_profile(profile_path)
        section = data[direction]
        clocks = data["clocks"]
        self.profile_device_clock = int(clocks["deviceClock_kHz"] * 1000)
        self.sample_clock = int(section["iqRate_kHz"] * 1000)

    def _profile_required_clocks(self) -> List[Dict]:
        self.config = {}
        self.config["lmfc_divisor_sysref"] = self._convert_input(
            self._lmfc_divisor_sysref_available, name="lmfc_divisor_sysref"
        )
        self.config["ref_clk"] = self._add_intermediate(self.profile_device_clock)
        self.config["sysref"] = self._add_intermediate(
            self.multiframe_clock / self.config["lmfc_divisor_sysref"]
        )
        return [self.config["ref_clk"], self.config["sysref"]]


class ad9371_rx(_ad9371_profile_mixin, adrv9009_rx):
    """AD9371 receive datapath and JESD204B model."""

    name = "AD9371_RX"
    sample_clock_min = 30_720_000
    sample_clock_max = 122_880_000
    bit_clock_min_available = {"jesd204b": 614_400_000}
    bit_clock_max_available = {"jesd204b": 6_144_000_000}
    decimation_available = [10, 20, 40]

    def get_required_clock_names(self) -> List[str]:
        """Return AD9371 RX device-clock and SYSREF names."""
        return ["ad9371_rx_ref_clk", "ad9371_rx_sysref"]

    def get_required_clocks(self) -> List[Dict]:
        """Return profile device clock and a valid RX SYSREF."""
        return self._profile_required_clocks()

    def apply_profile_settings(self, profile_path: str, jesd: dict = None) -> None:
        """Apply RX sample rate, decimation, device clock, and optional JESD mode."""
        self._apply_ad9371_profile(profile_path, direction="rx")
        data = parse_ad9371_profile(profile_path)["rx"]
        self.decimation = int(
            data.get("rxFirDecimation", 1)
            * data.get("rxDec5Decimation", 1)
            * data.get("rhb1Decimation", 1)
        )
        if jesd is not None:
            from adijif.utils import get_jesd_mode_from_params

            modes = get_jesd_mode_from_params(self, **jesd)
            if not modes:
                raise ValueError(f"No matching JESD mode found for {jesd}")
            self.set_quick_configuration_mode(modes[0]["mode"], modes[0]["jesd_class"])


class ad9371_tx(_ad9371_profile_mixin, adrv9009_tx):
    """AD9371 transmit datapath and JESD204B model."""

    name = "AD9371_TX"
    sample_clock_min = 61_440_000
    sample_clock_max = 245_760_000
    bit_clock_min_available = {"jesd204b": 614_400_000}
    bit_clock_max_available = {"jesd204b": 6_144_000_000}
    interpolation_available = [2, 4, 8]

    def get_required_clock_names(self) -> List[str]:
        """Return AD9371 TX device-clock and SYSREF names."""
        return ["ad9371_tx_ref_clk", "ad9371_tx_sysref"]

    def get_required_clocks(self) -> List[Dict]:
        """Return profile device clock and a valid TX SYSREF."""
        return self._profile_required_clocks()

    def apply_profile_settings(self, profile_path: str, jesd: dict = None) -> None:
        """Apply TX sample rate, interpolation, device clock, and optional JESD mode."""
        self._apply_ad9371_profile(profile_path, direction="tx")
        data = parse_ad9371_profile(profile_path)["tx"]
        self.interpolation = int(
            data.get("txFirInterpolation", 1)
            * data.get("thb1Interpolation", 1)
            * data.get("thb2Interpolation", 1)
            * data.get("txInputHbInterpolation", 1)
        )
        if jesd is not None:
            from adijif.utils import get_jesd_mode_from_params

            modes = get_jesd_mode_from_params(self, **jesd)
            if not modes:
                raise ValueError(f"No matching JESD mode found for {jesd}")
            self.set_quick_configuration_mode(modes[0]["mode"], modes[0]["jesd_class"])


class ad9371_obs(ad9371_rx):
    """AD9371 observation-receiver datapath and JESD204B model."""

    name = "AD9371_OBS"
    sample_clock_max = 245_760_000
    decimation_available = [5, 10, 20]

    def get_required_clock_names(self) -> List[str]:
        """Return AD9371 observation device-clock and SYSREF names."""
        return ["ad9371_obs_ref_clk", "ad9371_obs_sysref"]

    def apply_profile_settings(self, profile_path: str, jesd: dict = None) -> None:
        """Apply observation sample rate, decimation, clock, and optional JESD."""
        self._apply_ad9371_profile(profile_path, direction="obs")
        data = parse_ad9371_profile(profile_path)["obs"]
        self.decimation = int(
            data.get("rxFirDecimation", 1)
            * data.get("rxDec5Decimation", 1)
            * data.get("rhb1Decimation", 1)
        )
        if jesd is not None:
            from adijif.utils import get_jesd_mode_from_params

            modes = get_jesd_mode_from_params(self, **jesd)
            if not modes:
                raise ValueError(f"No matching JESD mode found for {jesd}")
            self.set_quick_configuration_mode(modes[0]["mode"], modes[0]["jesd_class"])


class ad9371(adrv9009):
    """Combined AD9371 RX and TX profile-driven model."""

    name = "AD9371"

    def __init__(
        self, model: Union[GEKKO, CpoModel] = None, solver: str = None
    ) -> None:
        """Initialize the AD9371 RX and TX datapaths."""
        if solver:
            self.solver = solver
        self.adc = ad9371_rx(model, solver=self.solver)
        self.obs = ad9371_obs(model, solver=self.solver)
        self.dac = ad9371_tx(model, solver=self.solver)
        self.model = model
        self.profile_device_clock = 122_880_000

    def get_required_clock_names(self) -> List[str]:
        """Return shared device clock plus RX and TX SYSREF names."""
        return ["ad9371_ref_clk", "ad9371_rx_sysref", "ad9371_tx_sysref"]

    def get_required_clocks(self) -> List[Dict]:
        """Generate shared profile device clock and RX/TX SYSREF requirements."""
        ratio = self.dac.sample_clock / self.adc.sample_clock
        if ratio not in (0.25, 0.5, 1, 2, 4):
            raise ValueError(
                "AD9371 RX and TX sample rates must be related by a power of 2"
            )
        if self.solver == "gekko":
            raise AssertionError("AD9371 combined model requires CPLEX")

        self.config = {}
        self.config["adc_lmfc_divisor_sysref"] = self._convert_input(
            self._lmfc_divisor_sysref_available, name="adc_lmfc_divisor_sysref"
        )
        self.config["dac_lmfc_divisor_sysref"] = self._convert_input(
            self._lmfc_divisor_sysref_available, name="dac_lmfc_divisor_sysref"
        )
        self.config["ref_clk"] = self._add_intermediate(self.profile_device_clock)
        self.config["sysref_adc"] = self._add_intermediate(
            self.adc.multiframe_clock / self.config["adc_lmfc_divisor_sysref"]
        )
        self.config["sysref_dac"] = self._add_intermediate(
            self.dac.multiframe_clock / self.config["dac_lmfc_divisor_sysref"]
        )
        return [self.config["ref_clk"], self.config["sysref_adc"], self.config["sysref_dac"]]

    def get_config(self, solution: CpoSolveResult = None) -> Dict:
        """Return profile-derived shared device-clock metadata."""
        if solution:
            self._solution = solution
        return {"device_clock": self.profile_device_clock}

    def apply_profile_settings(
        self,
        profile_path: str,
        rx_jesd: dict = None,
        tx_jesd: dict = None,
        obs_jesd: dict = None,
    ) -> None:
        """Apply one AD9371 profile to RX, observation RX, and TX datapaths."""
        self.adc.apply_profile_settings(profile_path, rx_jesd)
        self.obs.apply_profile_settings(profile_path, obs_jesd)
        self.dac.apply_profile_settings(profile_path, tx_jesd)
        if self.adc.profile_device_clock != self.dac.profile_device_clock:
            raise ValueError("AD9371 RX and TX profile device clocks differ")
        self.profile_device_clock = self.adc.profile_device_clock
