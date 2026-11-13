"""ADRV9042 transport and shared-clock regression tests (UG-2358)."""

from fractions import Fraction

import pytest

import adijif
from adijif.registry import get_component_class


@pytest.mark.parametrize(
    "part", ["adrv9042", "adrv9042_rx", "adrv9042_tx", "adrv9042_obs"]
)
def test_public_models(part):
    cls = getattr(adijif, part)
    assert get_component_class("converter", part) is cls
    assert getattr(adijif, part.upper()) is cls
    assert cls().solver == "CPLEX"
    assert cls().clocking_option == "integrated_pll"
    with pytest.raises(ValueError, match="CPLEX"):
        cls(solver="gekko")


@pytest.mark.parametrize("part", ["adrv9042_rx", "adrv9042_tx", "adrv9042_obs"])
@pytest.mark.parametrize("standard", ["jesd204b", "jesd204c"])
@pytest.mark.parametrize("width", [12, 16, 24])
def test_transport_rates(part, standard, width):
    link = getattr(adijif, part)()
    link.set_quick_configuration_mode(f"M4L2Np{width}S1", standard)
    link.sample_clock = 122_880_000
    link.validate_config()
    encoding = Fraction(10, 8) if standard == "jesd204b" else Fraction(66, 64)
    assert link.bit_clock == 122_880_000 * 2 * width * encoding
    assert link.multiframe_clock == link.sample_clock / (link.S * link.K)
    assert link.get_jesd_config()["E"] == link.E


def test_link_instance_limits_and_bypass():
    assert adijif.adrv9042_rx(link_index=0).L_available == [1, 2, 4, 8]
    assert adijif.adrv9042_rx(link_index=1).L_available == [1, 2, 4]
    assert adijif.adrv9042_obs().L_available == [1, 2]
    assert max(adijif.adrv9042_tx(link_index=1).M_available) == 96
    link = adijif.adrv9042_rx()
    link.set_quick_configuration_mode("M64L8Np16S1", "jesd204c")
    link.sample_clock = 30_720_000
    link.validate_config()
    link.cddc_cduc_bypassed = True
    with pytest.raises(ValueError, match="32"):
        link.validate_config()


def test_204c_above_generic_limit_and_extended_multiblock():
    link = adijif.adrv9042_rx()
    link.set_quick_configuration_mode("M16L4Np16S1", "jesd204c")
    link.sample_clock = 491_520_000
    assert link.bit_clock == 32_440_320_000
    link.validate_config()
    link.E, link.K = 3, 96
    link.validate_config()
    assert link.multiframe_clock == 5_120_000
    link.K = 32
    with pytest.raises(ValueError, match="256"):
        link.validate_config()
    link.E, link.K = 1, 32
    link.sample_clock += 1
    with pytest.raises(ValueError, match="lane rate"):
        link.validate_config()


@pytest.mark.parametrize(
    "change,match",
    [
        ({"F": 8}, "packing"),
        ({"K": 1}, "multiframe"),
        ({"N": 16, "CS": 1}, "control"),
        ({"sample_clock": 0}, "sample"),
        ({"lane_mapping": [0, 0]}, "lane"),
    ],
)
def test_invalid_transport(change, match):
    link = adijif.adrv9042_rx()
    link.set_quick_configuration_mode("M4L2Np16S1", "jesd204b")
    for key, value in change.items():
        setattr(link, key, value)
    with pytest.raises(ValueError, match=match):
        link.validate_config()


def test_control_bits_and_noncanonical_framing():
    link = adijif.adrv9042_rx()
    link.set_quick_configuration_mode("M4L2Np16S1", "jesd204b")
    link.N, link.CS, link.K = 14, 2, 8
    link.validate_config()
    assert link.get_current_jesd_mode_settings()["CS"] == 2


def test_density_and_instance_changes():
    link = adijif.adrv9042_rx()
    link.set_quick_configuration_mode("M4L2Np16S1", "jesd204b")
    assert link.HD == 0  # two complete converter samples in each lane frame
    link.link_index = 2
    assert link.L_available == [1, 2]
    assert max(link.M_available) == 32
    with pytest.raises(ValueError, match="link_index"):
        link.link_index = 3


def test_agent_discovery_and_nested_properties():
    from adijif.agent_api import (
        _apply_config_recursively,
        list_components,
        query_jesd_modes,
    )

    assert "ADRV9042" in list_components("converter")["components"]
    modes = query_jesd_modes("ADRV9042_RX", '{"M": 16, "L": 8, "Np": 16}')
    assert modes["jesd_modes"]
    device = adijif.adrv9042()
    _apply_config_recursively(
        device,
        {
            "reference_clock": 245_760_000,
            "framer0": {"enabled": False},
            "framer2": {"enabled": True},
        },
    )
    assert device._nested == ["framer2", "deframer0"]


