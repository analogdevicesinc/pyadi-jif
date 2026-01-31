"""Performance benchmarking across CPLEX, GEKKO, and OR-Tools solvers.

This module measures solve times for different problem categories to help
users choose the best solver for their use cases.
"""

import time
import pytest

from adijif.pysym import Model, IntegerVar, BinaryVar
from adijif.solvers import cplex_solver, gekko_solver, ortools_solver


@pytest.mark.skipif(
    not (cplex_solver and gekko_solver and ortools_solver),
    reason="All three solvers required"
)
class TestPerformanceBenchmarks:
    """Performance benchmarking across three solver backends."""

    def test_small_problem_performance(self):
        """Benchmark small optimization problem (5-20 variables).

        Small problems typical of embedded system constraints.
        """
        results = {}

        for solver_name in ["CPLEX", "gekko", "ortools"]:
            model = Model(solver=solver_name)

            # Create variables
            vars_list = [
                IntegerVar(domain=range(1, 50), name=f"x{i}") for i in range(10)
            ]

            for var in vars_list:
                model.add_variable(var)

            # Add constraints
            for i in range(5):
                model.add_constraint(
                    vars_list[i] + vars_list[i + 1] >= 10
                )

            # Objective
            total = sum(vars_list[:5])
            model.add_objective(total, minimize=True)

            # Measure solve time
            start = time.time()
            solution = model.solve()
            elapsed = time.time() - start

            results[solver_name] = {
                "time": elapsed,
                "feasible": solution.is_feasible,
            }

        # All solvers should find feasible solution
        assert all(r["feasible"] for r in results.values())

        # Print results
        print("\n=== SMALL PROBLEM (10 variables, 5 constraints) ===")
        for solver_name, result in results.items():
            print(f"{solver_name:10s}: {result['time']*1000:7.2f} ms")

    def test_medium_problem_performance(self):
        """Benchmark medium optimization problem (50-100 variables).

        Medium problems typical of PLL/clock configuration.
        """
        results = {}

        for solver_name in ["CPLEX", "gekko", "ortools"]:
            model = Model(solver=solver_name)

            # Create variables
            vars_list = [
                IntegerVar(domain=range(1, 100), name=f"x{i}") for i in range(50)
            ]

            for var in vars_list:
                model.add_variable(var)

            # Add constraints
            for i in range(0, 40, 4):
                model.add_constraint(
                    vars_list[i]
                    + vars_list[i + 1]
                    + vars_list[i + 2]
                    >= 100
                )

            # Objective
            total = sum(vars_list)
            model.add_objective(total, minimize=True)

            # Measure solve time
            start = time.time()
            solution = model.solve()
            elapsed = time.time() - start

            results[solver_name] = {
                "time": elapsed,
                "feasible": solution.is_feasible,
            }

        # All solvers should find feasible solution
        assert all(r["feasible"] for r in results.values())

        # Print results
        print("\n=== MEDIUM PROBLEM (50 variables, 10 constraints) ===")
        for solver_name, result in results.items():
            print(f"{solver_name:10s}: {result['time']*1000:7.2f} ms")

    def test_pll_problem_performance(self):
        """Benchmark PLL configuration problem (realistic scenario).

        Simulates actual PLL frequency synthesis configuration.
        """
        results = {}

        for solver_name in ["CPLEX", "gekko", "ortools"]:
            model = Model(solver=solver_name)

            # PLL configuration variables
            n_div = IntegerVar(domain=range(8, 256), name="n_div")
            r_div = IntegerVar(domain=[1, 2, 4, 8], name="r_div")
            m_div = IntegerVar(domain=range(1, 129), name="m_div")

            model.add_variable(n_div)
            model.add_variable(r_div)
            model.add_variable(m_div)

            # VCO constraints: 800 MHz <= VCO <= 1600 MHz
            # VCO = ref_clk * N = 100e6 * N
            # 800e6 <= 100e6 * N <= 1600e6 => 8 <= N <= 16
            # But use full range for testing
            model.add_constraint(n_div >= 8)
            model.add_constraint(n_div <= 256)

            # Output constraints
            model.add_constraint(m_div >= 1)
            model.add_constraint(m_div <= 128)

            # Objective: minimize power (prefer lower N and M)
            model.add_objective(n_div + m_div, minimize=True)

            # Measure solve time
            start = time.time()
            solution = model.solve()
            elapsed = time.time() - start

            results[solver_name] = {
                "time": elapsed,
                "feasible": solution.is_feasible,
                "n": solution.get_value(n_div) if solution.is_feasible else None,
            }

        # Print results
        print("\n=== PLL CONFIGURATION (3 variables, 2 constraints) ===")
        for solver_name, result in results.items():
            print(
                f"{solver_name:10s}: {result['time']*1000:7.2f} ms "
                f"(N={result['n']})"
            )

    def test_clock_divider_problem_performance(self):
        """Benchmark clock divider problem (multiple outputs).

        Simulates clock chip configuration with multiple dividers.
        """
        results = {}

        for solver_name in ["CPLEX", "gekko", "ortools"]:
            model = Model(solver=solver_name)

            # Create 16 clock dividers
            dividers = [
                IntegerVar(domain=range(1, 33), name=f"div{i}") for i in range(16)
            ]

            for div in dividers:
                model.add_variable(div)

            # Constraints: clock relationships
            # All dividers >= 1
            for div in dividers:
                model.add_constraint(div >= 1)

            # Some dividers paired (e.g., diff/data clocks)
            model.add_constraint(dividers[0] == dividers[1])
            model.add_constraint(dividers[2] * 2 == dividers[3])

            # Objective: minimize total divider sum
            total = sum(dividers)
            model.add_objective(total, minimize=True)

            # Measure solve time
            start = time.time()
            solution = model.solve()
            elapsed = time.time() - start

            results[solver_name] = {
                "time": elapsed,
                "feasible": solution.is_feasible,
            }

        # Print results
        print("\n=== CLOCK DIVIDERS (16 variables, 3 constraints) ===")
        for solver_name, result in results.items():
            print(f"{solver_name:10s}: {result['time']*1000:7.2f} ms")

    def test_mixed_integer_binary_performance(self):
        """Benchmark mixed integer-binary problem.

        Simulates feature selection with resource constraints.
        """
        results = {}

        for solver_name in ["CPLEX", "gekko", "ortools"]:
            model = Model(solver=solver_name)

            # 20 binary features
            features = [BinaryVar(name=f"feature{i}") for i in range(20)]

            # 20 integer resource allocation
            resources = [
                IntegerVar(domain=range(0, 51), name=f"resource{i}")
                for i in range(20)
            ]

            for f in features:
                model.add_variable(f)
            for r in resources:
                model.add_variable(r)

            # Resource constraints: if feature enabled, allocate resources
            for i in range(20):
                model.add_constraint(resources[i] >= 10 * features[i])

            # Total resource limit
            total_resources = sum(resources)
            model.add_constraint(total_resources <= 300)

            # Objective: minimize total resources
            model.add_objective(total_resources, minimize=True)

            # Measure solve time
            start = time.time()
            solution = model.solve()
            elapsed = time.time() - start

            results[solver_name] = {
                "time": elapsed,
                "feasible": solution.is_feasible,
            }

        # Print results
        print("\n=== MIXED INTEGER-BINARY (40 variables, 22 constraints) ===")
        for solver_name, result in results.items():
            print(f"{solver_name:10s}: {result['time']*1000:7.2f} ms")

    @pytest.mark.slow
    def test_large_problem_performance(self):
        """Benchmark larger problem (100+ variables).

        Tests scalability for complex system configurations.
        """
        results = {}

        for solver_name in ["CPLEX", "gekko", "ortools"]:
            model = Model(solver=solver_name)

            # 100 variables
            vars_list = [
                IntegerVar(domain=range(1, 50), name=f"x{i}") for i in range(100)
            ]

            for var in vars_list:
                model.add_variable(var)

            # Add 20 constraints
            for i in range(0, 80, 4):
                model.add_constraint(
                    vars_list[i]
                    + vars_list[i + 1]
                    + vars_list[i + 2]
                    + vars_list[i + 3]
                    >= 50
                )

            # Objective
            total = sum(vars_list)
            model.add_objective(total, minimize=True)

            # Measure solve time
            start = time.time()
            solution = model.solve()
            elapsed = time.time() - start

            results[solver_name] = {
                "time": elapsed,
                "feasible": solution.is_feasible,
            }

        # Print results
        print("\n=== LARGE PROBLEM (100 variables, 20 constraints) ===")
        for solver_name, result in results.items():
            print(f"{solver_name:10s}: {result['time']*1000:7.2f} ms")


