"""Solve external clocks for explicit ADRV9042 interface settings.

Replace these rates and transport tuples with the values of an ACE-approved
configuration. This example does not generate or program a firmware profile.
"""

from pprint import pprint

import adijif


def standalone() -> dict:
    """Solve a single receive link with an AD9528 and ZCU102."""
    system = adijif.system("adrv9042_rx", "ad9528", "xilinx", 122_880_000)
    system.fpga.setup_by_dev_kit_name("zcu102")
    system.converter.reference_clock = 245_760_000
    system.converter.set_quick_configuration_mode("M16L8Np16S1", "jesd204c")
    system.converter.sample_clock = 491_520_000
    return system.solve()


def combined() -> dict:
    """Solve RX, observation RX, and TX together with nonoverlapping lanes."""
    system = adijif.system("adrv9042", "ad9528", "xilinx", 122_880_000)
    system.fpga.setup_by_dev_kit_name("zcu102")
    device = system.converter
    device.reference_clock = 245_760_000
    device.adc.set_quick_configuration_mode("M8L4Np16S1", "jesd204c")
    device.adc.sample_clock = 245_760_000
    device.obs.enabled = True
    device.obs.set_quick_configuration_mode("M4L2Np16S1", "jesd204c")
    device.obs.sample_clock = 245_760_000
    device.obs.lane_mapping = [4, 5]
    device.dac.set_quick_configuration_mode("M8L4Np16S1", "jesd204c")
    device.dac.sample_clock = 245_760_000
    return system.solve()


if __name__ == "__main__":
    pprint(standalone())
    pprint(combined())
