"""HMC7044 clock chip configuration using OR-Tools solver.

This example demonstrates HMC7044 clock chip configuration using the
OR-Tools constraint programming solver through the pysym framework.

The HMC7044 is a versatile clock generator that can produce multiple
output clocks with different frequencies from a single reference input.

This example shows:
  - Using the pysym Model API with OR-Tools solver
  - Defining output clock requirements (multiple target frequencies)
  - Solving for valid divider values

Compare with examples/hmc7044_example.py which uses CPLEX.

NOTE: This example requires OR-Tools. Install with:
    pip install 'pyadi-jif[ortools]'
"""

from adijif.pysym.model import Model
from adijif.pysym.variables import IntegerVar
import pprint

# ============================================================================
# HMC7044 Configuration
# ============================================================================

# Reference input frequency
VCXO_FREQ = 125_000_000  # 125 MHz reference

# Desired output clock frequencies
# Output 0: 1000 MHz (ADC clock)
# Output 1: 500 MHz (FPGA clock)
# Output 2: 7.8125 MHz (SYSREF)
OUTPUT_TARGETS = [1_000_000_000, 500_000_000, 7_812_500]
OUTPUT_NAMES = ["ADC", "FPGA", "SYSREF"]

# ============================================================================
# Problem Setup with OR-Tools
# ============================================================================

# Create optimization model using OR-Tools
model = Model(solver="ortools")

# N2 divider: divides the reference input by N2 to produce the VCO input
# HMC7044 specification: N2 should be in range [1, 254]
n2 = IntegerVar(domain=range(1, 255), name="N2")
model.add_variable(n2)

# Output dividers: each output has a divider that reduces VCO to desired frequency
# HMC7044 specification: output dividers should be in range [1, 4095]
output_dividers = []
for i in range(3):
    div = IntegerVar(domain=range(1, 4096), name=f"OUT{i}_DIV")
    output_dividers.append(div)
    model.add_variable(div)

# VCO frequency (determined by N2 and other PLL parameters)
# For this simplified example, VCO is assumed to be related to reference clock
# Typical VCO range: 400 MHz to 1600 MHz
# VCO = (VCXO / N2) * M where M is a feedback multiplier
# For simplicity, we use a specific VCO frequency
vco_freq = 1000_000_000  # 1000 MHz

# ============================================================================
# Constraints
# ============================================================================

# The output frequency is VCO divided by the output divider:
# output_freq = vco_freq / output_divider

# Add constraints to achieve target frequencies (allow ±1% tolerance)
for i, (target, divider, name) in enumerate(
    zip(OUTPUT_TARGETS, output_dividers, OUTPUT_NAMES)
):
    # output = vco / divider
    # divider = vco / output
    expected_divider = vco_freq // target
    tolerance = max(1, expected_divider // 100)  # 1% tolerance

    # Constrain divider to be close to expected value
    model.add_constraint(divider >= expected_divider - tolerance)
    model.add_constraint(divider <= expected_divider + tolerance)

# ============================================================================
# Objective
# ============================================================================

# Minimize N2 to reduce power consumption (lower divider ratio = lower power)
model.add_objective(n2, minimize=True)

# ============================================================================
# Solve
# ============================================================================

print("=" * 70)
print("HMC7044 Clock Configuration with OR-Tools")
print("=" * 70)
print(f"\nReference Input (VCXO): {VCXO_FREQ / 1e6:.1f} MHz")
print(f"Target VCO Frequency:   {vco_freq / 1e6:.1f} MHz")
print(f"\nDesired Output Clocks:")
for name, freq in zip(OUTPUT_NAMES, OUTPUT_TARGETS):
    print(f"  {name:6s}: {freq / 1e6:10.2f} MHz")

print("\n" + "=" * 70)
print("Solving...")
print("=" * 70)

solution = model.solve()

if solution.is_feasible:
    print("\n✓ Feasible solution found with OR-Tools!")
    print("\nConfiguration:")
    print(f"  N2 Divider: {solution.get_value(n2)}")

    print("\n  Output Clocks:")
    for i, (name, divider, target) in enumerate(
        zip(OUTPUT_NAMES, output_dividers, OUTPUT_TARGETS)
    ):
        div_value = solution.get_value(divider)
        actual_freq = vco_freq / div_value
        error_pct = abs(actual_freq - target) / target * 100
        print(f"    {name:6s}: Divider={div_value:5d}, Freq={actual_freq / 1e6:10.2f} MHz "
              f"(Target: {target / 1e6:10.2f} MHz, Error: {error_pct:.2f}%)")

    # Summary
    print("\n" + "=" * 70)
    print("Configuration Summary")
    print("=" * 70)
    config = {
        "N2": solution.get_value(n2),
        "VCO_FREQ": f"{vco_freq / 1e6:.1f} MHz",
        "OUTPUTS": {},
    }
    for name, divider, target in zip(OUTPUT_NAMES, output_dividers, OUTPUT_TARGETS):
        div_value = solution.get_value(divider)
        actual_freq = vco_freq / div_value
        config["OUTPUTS"][name] = {
            "DIVIDER": div_value,
            "TARGET_FREQ": f"{target / 1e6:.2f} MHz",
            "ACTUAL_FREQ": f"{actual_freq / 1e6:.2f} MHz",
        }

    pprint.pprint(config)

else:
    print("\n✗ No feasible solution found")
    print(f"Solver status: {solution.status}")
