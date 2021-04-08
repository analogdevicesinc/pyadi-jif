# FPGAs

FPGA clock models focus upon the PLLs inside different FPGA variants that drive different transceivers which connect to data converters. Currently, only specific Xilinx FPGA models are supported, but more are planned. However, the configurations determined by **pyadi-jif** are in the context of the [ADI JESD Interface Framework](https://wiki.analog.com/resources/tools-software/linux-drivers/jesd204/jesd204-fsm-framework) and their related HDL cores. This is important since IP from different vendors have different supported modes.

The FPGA models are similar to converter models but they require converter objects to be passed to them for configuration. From the converter objects the FPGA classes can derive the dependent clocks and JESD configuration. Due to this limitation, FPGA classes cannot be used standalone like data converter or clock chip classes.

The second primary limitation is that the FPGA hardware model must be known and set beforehand. The FPGA hardware model determines clock ranges, internal PLL limits, and transceiver constraints. Since these can vary widely, making the internal solvers directly determine supported FPGAs would be a very burdensome task. However, **pyadi-jif** could be called in a loop to validate against different FPGA hardware models.

!!! note "**pyadi-jif** is not endorsed or verified by Xilinx or Intel"

## Xilinx FPGAs

For Xilinx FPGAs both 7000 and Ultrascale device types can be parameterized. However, since specifications can vary widely depending on chip model or board, extensive configuration needs to be provided. A pre-existing table of boards can be leveraged through the `setup_by_dev_kit_name` method. This includes support for:

-   ZC706
-   ZCU102
-   VCU118

Otherwise to manually configure an FPGA object requires setting the following:

```python
fpga.transceiver_voltage = 800
fpga.transciever_type = "GTX2"
fpga.fpga_family = "Zynq"
fpga.fpga_package = "FF"
fpga.speed_grade = -2
fpga.ref_clock_min = 60000000
fpga.ref_clock_max = 670000000

```

### Selecting QPLL or CPLL

Both CPLL and QPLL types are supported and can either be automatically determined or forced to use either. This is done through two class properties:

```python
sys = adijif.system("ad9680", "ad9523_1", "xilinx", vcxo)
...
sys.fpga.force_cpll = 1 # Force use of CPLL
# or
sys.fpga.force_qpll = 1 # Force use of QPLL
# or (Default) let solver select
sys.fpga.force_cpll = 0
sys.fpga.force_qpll = 0
```

The solver tries to use the CPLL since it is more flexible architecturally. For more detail on the 7000 Series PLL architecture consult [ug476](https://www.xilinx.com/support/documentation/user_guides/ug476_7Series_Transceivers.pdf).

### Current known limitations

-   When multiple converters are connected to the same FPGA, or RX and TX from the same converter, the solver does not force the clocks to come from a single QTile.

## Intel FPGAs

None supported yet.

## Example usage

As mentioned the FPGA classes can not be used standalone. Therefore, the system class must be used when interfacing with the solvers. Below is a simple example based around using the [AD-FMCDAQ2-EBZ](https://www.analog.com/en/design-center/evaluation-hardware-and-software/evaluation-boards-kits/eval-ad-fmcdaq2-ebz.html) and a Xilinx ZC706.

```python
# Create instance of system class with desired parts
sys = adijif.system("ad9680", "ad9523_1", "xilinx", 125000000)
# Set Converter clocking requirements
sys.converter.sample_clock = 1e9
sys.converter.datapath_decimation = 1
sys.converter.L = 4
sys.converter.M = 2
sys.converter.N = 14
sys.converter.Np = 16
sys.converter.K = 32
sys.converter.F = 1
# Set FPGA clocking requirements
sys.fpga.setup_by_dev_kit_name("zc706")
# Call solver and collect configuration
config = sys.solve()
pprint.pprint(config['fpga'])
```

**Sample Output**

```bash
{'band': 1.0,
 'd': 1.0,
 'm': 1.0,
 'n': 100.0,
 'qty4_full_rate_enabled': 0.0,
 'type': 'qpll',
 'vco': 10000000000.0}
```

The output in this case shows that the QPLL is used (probably required), the upper band related to VCO1 is used, and all the necessary dividers are provided for configuration.
