# Optimization Tutorial

In this tutorial you will steer the JIF solver toward the configuration *you*
want by attaching optimization objectives to a system. By the end you will
have a working AD9680 + HMC7044 system that minimizes a custom expression
in addition to the framework's built-in defaults, you will have inspected
which objectives are active, and you will have disabled one of them to
observe the effect.

A JIF system is a constraint-satisfaction problem with many valid solutions.
Optimization objectives let you pick the *best* one along criteria you care
about — lower divider counts for jitter, smaller VCO frequencies for power,
preferred PLL types, and so on.

## Prerequisites

- pyadi-jif installed with the CPLEX extra (`pip install 'pyadi-jif[cplex]'`).
  Multi-tier (lexicographic) optimization requires the CPLEX backend.
- Familiarity with [Usage Flows](flow.md) — you should know how to build a
  `system` and call `sys.solve()`.

## Step 1: Solve with default objectives

Every component class registers built-in objectives when its constraints
are set up — for example, the HMC7044 model registers a "minimize R2 input
divider" objective so the solver naturally biases toward simpler clock
trees.

Build a baseline system and solve it without touching the optimization API:

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

Note the `r2` divider value in the output. The solver chose this because
HMC7044's default `hmc7044.r2_min` objective biased it toward a small R2.

## Step 2: Inspect which objectives are active

Call `sys.list_objectives()` after `solve()` (or after `initialize()`) to
get a flat list of every `Objective` the framework will apply. Each entry
carries its tier, sense (`min` or `max`), name, and the component that
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

## Step 3: Add a custom user objective

Use `sys.add_objective(expr, sense=, tier=, name=)` to register your own
optimization criterion. The expression must reference solver variables
that already exist on a component (look in `sys.clock.config`,
`sys.fpga.config`, etc., after the model is built).

Suppose you want to favor configurations where the HMC7044's VCO output
runs as close as possible to its lower bound (2.4 GHz on this part) — for
example to keep PLL bandwidth low. Add a max-priority user objective that
minimizes the VCO expression:

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

# initialize() builds the solver model so we can reference its variables.
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

The `user.vco_min` objective sits at tier 0, which puts it ahead of every
built-in objective (which start at tier 1). Compare the resulting `vco`
field against Step 1 — it should be lower or equal.

## Step 4: Disable a default objective

Sometimes a built-in objective conflicts with what you actually want.
`disable_objective(name)` on any component suppresses one of its
defaults by name. The names are stable identifiers — see them via
`list_objectives()` (Step 2).

Disable HMC7044's R2 minimization and re-solve:

```{exec_code}
:caption_output: Solve without r2 minimization

# --- hide: start ---
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
# --- hide: stop ---
sys.clock.disable_objective("hmc7044.r2_min")
cfg = sys.solve()
print(f"r2 = {cfg['clock']['r2']}")
```

The solver is now free to pick any valid R2 — the value will likely differ
from Step 1.

## Step 5: Layer multiple priorities

Lexicographic optimization shines when you have several criteria you'd
rank in order. The solver fully optimizes tier 0, then uses tier 1 as a
tie-breaker when tier 0 has multiple optima, and so on.

Stack two user objectives at different tiers:

```{exec_code}
:caption_output: Multi-tier user objectives

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
sys.initialize()

# Highest priority: minimize VCO frequency.
sys.add_objective(
    sys.clock.config["vcxod"] * sys.clock.config["n2"] / sys.clock.config["r2"],
    sense="min",
    tier=0,
    name="user.vco_min",
)
# Tie-breaker: prefer the largest possible VCXO doubler input.
sys.add_objective(
    sys.clock.config["vcxo_doubler"],
    sense="max",
    tier=1,
    name="user.prefer_doubled_vcxo",
)

cfg = sys.do_solve()
print(f"vco = {cfg['clock']['vco']:.0f}")
print(f"vcxo_doubler = {cfg['clock']['vcxo_doubler']}")
```

If the VCO minimum is achievable with both `vcxo_doubler=1` and
`vcxo_doubler=2`, the second tier breaks the tie in favor of the doubled
input. If only one doubler value reaches the VCO optimum, tier 0 wins
unconditionally.

## What's next

- The {py:class}`adijif.optimization.Objective` dataclass is the type
  returned by `list_objectives()`; its fields (`expr`, `sense`, `tier`,
  `weight`, `name`, `component`) are documented in the source.
- See [Usage Flows](flow.md) for the broader system-construction pattern.
- The gekko solver backend supports a single objective tier only; passing
  multi-tier objectives on `solver="gekko"` raises `NotImplementedError`.
  Use `solver="CPLEX"` whenever you need lexicographic priorities.