class TestSolverRecommendations:
    """Recommendations for solver selection based on problem type."""

    @staticmethod
    def print_recommendations():
        """Print solver recommendations for different use cases."""
        recommendations = """
=== SOLVER SELECTION GUIDE ===

CPLEX (docplex):
- Best for: Deterministic solutions, mixed-integer problems, guaranteed optimality
- Strengths: Fast for most problem sizes, best for production use
- Requirements: Commercial license (free academic licenses available)
- Use when: You need guaranteed optimal solutions

GEKKO:
- Best for: Open-source projects, embedded systems, optimization research
- Strengths: Free, handles continuous optimization, good for learning
- Limitations: Slower for large integer problems, numerical precision issues
- Use when: Cost is primary concern or you have continuous variables

OR-Tools:
- Best for: Modern constraint programming, fast solutions, open-source
- Strengths: Fast for many problem types, free, active development
- Limitations: Newer, fewer real-world deployments
- Use when: You want modern CP-SAT approach with good performance

RECOMMENDATIONS BY PROBLEM TYPE:

1. PLL/Clock Configuration (Small: 3-10 vars)
   → CPLEX or OR-Tools (both very fast)

2. Clock Divider Problems (Medium: 16-50 vars)
   → CPLEX (slightly faster)

3. Converter JESD Parameters (Medium: 20-50 vars)
   → CPLEX or OR-Tools

4. Large System Configuration (100+ vars)
   → CPLEX (more mature)

5. Embedded/Portable (no license)
   → GEKKO or OR-Tools

6. Academic/Research
   → GEKKO (free) or CPLEX (academic license)
        """
        print(recommendations)

    def test_print_recommendations(self):
        """Print solver selection recommendations."""
        self.print_recommendations()
