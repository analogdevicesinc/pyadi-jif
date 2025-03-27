"""Cross part connector methods for system models."""

from typing import List

from adijif.clocks.clock import clock as clockc
from adijif.converters.converter import converter as convc
from adijif.fpgas.fpga import fpga as fpgac
from adijif.plls.pll import pll as pllc

import adijif  # isort:skip


class SystemPLL:

    _plls_sysref = []

    @property
    def plls_sysref(self) -> List[pllc]:
        """External PLLs used as SYSREF sources for converters and FPGA

        Returns:
            List: List of PLL objects
        """
        return self._plls_sysref

    def add_pll_sysref(
        self, pll_name: str, clk: clockc, cnv: convc = None, fpga: fpgac = None
    ) -> None:
        """Add External PLL to system between clock chip, converter and FPGA.

        Args:
            pll_name (str): Name of PLL class
            clk (clockc): Clock chip reference
            cnv (convc): Converter to be driven by PLL
            fpga (fpgac): FPGA to be driven by PLL
        """
        pll = eval(f"adijif.{pll_name}(self.model,solver=self.solver)")
        self._plls_sysref.append(pll)
        pll._connected_to_output = []
        pll._ref = clk
        assert cnv or fpga, "Converter or FPGA must be connected to PLL"
        if cnv:
            pll._connected_to_output.append(cnv.name)
        if fpga:
            pll._connected_to_output.append(fpga.name)

    def _get_ref_clock(self, conv, config, clock_names):
        config[f"{conv.name}_ref_clk"] = self.clock._get_clock_constraint(
            f"{conv.name}_ref_clk"
        )
        clock_names.append(f"{conv.name}_ref_clk")
        return config, clock_names

    def _get_ref_clock_fpga(self, conv, config, clock_names, need_separate_link_clock):
        if conv._nested:
            names = conv._nested
            for name in names:
                config[f"{name}_fpga_ref_clk"] = self.clock._get_clock_constraint(
                    "xilinx" + "_" + name
                )
                clock_names.append(f"{name}_fpga_ref_clk")
                # sys_refs.append(config[name + "_fpga_ref_clk"])

                if need_separate_link_clock:
                    config[f"{name}_fpga_link_out_clk"] = (
                        self.clock._get_clock_constraint(
                            "xilinx" + "_" + name + "_link_out"
                        )
                    )
                    clock_names.append(f"{name}_fpga_link_out_clk")

        else:
            config[f"{conv.name}_fpga_ref_clk"] = self.clock._get_clock_constraint(
                "xilinx" + "_" + conv.name
            )
            clock_names.append(f"{conv.name}_fpga_ref_clk")
            # sys_refs.append(config[f"{conv.name}_fpga_ref_clk"])

            if need_separate_link_clock:
                config[f"{conv.name}_fpga_link_out_clk"] = (
                    self.clock._get_clock_constraint(
                        "xilinx" + "_" + conv.name + "_link_out"
                    )
                )
                clock_names.append(f"{conv.name}_fpga_link_out_clk")

        return config, clock_names

    def _get_ext_sysref_clock(self, name, config, clock_names):
        found = False
        if self._plls_sysref:
            for pll in self._plls_sysref:

                if name in pll._connected_to_output:
                    config[f"{name}_sysref"] = pll._get_clock_constraint(
                        f"{name}_sysref"
                    )
                    clock_names.append(f"{name}_sysref")
                    found = True
                    break
        return found, config, clock_names

    def _get_sysref_clock(self, conv, config, clock_names):
        if conv._nested:  # MxFE, Transceivers
            assert isinstance(conv._nested, list)
            names = conv._nested
            for name in names:
                # Check if we want to use external PLL for SYSREF
                found, config, clock_names = self._get_ext_sysref_clock(
                    name, config, clock_names
                )
                if not found:
                    # Use clock chip for SYSREF
                    config[f"{name}_sysref"] = self.clock._get_clock_constraint(
                        f"{name}_sysref"
                    )
                    clock_names.append(f"{name}_sysref")
        else:
            found, config, clock_names = self._get_ext_sysref_clock(
                conv.name, config, clock_names
            )
            if not found:
                # Use clock chip for SYSREF
                config[f"{conv.name}_sysref"] = self.clock._get_clock_constraint(
                    f"{conv.name}_sysref"
                )
                clock_names.append(f"{conv.name}_sysref")
        return config, clock_names

    def __apply_ext_sysref_constraint(self, name, clks, config, sys_refs):
        found = False
        if self._plls_sysref:
            for pll in self._plls_sysref:
                if name in pll._connected_to_output:
                    self.clock._add_equation(config[f"{name}_sysref"] == clks[1])
                    sys_refs.append(config[f"{name}_sysref"])
                    found = True
                    break
        return found, sys_refs

    def _apply_sysref_constraint(self, device, clks, config, sys_refs):
        if device._nested:
            names = device._nested
            for i, name in enumerate(names):
                found, sys_refs = self.__apply_ext_sysref_constraint(
                    name, clks, config, sys_refs
                )
                if not found:
                    self.clock._add_equation(config[f"{name}_sysref"] == clks[i + 1])
                    sys_refs.append(config[f"{name}_sysref"])
        else:
            found, sys_refs = self.__apply_ext_sysref_constraint(
                device.name, clks, config, sys_refs
            )
            if not found:
                self.clock._add_equation(config[f"{device.name}_sysref"] == clks[1])
                sys_refs.append(config[f"{device.name}_sysref"])

        return sys_refs
