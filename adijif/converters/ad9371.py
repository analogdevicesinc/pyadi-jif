"""AD9371 Mykonos transceiver clocking and profile model."""

from __future__ import annotations

from typing import Any, Dict, List, Union

from adijif.utils import get_jesd_mode_from_params

from ..solvers import GEKKO, CpoModel, CpoSolveResult
from .ad9371_util import (
    AD9371_OBS_MODES,
    AD9371_RX_MODES,
    AD9371_TX_MODES,
    parse_ad9371_profile,
)
from .adrv9009 import adrv9009, adrv9009_rx, adrv9009_tx
from .converter import converter

_RX_FACTORS = {30_720_000: 40, 61_440_000: 20, 122_880_000: 10}
_OBS_FACTORS = {61_440_000: 20, 122_880_000: 10, 245_760_000: 5}
_TX_FACTORS = {61_440_000: 8, 122_880_000: 4, 245_760_000: 2}


class _ad9371_profile_mixin:
    """Common profile-driven behavior for AD9371 datapaths."""

    profile_device_clock = 122_880_000
    _lmfc_divisor_sysref_available = [*range(1, 65)]

    def _prepare_profile(
        self, data: dict[str, Any], *, direction: str, jesd: dict | None
    ) -> tuple[int, int, tuple[str, str] | None]:
        section = data[direction]
        device_clock = int(data["clocks"]["deviceClock_kHz"] * 1000)
        if device_clock != 122_880_000:
            raise ValueError(
                "AD9371 profile device clock must be 122.88 MHz, "
                f"got {device_clock} Hz"
            )
        sample_clock = int(section["iqRate_kHz"] * 1000)
        if direction == "tx":
            factor = int(
                section["txFirInterpolation"]
                * section["thb1Interpolation"]
                * section["thb2Interpolation"]
                * section["txInputHbInterpolation"]
            )
            expected = _TX_FACTORS
        else:
            factor = int(
                section["rxFirDecimation"]
                * section["rxDec5Decimation"]
                * section["rhb1Decimation"]
            )
            expected = _OBS_FACTORS if direction == "obs" else _RX_FACTORS
        if expected.get(sample_clock) != factor:
            raise ValueError(
                f"Unsupported AD9371 {direction} rate/factor pair: "
                f"{sample_clock} Hz, {factor}"
            )

        mode = None
        if jesd is not None:
            modes = get_jesd_mode_from_params(self, **jesd)
            if not modes:
                raise ValueError(f"No matching AD9371 JESD mode found for {jesd}")
            mode = (modes[0]["mode"], modes[0]["jesd_class"])
        return sample_clock, factor, mode

    def _commit_profile(
        self,
        prepared: tuple[int, int, tuple[str, str] | None],
        *,
        direction: str,
    ) -> None:
        sample_clock, factor, mode = prepared
        if mode is not None:
            self.set_quick_configuration_mode(mode[0], mode[1])
        if direction == "tx":
            self.interpolation = factor
        else:
            self.decimation = factor
        self.sample_clock = sample_clock
        self.profile_device_clock = 122_880_000
        self._last_config = None

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
    """AD9371 primary receive datapath and JESD204B model."""

    name = "AD9371_RX"
    quick_configuration_modes = {"jesd204b": AD9371_RX_MODES}
    M_available = [2, 4]
    L_available = [1, 2, 4]
    N_available = [14]
    Np_available = [16]
    F_available = [1, 2, 4, 8]
    S_available = [1]
    K_available = [*range(1, 33)]
    CS_available = [2]
    CF_available = [0]
    sample_clock_min = 30_720_000
    sample_clock_max = 122_880_000
    bit_clock_min_available = {"jesd204b": 614_400_000}
    bit_clock_max_available = {"jesd204b": 6_144_000_000}
    _decimation = 10
    decimation_available = [10, 20, 40]

    def get_required_clock_names(self) -> List[str]:
        return ["ad9371_rx_ref_clk", "ad9371_rx_sysref"]

    def get_required_clocks(self) -> List[Dict]:
        return self._profile_required_clocks()

    def apply_profile_settings(self, profile_path: str, jesd: dict = None) -> None:
        data = parse_ad9371_profile(profile_path)
        prepared = self._prepare_profile(data, direction="rx", jesd=jesd)
        self._commit_profile(prepared, direction="rx")


class ad9371_tx(_ad9371_profile_mixin, adrv9009_tx):
    """AD9371 transmit datapath and JESD204B model."""

    name = "AD9371_TX"
    quick_configuration_modes = {"jesd204b": AD9371_TX_MODES}
    M_available = [2, 4]
    L_available = [1, 2, 4]
    N_available = [14]
    Np_available = [16]
    F_available = [1, 2, 4, 8]
    S_available = [1]
    K_available = [*range(1, 33)]
    CS_available = [2]
    CF_available = [0]
    sample_clock_min = 61_440_000
    sample_clock_max = 245_760_000
    bit_clock_min_available = {"jesd204b": 614_400_000}
    bit_clock_max_available = {"jesd204b": 6_144_000_000}
    _interpolation = 4
    interpolation_available = [2, 4, 8]

    def get_required_clock_names(self) -> List[str]:
        return ["ad9371_tx_ref_clk", "ad9371_tx_sysref"]

    def get_required_clocks(self) -> List[Dict]:
        return self._profile_required_clocks()

    def apply_profile_settings(self, profile_path: str, jesd: dict = None) -> None:
        data = parse_ad9371_profile(profile_path)
        prepared = self._prepare_profile(data, direction="tx", jesd=jesd)
        self._commit_profile(prepared, direction="tx")


