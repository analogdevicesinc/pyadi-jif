"""This example shows how to draw a generic converter model. Not all
models have custom drawing functions, so this generic drawing function"""
import adijif as jif


adc = jif.adrv9009_rx()
adc.sample_clock = 122.88e6
adc.decimation = 4
adc.set_quick_configuration_mode("17", "jesd204b")

# Check static
adc.validate_config()

required_clocks = adc.get_required_clocks()
required_clock_names = adc.get_required_clock_names()

# Add generic clock sources for solver
clks = []
for clock, name in zip(required_clocks, required_clock_names):
    clk = jif.types.arb_source(name)
    adc._add_equation(clk(adc.model) == clock)
    clks.append(clk)

# Solve
solution = adc.model.solve(LogVerbosity="Quiet")
settings = adc.get_config(solution)

# Get clock values
clock_values = {}
for clk in clks:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values

print(settings)
print(dir(adc))
image_data = adc.draw(settings["clocks"])

with open("adrv9009_example.svg", "w") as f:
    f.write(image_data)