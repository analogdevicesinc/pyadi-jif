# Clock Chip Settings

Clock chip models are the central components of the **pyadi-jif** library and
govern most system-level clock limitations. Since clock chips provide the clocks
for converters, FPGAs, and optional external PLLs, they must understand the
frequency requirements for each downstream component.

## Theory of Operation

In traditional systems clock chips work as frequency generation systems with
multiple PLLs. One PLL, typically called PLL1, is used for synchronization and
jitter cleanup. The second PLL, typically called PLL2, is used for frequency
generation from a VCXO or PLL1 and is divided down to provide different output
frequencies. The current clock chip models only model PLL2 with a VCXO source.

<p align="center">
  <img width="600" src="../_static/imgs/draw/clock.svg">
</p>

## Standalone Usage

Clock chip models can be used standalone if the required clocks are known. The
required clocks are supplied directly with `set_requested_clocks`. The example
below configures an AD9523-1 to generate converter, FPGA, and SYSREF clocks from
a 125 MHz VCXO while constraining `n2` to 24.

```python
import adijif
import pprint

clk = adijif.ad9523_1()
clk.n2 = 24

vcxo = 125000000
output_clocks = [1e9, 500e6, 7.8125e6]
clock_names = ["ADC", "FPGA", "SYSREF"]

clk.set_requested_clocks(vcxo, output_clocks, clock_names)
clk.solve()
o = clk.get_config()
pprint.pprint(o)
```

When using clock chip models standalone, `set_requested_clocks` must be called
before `solve`. When using the `system` class this is handled internally based
on the components set at initialization.

## System Usage

In a system solve, the clock chip is the source for each requested clock unless
an external PLL is inserted. Typical clock chip outputs are:

- converter device or reference clocks
- converter SYSREF clocks
- FPGA reference clocks
- FPGA device clocks when `device_clock_source` is `external`
- external PLL reference clocks
- optional ADF4030 BSYNC reference clocks

```{mermaid}
flowchart LR
    VCXO[VCXO] --> CLK[Clock chip]
    CLK -->|converter ref/device clock| CNV[Converter]
    CLK -->|FPGA ref clock| FPGA[FPGA]
    CLK -->|device clock| FPGA
    CLK -->|SYSREF| CNV
    CLK -->|SYSREF| FPGA
```

The names in the solved `clock["output_clocks"]` dictionary are generated from
the device names and clock purpose. For example, a system may contain names such
as `AD9081_ref_clk`, `AD9081_sysref`, `AD9081_fpga_ref_clk`, and
`AD9081_fpga_device_clk`. These names can be constrained through the system
clock bundle API when the default search space is too broad.

```python
sys.clocks.constrain("AD9081_fpga_ref_clk", equal_to=250e6)
sys.clocks.constrain("AD9081_sysref", min=1e6, max=20e6)
```

Clock chip divider limits can also be narrowed directly on the clock object. This
is useful when the board design has a fixed divider plan or when the solver
should avoid divider values that are not practical in hardware.

```python
sys.clock.d = [2, 4, 8, 16, 32, 64, 128]
sys.clock.vco_min = 2.4e9
sys.clock.vco_max = 3.0e9
```
