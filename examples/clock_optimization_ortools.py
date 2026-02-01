"""Multi-clock optimization using OR-Tools solver.

This example demonstrates how OR-Tools excels at combinatorial optimization
problems with multiple clocks and different requirements.

The problem: Configure a clock generator to produce multiple output clocks
with different frequencies and characteristics, each with specific constraints.

This showcases OR-Tools' strengths:
  - Efficient exploration of combinatorial solution spaces
  - Non-linear constraints (e.g., division relationships)
  - Multiple objectives and constraints simultaneously
  - Fast solutions for configuration optimization

Scenario:
  - Clock generator with configurable PLL and multiple outputs
  - Different outputs serve different purposes (ADC clock, FPGA clock, SYSREF, etc.)
  - Each output has frequency targets and tolerance requirements
  - Optimize for minimum power while satisfying all constraints

NOTE: This example requires OR-Tools. Install with:
    pip install 'pyadi-jif[ortools]'
"""

from adijif.pysym.model import Model
from adijif.pysym.variables import IntegerVar
import pprint

# ============================================================================
# Multi-Clock System Definition
# ============================================================================

# Reference input
REFERENCE_FREQ = 125_000_000  # 125 MHz

# Clock outputs with requirements
CLOCKS = {
    "ADC_CLK": {
        "target": 1_000_000_000,  # 1 GHz
        "tolerance_pct": 0.1,  # 0.1% tolerance
        "description": "ADC sampling clock",
    },
    "FPGA_CLK": {
        "target": 250_000_000,  # 250 MHz
        "tolerance_pct": 1.0,  # 1% tolerance (less critical)
        "description": "FPGA logic clock",
    },
    "SYSREF": {
        "target": 7_812_500,  # 7.8125 MHz
        "tolerance_pct": 0.1,  # 0.1% tolerance
        "description": "JESD204 SYSREF (reference sync signal)",
    },
    "REF_OUT": {
        "target": 125_000_000,  # 125 MHz (buffered reference)
        "tolerance_pct": 0.01,  # 0.01% tolerance (reference quality)
        "description": "Buffered reference output",
    },
}

# ============================================================================
# Optimization Model
# ============================================================================

model = Model(solver="ortools")

print("=" * 80)
print("Multi-Clock System Optimization with OR-Tools")
print("=" * 80)
print(f"\nReference Input: {REFERENCE_FREQ / 1e6:.1f} MHz")
print(f"\nClock Requirements:")
print("-" * 80)
for clock_name, spec in CLOCKS.items():
    print(f"  {clock_name:12s}: {spec['target'] / 1e6:10.2f} MHz  "
          f"(±{spec['tolerance_pct']:.2f}%)  - {spec['description']}")

# ============================================================================
# Clock Generator Architecture (Simplified)
# ============================================================================
#
# Typical clock generator structure:
#   1. VCO (Voltage Controlled Oscillator) - produces high frequency signal
#   2. Output dividers - each output has a divider to reduce VCO to target
#   3. Optional additional stages (phase shifters, distribution, etc.)
#
# We model the core components:
#   - VCO divider (divides reference to produce VCO input)
#   - VCO multiplication factor
#   - Output dividers
#
# For this example, we use a simplified model:
#   VCO_FREQ = REFERENCE * M / N
#   OUTPUT_i = VCO_FREQ / DIV_i

print("\n" + "=" * 80)
print("Decision Variables (Configuration Parameters)")
print("=" * 80)

# Main VCO frequency (we'll model it as determined by divider ratios)
# For HMC7044-like device: VCO typically ranges 400-1600 MHz
# Let's set a fixed VCO for this example (in reality, it's determined by a multiplier)
vco_freq = 1_000_000_000  # 1 GHz VCO

# N2 divider (reduces reference to PLL input)
n2_divider = IntegerVar(domain=range(1, 256), name="N2_divider")
model.add_variable(n2_divider)

# Output dividers for each clock
output_dividers = {}
for clock_name in CLOCKS.keys():
    div = IntegerVar(
        domain=range(1, 4096),
        name=f"{clock_name}_divider",
    )
    output_dividers[clock_name] = div
    model.add_variable(div)

print(f"\n  N2 (Reference Divider): range [1, 255]")
print(f"  VCO Frequency: {vco_freq / 1e9:.1f} GHz (fixed)")
for clock_name in CLOCKS.keys():
    print(f"  {clock_name}_divider: range [1, 4095]")

# ============================================================================
# Constraints
# ============================================================================

print("\n" + "=" * 80)
print("Adding Constraints")
print("=" * 80)

constraint_count = 0

