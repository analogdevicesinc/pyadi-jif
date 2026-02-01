# OR-Tools Examples

This directory contains examples demonstrating the [Google OR-Tools](https://developers.google.com/optimization) constraint programming solver integration with the pyadi-jif framework.

## What is OR-Tools?

[OR-Tools](https://developers.google.com/optimization) (Operations Research Tools) is Google's open-source optimization library. It provides powerful constraint programming (CP) and linear programming (LP) capabilities for solving complex optimization problems.

**Key characteristics:**
- **Free and open-source** - No licensing costs
- **Constraint programming focused** - Excellent for combinatorial problems
- **Fast** - Highly optimized solver engine
- **Multi-language** - Available for Python, C++, Java, .NET
- **No external dependencies** - Self-contained solver (unlike some alternatives)

## Installation

To use the OR-Tools examples, install pyadi-jif with OR-Tools support:

```bash
pip install 'pyadi-jif[ortools]'
```

This installs:
- `ortools>=9.7.0` - The constraint programming solver
- All pyadi-jif dependencies and the pysym framework

Verify installation:
```bash
python -c "from ortools.sat.python import cp_model; print('OR-Tools installed successfully')"
```

## Example Index

### Foundation Examples (Start Here)

#### 1. [`hmc7044_ortools.py`](hmc7044_ortools.py)
**Basic clock chip configuration with OR-Tools**

A simplified example showing how to use the pysym Model API to configure a clock generator's output dividers.

**Topics covered:**
- Creating a pysym Model with OR-Tools solver
- Defining integer decision variables with domains
- Adding constraints to achieve target frequencies
- Solving and extracting results

**Complexity:** ⭐ Beginner
**Time to run:** < 1 second

**Run it:**
```bash
python examples/hmc7044_ortools.py
```

**Compare with CPLEX version:**
```bash
python examples/hmc7044_example.py
```

---

#### 2. [`adf4371_ortools.py`](adf4371_ortools.py)
**External PLL (Phase Locked Loop) configuration**

Demonstrates configuring an external PLL synthesizer to achieve a target RF frequency using fractional-N PLL constraints.

**Topics covered:**
- Handling fractional-N PLL mathematics
- Optimizing for component parameters (INT, FRAC dividers)
- Calculating achieved frequencies from divider values
- Handling more complex component types

**Complexity:** ⭐⭐ Intermediate
**Time to run:** < 1 second

**Run it:**
```bash
python examples/adf4371_ortools.py
```

**Compare with CPLEX version:**
```bash
python examples/adf4371_umts_example.py
```

---

### System-Level Examples

#### 3. [`simple_system_ortools.py`](simple_system_ortools.py)
**Composing a simple system with multiple components**

Shows how to build a complete system by composing constraints from different component types (converter + clock generator).

**Topics covered:**
- Defining system-level constraints
- Relationships between components
- Multi-component optimization
- Migration path from legacy system class to pysym

**Complexity:** ⭐⭐ Intermediate
**Time to run:** < 1 second

**Run it:**
```bash
python examples/simple_system_ortools.py
```

---

### Advanced Examples

#### 4. [`clock_optimization_ortools.py`](clock_optimization_ortools.py)
**Multi-clock optimization - What OR-Tools excels at**

A more complex example showing OR-Tools' strength in combinatorial optimization: configuring a single clock generator to produce multiple outputs, each with different frequency requirements and tolerances.

**Topics covered:**
- Multiple objectives and constraints
- Non-linear relationships (division)
- Tolerance-based constraints
- Optimization across many variables simultaneously
- OR-Tools' advantages for this problem class

**Complexity:** ⭐⭐⭐ Advanced
**Time to run:** < 1 second

**Run it:**
```bash
python examples/clock_optimization_ortools.py
```

---

## When to Use OR-Tools vs. Other Solvers

### Use OR-Tools if you need:

✓ **Free, open-source constraint programming**
  - No licensing costs
  - Can be embedded in products without restrictions

✓ **Combinatorial optimization**
  - Configuration space exploration (divider settings, mode selection)
  - Integer programming problems
  - Discrete variable domains

✓ **Speed for moderate problem sizes**
  - 10-1000s of variables
  - 100-10000s of constraints
  - Industry-standard response times

✓ **Native Python integration**
  - Pure Python OR-Tools library
  - Easy to integrate into automation scripts

✓ **Educational/Learning purposes**
  - Understanding constraint programming
  - Prototyping optimization approaches

### Use CPLEX if you need:

✓ **Guaranteed optimal solutions**
  - Integer linear programming with certified optimality
  - Deterministic results (same input = same output)

✓ **Large-scale problems**
  - 10,000+ variables
  - 100,000+ constraints
  - Commercial-grade performance

✓ **Mixed-integer quadratic programming**
  - Quadratic objectives and constraints

✓ **Enterprise support**
  - Commercial support contract
  - Optimization consulting

### Use GEKKO if you need:

✓ **Nonlinear programming**
  - Nonlinear objectives and constraints
  - Continuous optimization
  - Smooth function optimization

✓ **Machine learning integration**
  - Parameter tuning for neural networks
  - Combined with ML workflows

✓ **Educational nonlinear optimization**

## Solver Comparison Table

| Feature | OR-Tools | CPLEX | GEKKO |
|---------|----------|-------|-------|
| **Cost** | Free | Licensed ($$) | Free |
| **Type** | Constraint Programming | Mixed Integer LP | Nonlinear |
| **Speed** | Fast (moderate) | Very Fast | Moderate |
| **Optimality Guarantee** | Heuristic | Proven Optimal | Local Optimal |
| **Supported by pyadi-jif** | ✓ | ✓ | ✓ |
| **Best for Clock Config** | Good | Best | Limited |
| **Learning Curve** | Gentle | Moderate | Steep |

## Key OR-Tools Limitations (in pyadi-jif context)

The OR-Tools integration in pyadi-jif uses Google's CP-SAT (Satisfiability) solver. Some constraints that work in CPLEX may need adjustment for OR-Tools:

1. **Division constraints** - Non-linear division uses `AddDivisionEquality` (basic but functional)
2. **Conditional constraints** - Simplified approach (works for common patterns)
3. **Lexicographic multi-objective** - Sequential optimization (not native)
4. **Continuous variables** - SAT solver prefers integers (limited support)

**These limitations typically don't affect clock configuration problems**, which are naturally integer-based.

## pysym Framework

These examples use the [pysym](../adijif/pysym) framework, which provides:

- **Solver-agnostic API** - Same code works with CPLEX, GEKKO, or OR-Tools
- **Component-level abstraction** - Build complex systems from simpler pieces
- **Clear constraint definition** - Explicit variable and constraint creation
- **Three-solver validation** - Test problems across all solvers

The pysym framework is ideal for:
- Learning constraint programming
- Prototyping new optimization problems
- Educational code clarity
- Rapid solver switching and comparison

For production systems, you might use the higher-level `adijif` APIs (e.g., `adijif.hmc7044()`, `adijif.system()`), which handle complexity automatically.

## Running Multiple Examples

Run all OR-Tools examples:
```bash
for example in hmc7044_ortools.py adf4371_ortools.py simple_system_ortools.py clock_optimization_ortools.py; do
    echo "=== Running $example ==="
    python examples/$example
    echo ""
done
```

Run with timing to compare solver performance:
```bash
time python examples/hmc7044_ortools.py
time python examples/hmc7044_example.py  # CPLEX version
```

## Testing

Examples are tested automatically. To run OR-Tools example tests:

```bash
# Run all OR-Tools example tests
nox -rs tests -- tests/test_ortools_examples.py

# Run with verbose output
nox -rs tests -- -v tests/test_ortools_examples.py

# Skip OR-Tools tests if not installed
nox -rs tests -- --ignore=tests/test_ortools_examples.py
```

Tests verify:
- Examples run without errors
- Solutions are feasible
- Output is properly formatted

## Troubleshooting

### ImportError: "OR-Tools solver not installed"

**Solution:** Install OR-Tools
```bash
pip install 'pyadi-jif[ortools]'
```

### Solver returns infeasible solution

**Possible causes:**
1. Target frequencies are mathematically impossible (e.g., 10 GHz from 125 MHz reference)
2. Tolerance requirements are too tight
3. Divider ranges are too restrictive

**Debug steps:**
1. Check math: Are your target frequencies achievable?
2. Loosen tolerances temporarily to verify feasibility
3. Expand divider ranges to confirm they're not the bottleneck

### Example runs but output seems wrong

Check that your constraints are correct. Common issues:
1. Division by zero (domain should start at 1, not 0)
2. Expected divider calculations (verify math separately)
3. Tolerance percentage calculation (easy to get ±/× confused)

## Further Reading

- [Google OR-Tools Documentation](https://developers.google.com/optimization/install)
- [CP-SAT Solver Overview](https://developers.google.com/optimization/cp/cp_solver)
- [pyadi-jif pysym Framework](../adijif/pysym)
- [pyadi-jif Main Documentation](../doc/source)

## Related Examples

- CPLEX examples: [`examples/hmc7044_example.py`](hmc7044_example.py), [`examples/adf4371_umts_example.py`](adf4371_umts_example.py)
- GEKKO examples: See CLAUDE.md for solver configuration
- System configuration: [`examples/ad9081_rx_hmc7044_ext_pll_adf4371.py`](ad9081_rx_hmc7044_ext_pll_adf4371.py)

## Questions or Issues?

- Check [pyadi-jif GitHub Issues](https://github.com/analogdevicesinc/pyadi-jif/issues)
- Review the solver comparison table above
- Refer to the example code comments for detailed explanations
