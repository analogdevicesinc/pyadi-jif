# External SYSREF Usage

Some systems split SYSREF generation from the clock chip that generates converter
and FPGA reference clocks. This is useful when the SYSREF source has dedicated
synchronization behavior, as with ADF4030, or when the board architecture routes
SYSREF through a separate device.

## Direct External SYSREF

Without an external SYSREF PLL, the clock chip produces both device/reference
clocks and SYSREF.

```{mermaid}
flowchart LR
    VCXO[VCXO] --> CLK[Clock chip]
    CLK -->|converter ref/device clock| CNV[Converter]
    CLK -->|FPGA ref clock| FPGA[FPGA]
    CLK -->|FPGA device clock| FPGA
    CLK -->|SYSREF| CNV
    CLK -->|SYSREF| FPGA
```

With `add_pll_sysref`, the clock chip remains responsible for the ordinary
clocking plan while ADF4030 produces SYSREF for the selected converter and FPGA
models.

```{mermaid}
flowchart LR
    VCXO[VCXO] --> CLK[Clock chip]
    CLK -->|converter ref/device clock| CNV[Converter]
    CLK -->|FPGA ref clock| FPGA[FPGA]
    CLK -->|FPGA device clock| FPGA
    VCXO --> ADF[ADF4030]
    ADF -->|SYSREF| CNV
    ADF -->|SYSREF| FPGA
```

```python
sys.add_pll_sysref("adf4030", 100e6, sys.converter, sys.fpga)
```

`add_pll_sysref` supports both simple converters and nested converters such as
AD9081. When the converter object contains ADC and DAC children, the external
SYSREF source is applied to the relevant nested converter clocks.

## ADF4030 Example

The example below follows the AD9081 pattern and adds ADF4030 as the SYSREF
source for both the converter and FPGA. The clock chip still solves the converter
device clock and FPGA reference/device clock paths.

```python
import adijif

vcxo = 100e6
cddc = 6
fddc = 4

sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo, solver="CPLEX")
sys.fpga.setup_by_dev_kit_name("zcu102")
sys.fpga.ref_clock_constraint = "Unconstrained"
sys.fpga.sys_clk_select = "XCVR_QPLL0"
sys.fpga.out_clk_select = "XCVR_PROGDIV_CLK"

sys.converter.adc.sample_clock = 2900000000 / (cddc * fddc)
sys.converter.dac.sample_clock = 5800000000 / (cddc * fddc)
sys.converter.adc.datapath.cddc_decimations = [cddc] * 4
sys.converter.adc.datapath.fddc_decimations = [fddc] * 8
sys.converter.adc.datapath.fddc_enabled = [True] * 8
sys.converter.dac.datapath.cduc_interpolation = cddc
sys.converter.dac.datapath.fduc_interpolation = fddc
sys.converter.dac.datapath.fduc_enabled = [True] * 8

sys.add_pll_sysref("adf4030", vcxo, sys.converter, sys.fpga)

sys.converter.dac.set_quick_configuration_mode("0", "jesd204c")
sys.converter.adc.set_quick_configuration_mode("1.0", "jesd204c")

cfg = sys.solve()
```

After solving, the configuration includes a `clock_ext_pll_sysref_adf4030`
section. Converter and FPGA SYSREF clock names are supplied by that PLL instead
of by the clock chip output list.

## BSYNC Reference

ADF4030 also supports an optional BSYNC reference. In **pyadi-jif**, this is
modeled by passing `bsync_reference` to `add_pll_sysref`.

```{mermaid}
flowchart LR
    VCXO[VCXO] --> CLK[Clock chip]
    CLK -->|converter ref/device clock| CNV[Converter]
    CLK -->|FPGA ref/device clocks| FPGA[FPGA]
    CLK -->|BSYNC reference| ADF[ADF4030]
    ADF -->|SYSREF| CNV
    ADF -->|SYSREF| FPGA
```

When `bsync_reference` is a clock chip object, the system requests one additional
clock chip output named `<pll>_bsync_reference`. That output is constrained to
match the ADF4030 SYSREF output rate.

```python
sys.add_pll_sysref(
    "adf4030",
    vcxo,
    sys.converter,
    sys.fpga,
    bsync_reference=sys.clock,
)
```

This is useful when the board routes a clock chip output to the ADF4030 BSYNC
input and the solver should choose a coherent rate for both paths. The solved
configuration will contain both:

- `clock["output_clocks"]["adf4030_bsync_reference"]`
- `clock_ext_pll_sysref_adf4030["output_clocks"][...]`

For a fixed BSYNC reference rate, pass a numeric frequency instead of the clock
object:

```python
sys.add_pll_sysref(
    "adf4030",
    vcxo,
    sys.converter,
    sys.fpga,
    bsync_reference=7.8125e6,
)
```

The numeric form constrains the ADF4030 output to the supplied rate and does not
allocate an additional clock chip output.

## Constraints and Limits

The ADF4030 model enforces its input, PFD, VCO, output divider, and BSYNC
reference ranges during the solve. The BSYNC reference must be between the
model's `bsync_freq_min` and `bsync_freq_max`. If the clock chip cannot generate
the requested BSYNC reference, narrow or relax the clock chip output divider
constraints, the ADF4030 `o` divider options, or the requested SYSREF rate.
