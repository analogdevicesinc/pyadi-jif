import adijif
from rich import print

"""
Example extracted from the default adrv9009 devicetree, and HDL project.

- JESD204 parameters
    - https://github.com/analogdevicesinc/hdl/blob/master/projects/adrv9009/zcu102/system_project.tcl#L26

- decimation:
    - adi,rx-profile-rx-fir-decimation = <2>  -> RFIR=2
    - adi,rx-profile-rx-dec5-decimation = <4> -> RHB2 and RHB3 enabled
    - adi,rx-profile-rhb1-decimation = <1>    -> bypass
    - decimation: 2 * 4 * 1 = 8

- interpolation:
    - adi,tx-profile-tx-fir-interpolation = <1>  -> bypass
    - adi,tx-profile-thb1-interpolation = <2>    -> THB1 enabled
    - adi,tx-profile-thb2-interpolation = <2>    -> THB2 enabled
    - adi,tx-profile-thb3-interpolation = <2>    -> THB3 enabled
    - adi,tx-profile-tx-int5-interpolation = <1> -> bypass
    - interpolation = 1 * 2 * 2 * 2 * 1 = 8

- sample_clock
    - adi,rx-profile-rx-output-rate_khz = IQ data rate = <245760>
    - adi,tx-profile-tx-input-rate_khz = IQ data rate at the input of the TFIR = <245760>;
    - sample_clock = 245.76e6
"""


vcxo = 122.88e6
sys = adijif.system("adrv9009", "ad9528", "xilinx", vcxo=vcxo)

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
sys.converter.adc.sample_clock = 245.76e6
sys.converter.dac.interpolation = 8
sys.converter.dac.sample_clock = 245.76e6


conf = sys.solve()
print(conf)
