"""ADRV9042 JESD and external clock models, based on UG-2358 Rev. 0.

DEVCLK and interface rates must come from an ACE-approved configuration.
Internal PLLs, filter profiles, RF LOs, and TDD link sharing are not synthesized.
"""

from copy import deepcopy
from fractions import Fraction
from itertools import combinations
from math import gcd, isfinite, lcm

from .adrv9042_util import transport_modes
from .converter import converter


def _positive_rate(value: float, name: str) -> Fraction:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float, Fraction))
        or not isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be a positive finite rate in Hz")
    return Fraction(str(value))


def _common_rate(rates: list[Fraction]) -> Fraction:
    denominator = lcm(*(rate.denominator for rate in rates))
    return Fraction(
        gcd(
            *(
                rate.numerator * (denominator // rate.denominator)
                for rate in rates
            )
        ),
        denominator,
    )


def _power_of_two_ratio(left: float, right: float) -> bool:
    ratio = Fraction(str(left)) / Fraction(str(right))
    return all(v & (v - 1) == 0 for v in (ratio.numerator, ratio.denominator))


class _adrv9042_clock:
    """Shared external-reference and SYSREF behavior."""

    reference_clock = None

    def _clock_rates(self) -> list[Fraction]:
        reference = _positive_rate(self.reference_clock, "reference_clock")
        if not 61_440_000 <= reference <= 491_520_000:
            raise ValueError("reference_clock must be 61.44 to 491.52 MHz")
        return [
            reference,
            *[
                Fraction(str(link.sample_clock)) / (link.S * link.K)
                for link in self._get_converters()
            ],
        ]

    def sysref_candidates(self) -> list[Fraction]:
        """Return exact common submultiples of DEVCLK and active LMFC/LEMCs."""
        self.validate_config()
        base = _common_rate(self._clock_rates())
        if not self.sysref_dividers or any(
            type(d) is not int or d < 1 for d in self.sysref_dividers
        ):
            raise ValueError("sysref_dividers must contain positive integers")
        return [base / d for d in sorted(set(self.sysref_dividers))]

    def get_required_clocks(self) -> list:
        """Request one DEVCLK and a common SYSREF for each enabled link."""
        candidates = self.sysref_candidates()
        base = max(candidates) * min(self.sysref_dividers)
        divider = self._convert_input(
            sorted(set(self.sysref_dividers)),
            name=f"{self.name}_sysref_divider",
        )
        self.config = {
            "sysref_divider": divider,
            "sysref_base": float(base),
            "ref_clk": self._add_intermediate(self.reference_clock),
            "sysref": self._add_intermediate(float(base) / divider),
        }
        return [
            self.config["ref_clk"],
            *[self.config["sysref"] for _ in self._get_converters()],
        ]

    def device_clock_available(self) -> list:
        """Return the explicitly configured DEVCLK, when present."""
        return [] if self.reference_clock is None else [self.reference_clock]

    def device_clock_ranges(self) -> tuple:
        """Return the configured reference range for brute-force callers."""
        clocks = self.device_clock_available()
        if not clocks:
            raise ValueError("Set reference_clock from the ACE configuration")
        return clocks[0], clocks[0]


class _adrv9042_link(_adrv9042_clock, converter):
    """One hardware framer or deframer and its transport constraints."""

    available_jesd_modes = ["jesd204b", "jesd204c"]
    L_available = []
    M_available = []
    quick_configuration_modes = {}
    N_available = list(range(1, 25))
    Np_available = [12, 16, 24]
    F_available = list(range(2, 33))
    K_available = list(range(1, 257))
    CS_available = [0, 1, 2, 3]
    CF_available = [0]
    clocking_option_available = ["integrated_pll"]
    _clocking_option = "integrated_pll"
    converter_clock_min = 1
    converter_clock_max = 491_520_000
    sample_clock_min = 1
    sample_clock_max = 491_520_000
    bit_clock_min_available = {"jesd204b": 312_500_000, "jesd204c": 312_500_000}
    bit_clock_max_available = {
        "jesd204b": 12_500_000_000,
        "jesd204c": 32_440_320_000,
    }
    _jesd_params_to_skip = []
    _jesd_params_to_skip_check = []
    _parameters_to_return = [*converter._parameters_to_return, "N", "E"]

    def __init__(self, model=None, solver=None, *, link_index=0) -> None:
        if solver not in (None, "CPLEX"):
            raise ValueError("ADRV9042 requires CPLEX")
        receive = self.converter_type == "adc"
        if type(link_index) is not int or link_index not in range(
            3 if receive else 2
        ):
            raise ValueError("Invalid ADRV9042 link_index")
        super().__init__(model, solver="CPLEX")
        self.link_index = link_index
        self.S_available = [1, 2, 4] if receive else [1, 2]
        self.E_available = [1, 3, 5] if receive else list(range(1, 33))
        self.enabled = True
        self.reference_clock = None
        self.sysref_dividers = list(range(1, 65))
        self.lane_mapping = None
        self.cddc_cduc_bypassed = False
        self.sample_clock = 122_880_000
        self.set_quick_configuration_mode("M4L2Np16S1", "jesd204c")

    def __setattr__(self, key, value) -> None:
        if not key.startswith("_") and key not in (
            "model",
            "config",
            "configs",
        ):
            self.__dict__["_last_config"] = None
        super().__setattr__(key, value)

    @property
    def link_index(self) -> int:
        """Hardware framer or deframer index, including its resource limits."""
        return self._link_index

    @link_index.setter
    def link_index(self, value: int) -> None:
        receive = self.converter_type == "adc"
        if type(value) is not int or value not in range(3 if receive else 2):
            raise ValueError("Invalid ADRV9042 link_index")
        self._link_index = value
        self.L_available = (
            ([1, 2, 4, 8], [1, 2, 4], [1, 2])[value]
            if receive
            else ([1, 2, 4, 8], [1, 2, 4])[value]
        )
        self.M_available = list(
            range(2 if receive else 1, (192, 96, 32)[value] + 1)
        )
        self.quick_configuration_modes = deepcopy(
            transport_modes("rx" if receive else "tx", value)
        )

    @property
    def E(self) -> int:
        """Number of JESD204C multiblocks per extended multiblock."""
        return self._E

    @E.setter
    def E(self, value: int) -> None:
        if type(value) is not int or value not in self.E_available:
            raise ValueError(f"E must be one of {self.E_available}")
        self._last_config = None
        self._E = value

    @property
    def converter_clock(self) -> float:
        """Return the interface sample rate; analog converter rates are external."""
        return self.sample_clock

    def _get_converters(self) -> list:
        return [self]

    def physical_lanes(self) -> list[int]:
        """Return logical-to-physical lane assignment (identity by default)."""
        return (
            list(range(self.L))
            if self.lane_mapping is None
            else list(self.lane_mapping)
        )

    def _configuration_signature(self) -> tuple:
        return (
            self.link_index,
            self.enabled,
            self.reference_clock,
            tuple(self.sysref_dividers),
            self.cddc_cduc_bypassed,
            tuple(self.physical_lanes()),
            self.sample_clock,
            self.jesd_class,
            self.encoding,
            tuple(self.get_current_jesd_mode_settings().items()),
        )

    def _check_jesd_config(self) -> None:
        _positive_rate(self.sample_clock, "sample_clock")
        if not self.bit_clock_min <= self.bit_clock <= self.bit_clock_max:
            raise ValueError(
                f"ADRV9042 {self.jesd_class} lane rate outside {self.bit_clock_min}..{self.bit_clock_max} Hz"
            )

    def _check_valid_jesd_mode(self) -> str:
        self._check_jesd_config()
        if self.M * self.Np * self.S != 8 * self.L * self.F:
            raise ValueError(
                "Invalid transport packing: M*Np*S must equal 8*L*F"
            )
        modes = self.quick_configuration_modes[self.jesd_class]
        mode = f"M{int(self.M)}L{int(self.L)}Np{int(self.Np)}S{int(self.S)}"
        if mode not in modes:
            raise ValueError("Unsupported ADRV9042 transport tuple")
        if self.cddc_cduc_bypassed and self.M > 32:
            raise ValueError("M must be <= 32 with CDDC/CDUC bypassed")
        if self.N + self.CS > self.Np:
            raise ValueError("Sample resolution plus control bits exceeds Np")
        if self.encoding != (
            "8b10b" if self.jesd_class == "jesd204b" else "64b66b"
        ):
            raise ValueError("Encoding must match the selected JESD standard")
        fk = self.F * self.K
        if self.jesd_class == "jesd204b":
            if not (self.K <= 32 and 20 <= fk <= 256 and fk % 4 == 0):
                raise ValueError(
                    "Invalid JESD204B multiframe: 20 <= F*K <= 256, multiple of four, K <= 32"
                )
        elif fk != 256 * self.E:
            raise ValueError("JESD204C requires F*K = 256*E")
        if self.HD == 0 and (8 * self.F) % self.Np:
            raise ValueError(
                "HD=1 required when a converter's frame spans lanes"
            )
        return mode

    def _check_valid_internal_configuration(self) -> None:
        lanes = self.physical_lanes()
        if (
            len(lanes) != self.L
            or len(set(lanes)) != len(lanes)
            or any(
                type(lane) is not int or lane not in range(8) for lane in lanes
            )
        ):
            raise ValueError(
                "lane_mapping must contain L unique physical lanes in 0..7"
            )

    def validate_config(self) -> None:
        """Validate transport and physical lanes without requiring DEVCLK."""
        self._check_valid_jesd_mode()
        self._check_valid_internal_configuration()
        if not 0 < self.sample_clock <= self.sample_clock_max:
            raise ValueError(
                "sample_clock exceeds the 491.52 MSPS interface limit"
            )

    def get_required_clock_names(self) -> list[str]:
        """Return standalone DEVCLK and SYSREF output names."""
        return [f"{self.name.lower()}_ref_clk", f"{self.name.lower()}_sysref"]

    def get_config(self, solution=None) -> dict:
        """Report the supplied reference and link settings."""
        if solution is not None:
            self._solution = solution
        cfg = {
            "reference_clock": self.reference_clock,
            "clocking_option": self.clocking_option,
            "link_index": self.link_index,
            "lane_mapping": self.physical_lanes(),
            "cddc_cduc_bypassed": self.cddc_cduc_bypassed,
        }
        if solution is not None and "sysref" in self.config:
            cfg["sysref"] = self.config["sysref_base"] / self._get_val(
                self.config["sysref_divider"]
            )
        return self._cache_config(cfg)


class adrv9042_rx(_adrv9042_link):
    """ADRV9042 receive framer; link_index selects framer 0, 1, or 2."""

    name = "ADRV9042_RX"
    converter_type = "adc"


class adrv9042_tx(_adrv9042_link):
    """ADRV9042 transmit deframer; link_index selects deframer 0 or 1."""

    name = "ADRV9042_TX"
    converter_type = "dac"


class adrv9042_obs(adrv9042_rx):
    """Observation transport, defaulting to framer 2."""

    name = "ADRV9042_OBS"

    def __init__(self, model=None, solver=None, *, link_index=2) -> None:
        super().__init__(model, solver, link_index=link_index)


class adrv9042(_adrv9042_clock, converter):
    """ADRV9042 with three framers, two deframers, and shared external clocks."""

    name = "ADRV9042"
    converter_type = "adc_dac"
    available_jesd_modes = ["jesd204b", "jesd204c"]
    quick_configuration_modes = {}
    clocking_option_available = ["integrated_pll"]
    _clocking_option = "integrated_pll"
    converter_clock_min = 1
    converter_clock_max = 491_520_000
    K_available = L_available = M_available = N_available = Np_available = (
        F_available
    ) = []
    _link_names = ("framer0", "framer1", "framer2", "deframer0", "deframer1")

    def __init__(self, model=None, solver=None) -> None:
        if solver not in (None, "CPLEX"):
            raise ValueError("ADRV9042 requires CPLEX")
        super().__init__(model, solver="CPLEX")
        for name, cls, index in [
            ("framer0", adrv9042_rx, 0),
            ("framer1", adrv9042_rx, 1),
            ("framer2", adrv9042_obs, 2),
            ("deframer0", adrv9042_tx, 0),
            ("deframer1", adrv9042_tx, 1),
        ]:
            link = cls(self.model, solver="CPLEX", link_index=index)
            link.name = f"ADRV9042_{name.upper()}"
            link.enabled = name in ("framer0", "deframer0")
            setattr(self, name, link)
        self.reference_clock = None
        self.sysref_dividers = list(range(1, 65))

    @property
    def adc(self):
        """Primary RX compatibility alias."""
        return self.framer0

    @property
    def dac(self):
        """Primary TX compatibility alias."""
        return self.deframer0

    @property
    def obs(self):
        """Observation compatibility alias."""
        return self.framer2

    @property
    def _nested(self) -> list[str]:
        return [
            name for name in self._link_names if getattr(self, name).enabled
        ]

    def _get_converters(self) -> list:
        return [getattr(self, name) for name in self._nested]

    def _configuration_signature(self) -> tuple:
        return (
            self.reference_clock,
            tuple(self.sysref_dividers),
            tuple(
                getattr(self, name)._configuration_signature()
                for name in self._link_names
            ),
        )

    def _check_valid_internal_configuration(self) -> None:
        self.validate_config()

    def validate_config(self) -> None:
        """Check active links, lane ownership, and inter-framer rate ratios."""
        if not self._nested:
            raise ValueError("Enable at least one ADRV9042 link")
        for name in self._nested:
            if getattr(self, name).link_index != int(name[-1]):
                raise ValueError(
                    f"{name} must retain hardware index {name[-1]}"
                )
        for direction in ("adc", "dac"):
            links = [
                link
                for link in self._get_converters()
                if link.converter_type == direction
            ]
            used = set()
            for link in links:
                link.validate_config()
                lanes = set(link.physical_lanes())
                if used & lanes:
                    raise ValueError(
                        "Active links cannot share a physical lane; TDD link sharing is not modeled"
                    )
                used.update(lanes)
            if direction == "adc":
                for left, right in combinations(links, 2):
                    if not _power_of_two_ratio(
                        left.sample_clock, right.sample_clock
                    ) or not _power_of_two_ratio(
                        left.bit_clock, right.bit_clock
                    ):
                        raise ValueError(
                            "Active framers require power of two sample-clock and lane-rate ratios"
                        )

    def get_required_clock_names(self) -> list[str]:
        """Return one shared DEVCLK and per-link equal-frequency SYSREFs."""
        return [
            "adrv9042_ref_clk",
            *[f"{name}_sysref" for name in self._nested],
        ]

    def get_config(self, solution=None) -> dict:
        """Report enabled hardware link instances and shared clocks."""
        if solution is not None:
            self._solution = solution
        cfg = {
            "reference_clock": self.reference_clock,
            "links": {
                name: getattr(self, name).get_config() for name in self._nested
            },
        }
        if solution is not None and "sysref" in self.config:
            cfg["sysref"] = self.config["sysref_base"] / self._get_val(
                self.config["sysref_divider"]
            )
        return self._cache_config(cfg)
