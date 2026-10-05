# Finding Extreme Lane and Sample Rates

`adijif.utils.find_extreme_rate(...)` answers "what is the fastest (or
slowest) this converter can run?" by replacing the converter's scalar
`sample_clock` with a solver variable and asking CPLEX to push it to the
boundary. Unlike `adijif.utils.get_max_sample_rates`, which iterates
modes outside the solver, `find_extreme_rate` routes through the same
objective framework used by [Constraints and Optimization](optimization.md),
so its results respect every constraint the solver knows about — including,
optionally, a full clock-chain through a real clock chip.

The function has two modes:

- **Constraint-only**: no `clock` argument. Builds a minimal model
  bounded by the JESD-class limits and (optionally) an FPGA's QPLL VCO
  cap. Fast.
- **Full clock-chain**: pass `clock`, `fpga`, and `vcxo`. The solver
  additionally requires the result to be reachable by the clock chip's
  dividers.

When `mode` is omitted, every entry in `conv.quick_configuration_modes`
is enumerated and the best result is returned.

## Prerequisites

- pyadi-jif installed with the CPLEX extra (`pip install 'pyadi-jif[cplex]'`).
  `find_extreme_rate` is CPLEX-only.
- Familiarity with [Usage Flows](flow.md).

## Step 1: Maximize lane rate without any FPGA

The simplest call takes only a converter and asks for the largest lane
rate achievable across every JESD mode it supports:

```{exec_code}
:caption_output: Max lane rate, AD9081_RX

import adijif

conv = adijif.ad9081_rx()
result = adijif.utils.find_extreme_rate(
    conv, target="lane", sense="max"
)
print(f"bit_clock    = {result['bit_clock']:.4e}")
print(f"sample_clock = {result['sample_clock']:.4e}")
print(f"mode         = {result['mode']} ({result['jesd_class']})")
print(f"M={result['M']}, L={result['L']}, Np={result['Np']}")
```

The result is whichever mode achieves the highest `bit_clock` within the
JESD204C class limits.

The input `conv` is not mutated — the function deep-copies it for each
attempt — so it is safe to call against an object you intend to use
afterward.

## Step 2: Apply an FPGA lane-rate cap

Pass an `fpga` to bound the search by the FPGA's QPLL VCO ceiling (and
its `max_serdes_lanes`):

```{exec_code}
:caption_output: Max lane rate, AD9081_RX + ZC706

import adijif

conv = adijif.ad9081_rx()
fpga = adijif.xilinx()
fpga.setup_by_dev_kit_name("zc706")
fpga.sys_clk_select = "XCVR_QPLL0"

result = adijif.utils.find_extreme_rate(
    conv, target="lane", sense="max", fpga=fpga
)
print(f"bit_clock    = {result['bit_clock']:.4e}")
print(f"sample_clock = {result['sample_clock']:.4e}")
print(f"mode         = {result['mode']} ({result['jesd_class']})")
```

With ZC706 in the loop the cap drops from the JESD204C maximum to the
QPLL-derived bit-rate limit (10.3125 GHz for 7-Series GTX).

## Step 3: Pin a JESD mode

Pass `mode=` (and `jesd_class=` if the mode key is ambiguous across
JESD204B and JESD204C) to skip enumeration and solve for one mode only.
This is the fast path when you already know which mode you want and just
need the maximum achievable rate within it:

```{exec_code}
:caption_output: Max lane rate in a specific mode

import adijif

conv = adijif.ad9081_rx()
fpga = adijif.xilinx()
fpga.setup_by_dev_kit_name("zc706")
fpga.sys_clk_select = "XCVR_QPLL0"

result = adijif.utils.find_extreme_rate(
    conv,
    target="lane",
    sense="max",
    mode="19.0",
    jesd_class="jesd204b",
    fpga=fpga,
)
print(f"bit_clock    = {result['bit_clock']:.4e}")
print(f"sample_clock = {result['sample_clock']:.4e}")
```

## Step 4: Minimize instead

Set `sense="min"` to find the slowest valid rate, or `target="sample"`
to optimize the sample rate directly instead of the lane rate:

