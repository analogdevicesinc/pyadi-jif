import adijif
from rich import print

"""
AD9371 (Mykonos) example with AD9528 clock chip and a Xilinx ZCU102 FPGA.

AD9371 has a 6.144 GHz JESD204B lane-rate cap, so the sample rate is kept at
122.88 MHz here to leave headroom across the supported quick-configuration
modes.

- decimation:
    - RFIR = 2
    - Dec5 / RHB1 / RHB2 enabled to reach a total decimation of 8

- interpolation:
    - TFIR = 1 (bypass)
    - THB1 / THB2 / THB3 enabled to reach a total interpolation of 8

- sample_clock = 122.88 MHz (RX and TX I/Q data rate)
"""


vcxo = 122.88e6
sys = adijif.system("ad9371", "ad9528", "xilinx", vcxo=vcxo)

# Clock
sys.clock.m1 = 3
sys.clock.use_vcxo_doubler = True

# FPGA
sys.fpga.setup_by_dev_kit_name("zcu102")
sys.fpga.force_qpll = True


# Converters
mode_rx = adijif.utils.get_jesd_mode_from_params(
    sys.converter.adc, M=4, L=2, S=1, Np=16,
)
sys.converter.adc.set_quick_configuration_mode(mode_rx[0]['mode'], mode_rx[0]['jesd_class'])

mode_tx = adijif.utils.get_jesd_mode_from_params(
    sys.converter.dac, M=4, L=4, S=1, Np=16,
)
sys.converter.dac.set_quick_configuration_mode(mode_tx[0]['mode'], mode_tx[0]['jesd_class'])

sys.converter.adc.decimation = 8
sys.converter.adc.sample_clock = 122.88e6
sys.converter.dac.interpolation = 8
sys.converter.dac.sample_clock = 122.88e6


conf = sys.solve()
print(conf)
