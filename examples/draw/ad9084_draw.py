import adijif as jif


adc = jif.ad9084_rx()
adc.sample_clock = int(2.5e9)
adc.datapath.cddc_decimations = [4] * 4
adc.datapath.fddc_decimations = [2] * 8
adc.datapath.fddc_enabled = [True] * 8

rx_jesd_mode = jif.utils.get_jesd_mode_from_params(
    adc,
    M=4,
    L=8,
    S=1,
    Np=16,
    jesd_class="jesd204c",
)
assert rx_jesd_mode
rx_jesd_mode = rx_jesd_mode[0]["mode"]
adc.set_quick_configuration_mode(rx_jesd_mode, "jesd204c")

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
# print(dir(adc))
image_data = adc.draw(settings["clocks"])

with open("ad9084_example.svg", "w") as f:
    f.write(image_data)