class ad9371_obs(ad9371_rx):
    """AD9371 observation-receiver datapath and JESD204B model."""

    name = "AD9371_OBS"
    quick_configuration_modes = {"jesd204b": AD9371_OBS_MODES}
    sample_clock_min = 61_440_000
    sample_clock_max = 245_760_000
    _decimation = 10
    decimation_available = [5, 10, 20]

    def get_required_clock_names(self) -> List[str]:
        return ["ad9371_obs_ref_clk", "ad9371_obs_sysref"]

    def apply_profile_settings(self, profile_path: str, jesd: dict = None) -> None:
        data = parse_ad9371_profile(profile_path)
        prepared = self._prepare_profile(data, direction="obs", jesd=jesd)
        self._commit_profile(prepared, direction="obs")


class ad9371(adrv9009):
    """Combined AD9371 primary RX, observation RX, and TX model."""

    name = "AD9371"
    _nested = ["adc", "obs", "dac"]
    _lmfc_divisor_sysref_available = [*range(1, 65)]

    def __init__(
        self, model: Union[GEKKO, CpoModel] = None, solver: str = None
    ) -> None:
        if solver:
            self.solver = solver
        self.adc = ad9371_rx(model, solver=self.solver)
        self.obs = ad9371_obs(model, solver=self.solver)
        self.dac = ad9371_tx(model, solver=self.solver)
        self.model = model
        self.profile_device_clock = 122_880_000

    def validate_config(self) -> None:
        self.adc.validate_config()
        self.obs.validate_config()
        self.dac.validate_config()

    def _get_converters(self) -> List[converter]:
        return [self.adc, self.obs, self.dac]

    def get_required_clock_names(self) -> List[str]:
        return [
            "ad9371_ref_clk",
            "ad9371_rx_sysref",
            "ad9371_obs_sysref",
            "ad9371_tx_sysref",
        ]

    def get_required_clocks(self) -> List[Dict]:
        rates = [self.adc.sample_clock, self.obs.sample_clock, self.dac.sample_clock]
        for left in rates:
            for right in rates:
                if left / right not in (0.25, 0.5, 1, 2, 4):
                    raise ValueError(
                        "AD9371 RX, observation RX, and TX rates must be related "
                        "by powers of 2"
                    )
        if self.solver == "gekko":
            raise AssertionError("AD9371 combined model requires CPLEX")

        self.config = {}
        lmfcs = [
            self.adc.multiframe_clock,
            self.obs.multiframe_clock,
            self.dac.multiframe_clock,
        ]
        minimum_lmfc = min(lmfcs)
        possible_sysrefs = []
        for divisor in range(1, 65):
            candidate = minimum_lmfc / divisor
            if candidate != int(candidate):
                continue
            candidate = int(candidate)
            if all(lmfc % candidate == 0 for lmfc in lmfcs):
                possible_sysrefs.append(candidate)
        if not possible_sysrefs:
            raise ValueError("No common AD9371 SYSREF satisfies all active LMFCs")
        shared_sysref = self._convert_input(possible_sysrefs, name="shared_sysref")
        sysrefs = [shared_sysref, shared_sysref, shared_sysref]
        self.config["sysref_adc"] = shared_sysref
        self.config["sysref_obs"] = shared_sysref
        self.config["sysref_dac"] = shared_sysref
        self.config["ref_clk"] = self._add_intermediate(self.profile_device_clock)
        return [self.config["ref_clk"], *sysrefs]

    def get_config(self, solution: CpoSolveResult = None) -> Dict:
        if solution:
            self._solution = solution
        return {
            "device_clock": self.profile_device_clock,
            # Linux's AD9371 JESD-FSM flow programs the pulsed AD9528 SYSREF
            # provider separately from ordinary clock-output dividers.
            "jesd204_max_sysref_hz": 78_125,
        }

    def apply_profile_settings(
        self,
        profile_path: str,
        rx_jesd: dict = None,
        tx_jesd: dict = None,
        obs_jesd: dict = None,
    ) -> None:
        """Validate once, then atomically apply one profile to all three paths."""
        data = parse_ad9371_profile(profile_path)
        prepared = [
            self.adc._prepare_profile(data, direction="rx", jesd=rx_jesd),
            self.obs._prepare_profile(data, direction="obs", jesd=obs_jesd),
            self.dac._prepare_profile(data, direction="tx", jesd=tx_jesd),
        ]
        self.adc._commit_profile(prepared[0], direction="rx")
        self.obs._commit_profile(prepared[1], direction="obs")
        self.dac._commit_profile(prepared[2], direction="tx")
        self.profile_device_clock = 122_880_000