```{exec_code}
:caption_output: Minimum sample rate

import adijif

conv = adijif.ad9081_rx()
result = adijif.utils.find_extreme_rate(
    conv, target="sample", sense="min",
    mode="19.0", jesd_class="jesd204b",
)
print(f"sample_clock = {result['sample_clock']:.4e}")
print(f"bit_clock    = {result['bit_clock']:.4e}")
```

The minimum sample rate is whatever brings `bit_clock` down to the
JESD204B class minimum (1.5 GHz here) or the device's
`sample_clock_min`, whichever binds first.

## Step 5: Solve with a full clock chain

Adding a `clock` chip (plus `vcxo`) takes the analysis from "what's
theoretically achievable" to "what's actually reachable end-to-end". The
solver now also has to satisfy the clock chip's dividers, so a mode that
needs an awkward fractional reference clock can become infeasible. When
`clock` is supplied, `fpga` and `vcxo` are required:

```{exec_code}
:caption_output: Max lane rate, AD9680 + HMC7044 + ZC706

import adijif

conv = adijif.ad9680()
clock = adijif.hmc7044()
fpga = adijif.xilinx()
fpga.setup_by_dev_kit_name("zc706")

result = adijif.utils.find_extreme_rate(
    conv,
    target="lane",
    sense="max",
    mode="64",
    jesd_class="jesd204b",
    clock=clock,
    fpga=fpga,
    vcxo=125e6,
)
print(f"bit_clock     = {result['bit_clock']:.4e}")
print(f"sample_clock  = {result['sample_clock']:.4e}")
print(f"clock_config keys: {list(result['clock_config'].keys())}")
print(f"fpga_config keys:  {list(result['fpga_config'].keys())}")
```

In clock-chain mode the result dict includes `clock_config` (HMC7044
dividers and output rates) and `fpga_config` (FPGA transceiver PLL
selection) — everything you need to reproduce the solution in a full
`adijif.system` solve.

## Result shape

Every call returns the same dict shape:

| key                | meaning                                                       |
| ------------------ | ------------------------------------------------------------- |
| `sample_clock`     | Sample rate (Hz) of the winning configuration                 |
| `bit_clock`        | Lane rate (Hz)                                                |
| `mode`             | JESD quick-configuration mode key                             |
| `jesd_class`       | `"jesd204b"` or `"jesd204c"`                                  |
| `M`, `L`, `Np`, `F`, `S`, `K` | Resolved JESD parameters                           |
| `clock_config`     | Clock chip config (full chain mode only; otherwise `None`)    |
| `fpga_config`      | FPGA transceiver config (full chain mode only)                |
| `objective_value`  | Numerical value the solver optimized — `bit_clock` when `target="lane"`, `sample_clock` when `target="sample"` |

## Choosing the right mode

| Goal                                                | Args                                |
| --------------------------------------------------- | ----------------------------------- |
| Quick JESD-class ceiling check                      | `target`, `sense`                   |
| Add an FPGA lane-rate cap                           | `+ fpga=`                           |
| Pin a specific mode                                 | `+ mode=, jesd_class=`              |
| Require the clock chip to actually produce the ref  | `+ clock=, fpga=, vcxo=`            |

## Relationship to `get_max_sample_rates`

`adijif.utils.get_max_sample_rates` returns one entry per `M`
(channel count) and uses a closed-form check rather than the solver, so
it is faster for "give me the per-channel-count summary" workflows. Use
`find_extreme_rate` when you want a single global winner, a `min`
sense, or a clock-chain-aware result. The two agree on the constraint-only
path for the configurations they both cover.

## What's next

- The {py:class}`adijif.optimization.Objective` framework
  (see [Constraints and Optimization](optimization.md)) is what
  `find_extreme_rate` ultimately calls into; everything you can express
  by hand with `sys.add_objective` is available there.
- Nested converters (full MxFE / transceiver devices) are rejected by
  `find_extreme_rate`; pass the rx or tx side directly (e.g.
  `adijif.ad9081_rx()`).
- The gekko solver backend is not supported — the function requires
  `solver="CPLEX"` and the `[cplex]` extra.
