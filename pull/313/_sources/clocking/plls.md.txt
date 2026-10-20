# PLL Settings

External PLL models are used when a clock path should not be driven directly by
the system clock chip. In **pyadi-jif**, external PLLs are connected through the
`system` object so the clock chip, PLL, converter, and FPGA constraints are
solved together.

## Inline Converter PLLs

Use `add_pll_inline` when a PLL sits between the clock chip and a converter
reference clock. The clock chip provides the PLL reference, and the PLL output
drives the converter.

```{mermaid}
flowchart LR
    VCXO[VCXO] --> CLK[Clock chip]
    CLK -->|PLL reference| PLL[External PLL]
    PLL -->|converter ref/device clock| CNV[Converter]
    CLK -->|FPGA ref/device clocks| FPGA[FPGA]
    CLK -->|SYSREF| CNV
    CLK -->|SYSREF| FPGA
```

```python
sys = adijif.system("ad9081", "hmc7044", "xilinx", 100e6)
sys.add_pll_inline("adf4371", sys.clock, sys.converter)
```

The solved configuration contains a `clock_ext_pll_<name>` entry for the PLL and
the converter configuration identifies the external clock source.

## SYSREF PLLs

Use `add_pll_sysref` when an external PLL provides SYSREF to a converter, an
FPGA, or both. This is the topology used with ADF4030 when SYSREF generation is
split away from the clock chip that provides device and reference clocks.

```{mermaid}
flowchart LR
    VCXO[VCXO] --> CLK[Clock chip]
    CLK -->|converter ref/device clock| CNV[Converter]
    CLK -->|FPGA ref/device clocks| FPGA[FPGA]
    VCXO --> ADF[ADF4030 SYSREF PLL]
    ADF -->|SYSREF| CNV
    ADF -->|SYSREF| FPGA
```

```python
sys.add_pll_sysref("adf4030", 100e6, sys.converter, sys.fpga)
```

The first argument selects the PLL model. The second argument is the PLL input
reference and may be a numeric frequency, a clock object, or another supported
clock source expression. The converter and FPGA arguments identify which devices
receive the SYSREF output.

## ADF4030 Settings

The ADF4030 model currently exposes the reference divider `r`, feedback divider
`n`, and output divider `o`. These may be left unconstrained for the solver or
narrowed before the system solve.

```python
adf4030 = sys.get_sysref_pll_by_name("adf4030")
adf4030.r = [5, 10]
adf4030.n = range(120, 131)
adf4030.o = [320, 640, 1280]
```

In a solved configuration, ADF4030 appears as `clock_ext_pll_sysref_adf4030`.
Its `output_clocks` map contains the SYSREF clock names and their solved rates.

## Choosing the Topology

Use a clock chip output directly when the clock chip can generate a suitable
SYSREF and reference/device clock plan. Add an inline PLL when the converter
sample clock needs a cleaner or higher-frequency source than the clock chip can
provide directly. Add a SYSREF PLL when SYSREF timing needs a dedicated source,
or when SYSREF must be aligned through ADF4030 BSYNC behavior.