def test_combined_links_aliases_lane_conflicts_and_rates():
    dev = adijif.adrv9042()
    assert dev.adc is dev.framer0 and dev.dac is dev.deframer0
    assert dev.obs is dev.framer2
    assert dev._nested == ["framer0", "deframer0"]
    dev.validate_config()
    dev.obs.enabled = True
    assert dev._get_converters() == [dev.framer0, dev.framer2, dev.deframer0]
    with pytest.raises(ValueError, match="lane"):
        dev.validate_config()
    dev.adc.set_quick_configuration_mode("M8L4Np16S1", "jesd204c")
    dev.obs.lane_mapping = [4, 5]
    dev.validate_config()
    dev.obs.sample_clock = 184_320_000
    with pytest.raises(ValueError, match="power of two"):
        dev.validate_config()


def test_reference_required_and_shared_rational_sysref():
    dev = adijif.adrv9042()
    with pytest.raises(ValueError, match="reference_clock"):
        dev.get_required_clocks()
    dev.reference_clock = 245_760_000
    dev.sysref_dividers = [1, 3, 64]
    candidates = dev.sysref_candidates()
    assert candidates
    for rate in candidates:
        assert all(
            (Fraction(str(v)) / rate).denominator == 1
            for v in [
                dev.reference_clock,
                dev.adc.multiframe_clock,
                dev.dac.multiframe_clock,
            ]
        )
    assert dev.get_required_clock_names() == [
        "adrv9042_ref_clk",
        "framer0_sysref",
        "deframer0_sysref",
    ]
    assert len(dev.get_required_clocks()) == 3
    dev.reference_clock = 0
    with pytest.raises(ValueError, match="reference_clock"):
        dev.get_required_clocks()


def test_combined_slot_identity_cannot_be_changed():
    device = adijif.adrv9042()
    device.framer1.enabled = True
    device.framer1.lane_mapping = [2, 3]
    device.framer1.link_index = 0
    with pytest.raises(ValueError, match="hardware index"):
        device.validate_config()


def test_preset_discovery_restores_e():
    from adijif.tools.explorer.src.pages.helpers.jesd import (
        get_jesd_controls,
        get_valid_jesd_modes,
    )

    link = adijif.adrv9042_rx()
    link.set_quick_configuration_mode("M4L2Np16S1", "jesd204c")
    link.E, link.K = 3, 192
    options, modes = get_jesd_controls(link)
    assert "E" in options
    rows, found = get_valid_jesd_modes(
        link, modes, {"M": [4], "L": [2], "Np": [16], "S": [1]}
    )
    assert rows and found
    assert link.E == 3 and link.K == 192


@pytest.mark.parametrize(
    "part", ["adrv9042_rx", "adrv9042_tx", "adrv9042_obs", "adrv9042"]
)
def test_system_solve_and_reconfigure(part):
    from .common import skip_solver

    skip_solver("CPLEX")
    system = adijif.system(part, "ad9528", "xilinx", 122_880_000)
    system.fpga.setup_by_dev_kit_name("zcu102")
    dev = system.converter
    dev.reference_clock = 245_760_000
    result = system.solve()
    assert (
        result["clock"]["output_clocks"][f"{dev.name}_ref_clk"]["rate"]
        == 245_760_000
    )
    if part == "adrv9042":
        assert set(result["converter"]["links"]) == {"framer0", "deframer0"}
        dev.adc.enabled = False
        dev.obs.enabled = True
        dev.obs.sample_clock = 245_760_000
        result = system.solve()
        assert "jesd_framer0" not in result
        assert result["jesd_framer2"]["sample_clock"] == 245_760_000
        assert dev.obs.model is system.model
    else:
        dev.sample_clock = 245_760_000
        result = system.solve()
        assert result[f"jesd_{dev.name}"]["sample_clock"] == 245_760_000


def test_all_five_links_solve():
    from .common import skip_solver

    skip_solver("CPLEX")
    system = adijif.system("adrv9042", "hmc7044", "xilinx", 122_880_000)
    system.fpga.setup_by_dev_kit_name("zcu102")
    dev = system.converter
    dev.reference_clock = 245_760_000
    for index, name in enumerate(dev._link_names):
        link = getattr(dev, name)
        link.enabled = True
        link.lane_mapping = (
            [index % 3 * 2, index % 3 * 2 + 1]
            if index < 3
            else [(index - 3) * 2, (index - 3) * 2 + 1]
        )
    result = system.solve()
    assert len(result["converter"]["links"]) == 5
    sysrefs = [
        result["clock"]["output_clocks"][f"{name}_sysref"]["rate"]
        for name in dev._link_names
    ]
    assert len(set(sysrefs)) == 1
    assert len({key for key in result if key.startswith("fpga_")}) == 5


def test_incompatible_reference_clock_constraint_fails():
    from .common import skip_solver

    skip_solver("CPLEX")
    system = adijif.system("adrv9042_rx", "ad9528", "xilinx", 122_880_000)
    system.fpga.setup_by_dev_kit_name("zcu102")
    system.converter.reference_clock = 245_760_000
    with pytest.raises(
        Exception, match="No solution|Solution Not Found|No Solution"
    ):
        system.solve(out_clock_constraints={"ADRV9042_RX_ref_clk": 122_880_000})