for clock_name, spec in CLOCKS.items():
    target_freq = spec["target"]
    tolerance_pct = spec["tolerance_pct"]

    # Calculate expected divider
    expected_divider = vco_freq / target_freq

    # Calculate tolerance as absolute divider value
    tolerance = max(1, int(expected_divider * tolerance_pct / 100))

    # Add constraints for this output
    div = output_dividers[clock_name]

    # Constraint: divider must produce output within tolerance of target
    # output = vco / divider
    # target * (1 - tol/100) <= vco / divider <= target * (1 + tol/100)
    # vco / (target * (1 + tol/100)) <= divider <= vco / (target * (1 - tol/100))

    min_div = int(expected_divider - tolerance)
    max_div = int(expected_divider + tolerance)

    model.add_constraint(div >= max(1, min_div))
    model.add_constraint(div <= max_div)
    constraint_count += 2

    print(f"\n  {clock_name}:")
    print(f"    Target: {target_freq / 1e6:.2f} MHz, Tolerance: ±{tolerance_pct:.2f}%")
    print(f"    Expected divider: {expected_divider:.2f}")
    print(f"    Constraint range: [{max(1, min_div)}, {max_div}]")

# ============================================================================
# Multi-Objective Optimization
# ============================================================================
#
# Primary objective: Minimize total divider ratio (affects power)
# Secondary consideration: Minimize variation in dividers (aids manufacturability)

print("\n" + "=" * 80)
print("Optimization Objective")
print("=" * 80)

# Sum of all output dividers
total_output_dividers = sum(output_dividers.values())

# Objective: minimize total divider ratio
# This typically correlates with lower power consumption in PLL circuits
model.add_objective(total_output_dividers, minimize=True)

print(f"\nObjective: Minimize total output divider ratio")
print(f"  (Minimizes power consumption and improves phase noise)")

# ============================================================================
# Solve
# ============================================================================

print("\n" + "=" * 80)
print("Solving with OR-Tools...")
print("=" * 80)

solution = model.solve()

if solution.is_feasible:
    print("\n✓ Feasible solution found!")

    n2_val = solution.get_value(n2_divider)

    print("\n" + "=" * 80)
    print("Clock Generator Configuration")
    print("=" * 80)

    print(f"\nMain Configuration:")
    print(f"  Reference Input:  {REFERENCE_FREQ / 1e6:.1f} MHz")
    print(f"  N2 Divider:       {n2_val}")
    print(f"  PLL Input Freq:   {REFERENCE_FREQ / n2_val / 1e6:.2f} MHz")
    print(f"  VCO Frequency:    {vco_freq / 1e9:.1f} GHz")

    print(f"\nOutput Clocks:")
    print("-" * 80)
    print(f"{'Clock Name':<12} {'Divider':>8} {'Actual (MHz)':>15} {'Target (MHz)':>15} {'Error (%)':>12}")
    print("-" * 80)

    config = {
        "REFERENCE": f"{REFERENCE_FREQ / 1e6:.1f} MHz",
        "N2_DIVIDER": n2_val,
        "VCO": f"{vco_freq / 1e9:.1f} GHz",
        "OUTPUTS": {},
    }

    total_divider_sum = 0
    all_in_spec = True

    for clock_name, spec in CLOCKS.items():
        div_val = solution.get_value(output_dividers[clock_name])
        actual_freq = vco_freq / div_val
        target_freq = spec["target"]
        tolerance_pct = spec["tolerance_pct"]

        error_pct = abs(actual_freq - target_freq) / target_freq * 100
        in_spec = error_pct <= tolerance_pct

        if not in_spec:
            all_in_spec = False

        print(
            f"{clock_name:<12} {div_val:>8d} {actual_freq / 1e6:>15.2f} "
            f"{target_freq / 1e6:>15.2f} {error_pct:>12.4f} {'✓' if in_spec else '✗'}"
        )

        total_divider_sum += div_val
        config["OUTPUTS"][clock_name] = {
            "DIVIDER": div_val,
            "TARGET": f"{target_freq / 1e6:.2f} MHz",
            "ACTUAL": f"{actual_freq / 1e6:.2f} MHz",
            "ERROR_PCT": f"{error_pct:.4f}%",
            "IN_SPEC": in_spec,
        }

    print("-" * 80)
    print(f"{'Total Divider Ratio':<32} {total_divider_sum:>8d}")

    print("\n" + "=" * 80)
    print("Validation Summary")
    print("=" * 80)
    if all_in_spec:
        print("✓ All outputs within specification!")
    else:
        print("⚠ Some outputs exceeded tolerance")

    print(f"  Total divider ratio (power figure): {total_divider_sum}")
    print(f"  Number of outputs configured: {len(CLOCKS)}")

    print("\n" + "=" * 80)
    print("Detailed Configuration")
    print("=" * 80)
    pprint.pprint(config)

else:
    print("\n✗ No feasible solution found")
    print(f"Solver: {solution.solver_name}")
    print("\nPossible causes:")
    print("  - Frequency targets are incompatible with available dividers")
    print("  - Tolerance requirements are too tight")
    print("  - VCO frequency is outside optimal range for these outputs")
