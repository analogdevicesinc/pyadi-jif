"""Top-level package for pyadi-jif."""

__author__ = """Analog Devices, Inc."""
__email__ = "travis.collins@analog.com"
__version__ = "0.1.4"

import adijif.solvers
import adijif.utils
from adijif.clocks.ad9523 import ad9523_1
from adijif.clocks.ad9528 import ad9528
from adijif.clocks.ad9545 import ad9545
from adijif.clocks.hmc7044 import hmc7044
from adijif.clocks.ltc6952 import ltc6952
from adijif.clocks.ltc6953 import ltc6953
from adijif.converters.ad9081 import (
    ad9081,
    ad9081_rx,
    ad9081_tx,
    ad9082,
    ad9082_rx,
    ad9082_tx,
)
from adijif.converters.ad9084 import ad9084_rx, ad9088_rx
from adijif.converters.ad9144 import ad9144
from adijif.converters.ad9152 import ad9152
from adijif.converters.ad9680 import ad9680
from adijif.converters.adrv9009 import adrv9009, adrv9009_rx, adrv9009_tx
from adijif.fpgas.xilinx import xilinx
from adijif.fpgas.xilinx.bf import xilinx_bf
from adijif.plls.adf4030 import adf4030
from adijif.plls.adf4371 import adf4371
from adijif.plls.adf4382 import adf4382
from adijif.system import system
from adijif.types import range

# Uppercase aliases used by the MCP server registry
AD9081 = ad9081
AD9081_RX = ad9081_rx
AD9081_TX = ad9081_tx
AD9082 = ad9082
AD9082_RX = ad9082_rx
AD9082_TX = ad9082_tx
AD9084_RX = ad9084_rx
AD9088_RX = ad9084_rx
AD9144 = ad9144
AD9152 = ad9152
AD9680 = ad9680

ADRV9009 = adrv9009
ADRV9009_RX = adrv9009_rx
ADRV9009_TX = adrv9009_tx
AD9523_1 = ad9523_1
AD9528 = ad9528
AD9545 = ad9545
HMC7044 = hmc7044
LTC6952 = ltc6952
LTC6953 = ltc6953
XILINX = xilinx
XILINX_BF = xilinx_bf
ADF4030 = adf4030
ADF4371 = adf4371
ADF4382 = adf4382
