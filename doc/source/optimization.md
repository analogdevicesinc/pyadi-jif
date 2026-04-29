# Constraints and Optimization

In this tutorial you will steer the JIF solver toward the configuration *you*
want by layering two complementary tools on top of `sys.solve()`:

- **Custom clock constraints** — `clocks.constrain(...)` narrows the set of
  *valid* solutions by pinning, ranging, or restricting inter-component
  clocks (e.g. "the FPGA reference clock must be between 250 and 350 MHz").
- **Optimization objectives** — `sys.add_objective(...)` (and the built-in
  per-component defaults) tell the solver which of the still-many valid
  solutions to *prefer* (e.g. "among valid configurations, minimize the
  VCO frequency").

Both tools share the same two-phase pattern: call `sys.initialize()` to
build the solver model, modify it (constraints or objectives), then call
`sys.do_solve()` to run the solver. By the end of this tutorial you will
have a working AD9680 + HMC7044 system that uses both tools together.

## Prerequisites

- pyadi-jif installed with the CPLEX extra (`pip install 'pyadi-jif[cplex]'`).
  Multi-tier (lexicographic) optimization requires the CPLEX backend.
- Familiarity with [Usage Flows](flow.md) — you should know how to build a
  `system` and call `sys.solve()`.

## Step 1: Solve with defaults

Every component class registers built-in objectives when its constraints
are set up — for example, the HMC7044 model registers a "minimize R2 input
divider" objective so the solver naturally biases toward simpler clock
trees. Build a baseline system without touching either API:

```{exec_code}
:caption_output: Default-objective solve

import adijif
import pprint

vcxo = 125_000_000
sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver="CPLEX")

sys.fpga.setup_by_dev_kit_name("zc706")
sys.converter.sample_clock = 1e9 / 2
sys.converter.datapath_decimation = 1
sys.converter.L = 4
sys.converter.M = 2
sys.converter.N = 14
sys.converter.Np = 16
sys.converter.K = 32
sys.converter.F = 1
sys.converter.HD = 1

cfg = sys.solve()
pprint.pprint(cfg["clock"])
```

Note the chosen `r2` divider and the rates inside `output_clocks` — the
next steps will steer them.

## Step 2: Constrain an inter-component clock

`sys.initialize()` returns a `ClocksBundle`: a dict-like view of every
clock that flows between high-level components (clock chip → converter,
clock chip → FPGA, etc.). Use `clocks.constrain(name, ...)` to narrow what
the solver can pick.

Pin the FPGA reference clock to a range and the converter sysref to an
exact value, then call `do_solve()` to honor them:

```{exec_code}
:caption_output: Constrained solve

import adijif
import pprint

vcxo = 125_000_000
sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver="CPLEX")
sys.fpga.setup_by_dev_kit_name("zc706")
sys.converter.sample_clock = 1e9 / 2
sys.converter.datapath_decimation = 1
sys.converter.L = 4
sys.converter.M = 2
sys.converter.N = 14
sys.converter.Np = 16
sys.converter.K = 32
sys.converter.F = 1
sys.converter.HD = 1

clocks = sys.initialize()
clocks.constrain("AD9680_fpga_ref_clk", range=(100e6, 200e6))
clocks.constrain("AD9680_sysref", equal_to=15_625_000)

cfg = sys.do_solve()
pprint.pprint(cfg["clock"]["output_clocks"])
```

Print `clocks.keys()` after `initialize()` to discover the exact names
available for your configuration. Common names include
`{converter}_ref_clk`, `{converter}_sysref`, `{converter}_fpga_ref_clk`,
and `{converter}_fpga_device_clk`.

`constrain` accepts:

- `equal_to=` — a number, another solver expression, or another clock name
  in the bundle.
- `min=`, `max=` — lower / upper bound on the rate.
- `range=(lo, hi)` — sugar for `min=lo, max=hi`.
- `choices=[...]` — list of allowed exact rates (CPLEX only).

For shapes not covered by these helpers, index the bundle directly and
add an expression to `sys.model` using the solver's native API.

## Step 3: Inspect active objectives

Constraints rule out invalid configurations; *objectives* rank the
remaining valid ones. Call `sys.list_objectives()` after `solve()` (or
after `initialize()`) to see every `Objective` the framework will apply.
Each entry carries its tier, sense, name, and the component that
registered it.

```{exec_code}
:caption_output: Active objectives

# --- hide: start ---
import adijif
vcxo = 125_000_000
sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver="CPLEX")
sys.fpga.setup_by_dev_kit_name("zc706")
sys.converter.sample_clock = 1e9 / 2
sys.converter.datapath_decimation = 1
sys.converter.L = 4
sys.converter.M = 2
sys.converter.N = 14
sys.converter.Np = 16
sys.converter.K = 32
sys.converter.F = 1
sys.converter.HD = 1
sys.solve()
# --- hide: stop ---
for obj in sys.list_objectives():
    print(f"{obj.component:>10}  tier={obj.tier}  sense={obj.sense:>3}  name={obj.name}")
```

Lower tier numbers have higher priority. Tier 0 is solved first; tier 1
only matters as a tie-breaker when tier 0 has multiple optima.

## Step 4: Add a custom user objective

Use `sys.add_objective(expr, sense=, tier=, name=)` to register your own
preference. The expression must reference solver variables that already
exist on a component (look in `sys.clock.config`, `sys.fpga.config`, etc.,
after the model is built).

To prefer configurations whose VCO runs as low as possible — for instance
to keep PLL bandwidth low — add a tier-0 objective that minimizes the VCO
expression:

```{exec_code}
:caption_output: Solve with a user objective

import adijif
import pprint

vcxo = 125_000_000
sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver="CPLEX")
sys.fpga.setup_by_dev_kit_name("zc706")
sys.converter.sample_clock = 1e9 / 2
sys.converter.datapath_decimation = 1
sys.converter.L = 4
sys.converter.M = 2
sys.converter.N = 14
sys.converter.Np = 16
sys.converter.K = 32
sys.converter.F = 1
sys.converter.HD = 1

sys.initialize()
sys.add_objective(
    sys.clock.config["vcxod"] * sys.clock.config["n2"] / sys.clock.config["r2"],
    sense="min",
    tier=0,
    name="user.vco_min",
)

cfg = sys.do_solve()
pprint.pprint(cfg["clock"])
```

The `user.vco_min` objective sits at tier 0, ahead of every built-in
(which start at tier 1). Compare the resulting `vco` field against
Step 1 — it should be lower or equal.

## Step 5: Disable a default objective

Sometimes a built-in objective conflicts with what you actually want.
`disable_objective(name)` on any component suppresses one of its
defaults by name; the names are stable identifiers from `list_objectives()`.

Disable HMC7044's R2 minimization and re-solve:

```{exec_code}
:caption_output: Solve without r2 minimization

# --- hide: start ---
import adijif
vcxo = 125_000_000
sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver="CPLEX")
sys.fpga.setup_by_dev_kit_name("zc706")
sys.converter.sample_clock = 1e9 / 2
sys.converter.datapath_decimation = 1
sys.converter.L = 4
sys.converter.M = 2
sys.converter.N = 14
sys.converter.Np = 16
sys.converter.K = 32
sys.converter.F = 1
sys.converter.HD = 1
# --- hide: stop ---
sys.clock.disable_objective("hmc7044.r2_min")
cfg = sys.solve()
print(f"r2 = {cfg['clock']['r2']}")
```

The solver is now free to pick any valid R2.

## Step 6: Combine constraints with multi-tier objectives

The two tools compose. A realistic flow constrains the clocks you care
about, then layers ordered preferences on top so the solver picks the
best feasible configuration:

```{exec_code}
:caption_output: Constraints plus multi-tier objectives

import adijif
import pprint

vcxo = 125_000_000
sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver="CPLEX")
sys.fpga.setup_by_dev_kit_name("zc706")
sys.converter.sample_clock = 1e9 / 2
sys.converter.datapath_decimation = 1
sys.converter.L = 4
sys.converter.M = 2
sys.converter.N = 14
sys.converter.Np = 16
sys.converter.K = 32
sys.converter.F = 1
sys.converter.HD = 1

clocks = sys.initialize()

# Hard constraints: narrow what's *valid*.
clocks.constrain("AD9680_fpga_ref_clk", range=(100e6, 200e6))
clocks.constrain("AD9680_sysref", equal_to=15_625_000)

# Soft preferences: rank what's *desirable* among valid solutions.
sys.add_objective(
    sys.clock.config["vcxod"] * sys.clock.config["n2"] / sys.clock.config["r2"],
    sense="min",
    tier=0,
    name="user.vco_min",
)
sys.add_objective(
    sys.clock.config["vcxo_doubler"],
    sense="max",
    tier=1,
    name="user.prefer_doubled_vcxo",
)

cfg = sys.do_solve()
print(f"vco = {cfg['clock']['vco']:.0f}")
print(f"vcxo_doubler = {cfg['clock']['vcxo_doubler']}")
pprint.pprint(cfg["clock"]["output_clocks"])
```

If the VCO minimum is achievable with both `vcxo_doubler=1` and
`vcxo_doubler=2`, tier 1 breaks the tie in favor of the doubled input.
If only one doubler value reaches the VCO optimum, tier 0 wins
unconditionally — and the constrained clock rates always hold.

You can also express the same flow with a callback to `sys.solve()`:

```python
def constrain(clocks):
    clocks.constrain("AD9680_fpga_ref_clk", range=(100e6, 200e6))
    clocks.constrain("AD9680_sysref", equal_to=15_625_000)

cfg = sys.solve(constrain=constrain)
```

## What's next

- The {py:class}`adijif.optimization.Objective` dataclass is the type
  returned by `list_objectives()`; its fields (`expr`, `sense`, `tier`,
  `weight`, `name`, `component`) are documented in the source.
- For nested converters (MxFE / transceivers) the converter name in
  `ClocksBundle` keys is replaced by the nested channel name (e.g.
  `adc_sysref`, `dac_fpga_ref_clk`). Print `clocks.keys()` after
  `initialize()` to see the exact names available for your configuration.
- The gekko solver backend supports a single objective tier only; passing
  multi-tier objectives on `solver="gekko"` raises `NotImplementedError`.
  Use `solver="CPLEX"` whenever you need lexicographic priorities or the
  `choices=[...]` constraint helper.
