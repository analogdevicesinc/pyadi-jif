import adijif as jif
from adijif.converters.converter import converter

fpga = jif.xilinx()
fpga.setup_by_dev_kit_name("vcu118")

# class dummy_converter(converter):
#     name = "dummy"

# dc = dummy_converter()
dc = jif.ad9680()


fpga_ref = jif.types.arb_source("FPGA_REF")
link_out_ref = jif.types.arb_source("LINK_OUT_REF")

clocks = fpga.get_required_clocks(dc, fpga_ref(fpga.model), link_out_ref(fpga.model))
print(clocks)

solution = fpga.model.solve(LogVerbosity="Quiet")
solution.write()

settings = {}
# Get clock values
clock_values = {}
for clk in [fpga_ref, link_out_ref]:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values


settings['fpga'] = fpga.get_config(dc, settings['clocks']['FPGA_REF'], solution)
print(settings)


image_data = fpga.draw(settings)

with open("xilinx_example.svg", "w") as f:
    f.write(image_data)