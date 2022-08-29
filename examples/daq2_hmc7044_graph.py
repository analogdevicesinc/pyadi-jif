# Determine clocking for DAQ2

import pprint
import adijif

vcxo = 125000000

sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo)

# Get Converter clocking requirements
sys.converter.sample_clock = 1e9
sys.converter.decimation = 1
sys.converter.set_quick_configuration_mode(str(0x88))
sys.converter.K = 32
sys.Debug_Solver = False

# Get FPGA clocking requirements
sys.fpga.setup_by_dev_kit_name("zc706")
sys.fpga.force_qpll = 1

cfg = sys.solve()
pprint.pprint(cfg)

g = sys.create_graph(cfg)
# g.graph_attr['splines'] = 'true'
# g.graph_attr['sep'] = '0.5'
# g.graph_attr['overlap'] = 'false'

g.format = 'svg'
g.view()
print(g.source)

# testgraph = g.source

# import dot2tex

# texcode = dot2tex.dot2tex(testgraph, format='tikz', crop=True)

# print(texcode)
# with open("test.tex", "w") as f:
#     f.write(texcode)
# with open("test.dot", "w") as f:
#     f.write(testgraph)
