from docplex.cp.modeler import if_then


class xilinx_pll_constraints:
    # UltraScale+ GTY PLLs
    # https://docs.amd.com/v/u/en-US/ug578-ultrascale-gty-transceivers
    # GTHs
    # https://docs.amd.com/v/u/en-US/ug576-ultrascale-gth-transceivers
    # GTXs
    # https://docs.amd.com/v/u/en-US/ug476_7Series_Transceivers

    transceivers = {
        "UltrascalePlus": ["GTYE4", "GTHE4"],
        "Ultrascale": ["GTYE3", "GTHE3"],
        "7kSeries": ["GTXE2", "GTHE2"],
    }

    def trx_gen(self) -> int:
        """Get transceiver generation (2,3,4)

        Returns:
            int: generation of transceiver
        """
        return int(self.transceiver_type[-1])

    def trx_variant(self):
        """Get transceiver variant (GTX, GTH, GTY, ...)

        Returns:
            str: Transceiver variant
        """
        # return self.transceiver_type[:2]
        trxt = self.transceiver_type[:2]
        print(trxt)
        assert len(trxt) == 3
        return trxt

    def add_cpll_contraints(self, config: dict, fpga_ref, converter) -> dict:
        """Add Channel PLL (CPLL) constraints.

        This applies to GTH and GTY transceivers.

        Args:
            config (dict): Configuration dictionary.
            fpga_ref (int): FPGA reference clock.
            converter (converter): Converter object.
        """
        config[converter.name + "_use_cpll"] = self._convert_input(
            [0, 1], converter.name + "_use_cpll"
        )
        # v = self.model.integer_var(min=0, max=1, name=converter.name + "_use_cpll2")
        # self.model.export_model()
        # input()
        # return config

        # Add variables
        config[converter.name + "_m_cpll"] = self._convert_input(
            [1, 2], converter.name + "_m_cpll"
        )
        # This is documented oddly
        # There are footnotes that include 16 with GTHs, and 16,32 with GTYs
        # but its says "not supported for CPLL"?!?!?
        config[converter.name + "_d_cpll"] = self._convert_input(
            [1, 2, 4, 8], converter.name + "_d_cpll"
        )
        config[converter.name + "_n1_cpll"] = self._convert_input(
            [4, 5], converter.name + "_n1_cpll"
        )
        config[converter.name + "_n2_cpll"] = self._convert_input(
            [1, 2, 3, 4, 5], converter.name + "_n2_cpll"
        )

        # Add intermediate variables
        config[converter.name + "_pll_out_cpll"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + "_n1_cpll"]
            * config[converter.name + "_n2_cpll"]
            / (config[converter.name + "_m_cpll"])
        )

        # Add constraints
        self._add_equation(
            [
                if_then(
                    config[converter.name + "_use_cpll"] == 1,
                    config[converter.name + "_d_cpll"] * converter.bit_clock
                    == config[converter.name + "_pll_out_cpll"] * 2,
                ),
                if_then(
                    config[converter.name + "_use_cpll"] == 1,
                    config[converter.name + "_pll_out_cpll"] >= self.vco_min,
                ),
                if_then(
                    config[converter.name + "_use_cpll"] == 1,
                    config[converter.name + "_pll_out_cpll"] <= self.vco_max,
                ),
            ]
        )

        return config

    # QPLLs
    def add_qpll_contraints(self, config: dict, fpga_ref, converter) -> dict:
        if self.transceiver_type not in ["GTH3", "GTH4", "GTY4"]:
            return self._add_qpll_contraints_7_series(config, fpga_ref, converter)

        return self._add_qpllN_contraints(config, fpga_ref, converter, 0)

    def add_qpll1_contraints(self, config: dict, fpga_ref, converter):
        if self.transceiver_type not in ["GTH3", "GTH4", "GTY4"]:
            config[converter.name + "_use_qpll1"] = 0
            return config

        return self._add_qpllN_contraints(config, fpga_ref, converter, 1)

    def _add_qpllN_contraints(self, config: dict, fpga_ref, converter, n: int) -> dict:
        """Add constraints for QPLL{n}.

        Args:
            config (dict): Configuration dictionary.
            fpga_ref (int): FPGA reference clock.
            converter (converter): Converter object.
            n (int): QPLL number 0 or 1.
        """

        assert (
            False
        ), "QPLL equations are seem to be wrong based on GT Series and are more based on 7 series vs US vs US+"
        # See equation 2-4 and 2-5 in https://docs.amd.com/v/u/en-US/ug576-ultrascale-gth-transceivers (differences is US+ and doesn't seem to be just GTH based)

        if n == 0:
            pname = "qpll"
        elif n == 1:
            pname = "qpll1"
        else:
            raise Exception("Unsupported QPLL type")

        if self.transceiver_type not in ["GTH3", "GTH4", "GTY4"]:
            config[converter.name + f"_use_{pname}"] = 0
            return config

        # Global flag to use QPLLn
        config[converter.name + f"_use_{pname}"] = self._convert_input(
            [0, 1], converter.name + f"_use_{pname}"
        )

        # Add variables
        config[converter.name + f"_m_{pname}"] = self._convert_input(
            [1, 2, 3, 4], converter.name + f"_m_{pname}"
        )
        config[converter.name + f"_d_{pname}"] = self._convert_input(
            [1, 2, 4, 8, 16, 32], converter.name + f"_d_{pname}"
        )
        config[converter.name + f"_n_{pname}"] = self._convert_input(
            [*range(16, 160)], converter.name + f"_n_{pname}"
        )

        assert False, "Confirm this is GTH specific"
        if self.transceiver_type[:3] == "GTH":
            clkout = 2
        else:
            clkout = [1, 2]

        config[converter.name + f"_clkout_rate_{pname}"] = self._convert_input(
            clkout, converter.name + f"_clkout_rate_{pname}"
        )
        config[converter.name + f"_sdm_data_{pname}"] = self.model.integer_var(
            min=0, max=(2**24 - 1), name=converter.name + f"_sdm_data_{pname}"
        )
        config[converter.name + f"_sdm_width_{pname}"] = self._convert_input(
            [16, 20, 24], converter.name + f"_sdm_width_{pname}"
        )
        config[converter.name + f"_HIGH_RATE_{pname}"] = self._convert_input(
            [0, 1], converter.name + f"_HIGH_RATE_{pname}"
        )

        # Add intermediate variables
        config[converter.name + f"_frac_{pname}"] = self._add_intermediate(
            config[converter.name + f"_sdm_data_{pname}"]
            / (2 ** config[converter.name + f"_sdm_width_{pname}"])
        )
        config[converter.name + f"_n_dot_frac_{pname}"] = self._add_intermediate(
            config[converter.name + f"_n_{pname}"]
            + config[converter.name + f"_frac_{pname}"]
        )
        config[converter.name + f"_pll_out_{pname}"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + f"_n_dot_frac_{pname}"]
            / (
                config[converter.name + f"_m_{pname}"]
                * config[converter.name + f"_clkout_rate_{pname}"]
            )
        )
        config[converter.name + f"_vco_{pname}"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + f"_n_dot_frac_{pname}"]
            / (
                config[converter.name + f"_m_{pname}"]
                * config[converter.name + f"_m_{pname}"]
            )
        )

        # Add constraints

        self._add_equation(
            [
                if_then(
                    config[converter.name + f"_use_{pname}"] == 1,
                    converter.bit_clock
                    == config[converter.name + f"_pll_out_{pname}"]
                    * 2
                    / config[converter.name + f"_d_{pname}"],
                ),
                if_then(
                    config[converter.name + f"_use_{pname}"] == 1,
                    config[converter.name + f"_HIGH_RATE_{pname}"]
                    == (converter.bit_clock >= 28.1e9),
                ),
            ]
        )

        vco_min = 9.8e9 if n == 0 else 8e9
        vco_max = 16.375e9 if n == 0 else 13e9

        self._add_equation(
            [
                if_then(
                    config[converter.name + f"_use_{pname}"] == 1,
                    config[converter.name + f"_vco_{pname}"] >= vco_min,
                ),
                if_then(
                    config[converter.name + f"_use_{pname}"] == 1,
                    config[converter.name + f"_vco_{pname}"] <= vco_max,
                ),
                if_then(
                    config[converter.name + f"_HIGH_RATE_{pname}"] == 1,
                    config[converter.name + f"_frac_{pname}"] == 0,
                ),
            ]
        )

        return config

    def _add_qpll_contraints_7_series(self, config: dict, fpga_ref, converter) -> dict:
        """Add constraints for QPLL for 7 series FPGAs.

        Args:
            config (dict): Configuration dictionary.
            fpga_ref (int): FPGA reference clock.
            converter (converter): Converter object.
        """
        pname = "qpll"

        # if self.transceiver_type not in ["GTH3", "GTH4", "GTY4"]:
        #     config[converter.name + f"_use_{pname}"] = 0
        #     return config

        # Double check this constraint
        if self.transceiver_type in ["GTH3", "GTH4", "GTY4"]:
            raise Exception("Invalid GT is for 7 series FPGAs")

        # Global flag to use QPLLn
        config[converter.name + f"_use_{pname}"] = self._convert_input(
            [0, 1], converter.name + f"_use_{pname}"
        )

        # Add variables
        config[converter.name + f"_m_{pname}"] = self._convert_input(
            [1, 2, 3, 4], converter.name + f"_m_{pname}"
        )
        config[converter.name + f"_d_{pname}"] = self._convert_input(
            [1, 2, 4, 8, 16], converter.name + f"_d_{pname}"
        )
        config[converter.name + f"_n_{pname}"] = self._convert_input(
            [16, 20, 32, 40, 64, 66, 80, 100], converter.name + f"_n_{pname}"
        )

        # Add intermediate variables
        config[converter.name + f"_vco_{pname}"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + f"_n_{pname}"]
            / config[converter.name + f"_m_{pname}"]
        )
        config[converter.name + f"_pll_out_{pname}"] = self._add_intermediate(
            fpga_ref
            * config[converter.name + f"_n_{pname}"]
            / (config[converter.name + f"_m_{pname}"] * 2)
        )

        # Add constraints
        self._add_equation(
            [
                if_then(
                    config[converter.name + f"_use_{pname}"] == 1,
                    converter.bit_clock
                    == config[converter.name + f"_pll_out_{pname}"]
                    * 2
                    / config[converter.name + f"_d_{pname}"],
                ),
            ]
        )

        assert False, "Confirm this is GTH/GTX specific"
        if self.transceiver_type[:3] == "GTH":
            vco_min = 8e9
            vco_max = 13.1e9
            self._add_equation(
                [
                    if_then(
                        config[converter.name + f"_use_{pname}"] == 1,
                        config[converter.name + f"_vco_{pname}"] >= vco_min,
                    ),
                    if_then(
                        config[converter.name + f"_use_{pname}"] == 1,
                        config[converter.name + f"_vco_{pname}"] <= vco_max,
                    ),
                ]
            )
        elif self.transceiver_type[:3] == "GTX":
            config[converter.name + f"_lower_band_{pname}"] = self._convert_input(
                [0, 1], converter.name + f"_lower_band_{pname}"
            )
            # Lower band
            c1 = if_then(
                config[converter.name + f"_use_{pname}"] == 1,
                if_then(
                    config[converter.name + f"_lower_band_{pname}"] == 0,
                    config[converter.name + f"_vco_{pname}"] >= 5.93e9,
                ),
            )
            c2 = if_then(
                config[converter.name + f"_use_{pname}"] == 1,
                if_then(
                    config[converter.name + f"_lower_band_{pname}"] == 0,
                    config[converter.name + f"_vco_{pname}"] <= 8e9,
                ),
            )
            # Upper band
            c3 = if_then(
                config[converter.name + f"_use_{pname}"] == 1,
                if_then(
                    config[converter.name + f"_lower_band_{pname}"] == 1,
                    config[converter.name + f"_vco_{pname}"] >= 9.8e9,
                ),
            )
            c4 = if_then(
                config[converter.name + f"_use_{pname}"] == 1,
                if_then(
                    config[converter.name + f"_lower_band_{pname}"] == 1,
                    config[converter.name + f"_vco_{pname}"] <= 12.5e9,
                ),
            )
            self._add_equation([c1, c2, c3, c4])

        else:
            raise Exception("Unsupported transceiver type")

        return config

    def get_cpll_config(self, config: dict, converter, fpga_ref) -> dict:
        """Get CPLL configuration.

        Args:
            config (dict): Configuration dictionary.
            converter (converter): Converter object.
        """
        pll_config = {}
        pll_config["type"] = "cpll"
        for k in ["m", "d", "n1", "n2"]:
            pll_config[k] = self._get_val(config[converter.name + "_" + k + "_cpll"])

        pll_config["vco"] = (
            fpga_ref * pll_config["n1"] * pll_config["n2"] / pll_config["m"]  # type: ignore # noqa: B950
        )
        # Check
        assert (
            pll_config["vco"] * 2 / pll_config["d"] == converter.bit_clock  # type: ignore # noqa: B950
        ), "Invalid CPLL lane rate"

        return pll_config

    def get_qpll_config(self, config: dict, converter, fpga_ref, n: int) -> dict:
        """Get QPLL configuration.

        Args:
            config (dict): Configuration dictionary.
            converter (converter): Converter object.
            n (int): QPLL number 0 or 1.
        """
        if n == 0:
            pname = "qpll"
        elif n == 1:
            pname = "qpll1"
        else:
            raise Exception("Unsupported QPLL type")

        if self.transceiver_type not in ["GTH3", "GTH4", "GTY4"]:
            return self.get_qpll_config_7_series(config, converter, fpga_ref)

        pll_config = {}
        pll_config["type"] = pname
        for k in ["m", "d", "n", "clkout_rate", "sdm_data", "sdm_width", "HIGH_RATE"]:
            pll_config[k] = self._get_val(
                config[converter.name + "_" + k + "_" + pname]
            )

        pll_config["frac"] = pll_config["sdm_data"] / (2 ** pll_config["sdm_width"])
        pll_config["n_dot_frac"] = pll_config["n"] + pll_config["frac"]
        # FIXME: Check clkout_rate between GTH and GTY
        pll_config["vco"] = fpga_ref * pll_config["n_dot_frac"] / (pll_config["m"])
        # Check
        assert (
            pll_config["vco"] * 2 / (pll_config["d"] * pll_config["clkout_rate"]) == converter.bit_clock  # type: ignore # noqa: B950
        ), f"Invalid {pname} lane rate. {pll_config['vco'] * 2 / pll_config['d']} != {converter.bit_clock}"  # type: ignore # noqa: B950

        return pll_config

    def get_qpll_config_7_series(self, config: dict, converter, fpga_ref) -> dict:
        """Get QPLL configuration for 7 series FPGAs.

        Args:
            config (dict): Configuration dictionary.
            converter (converter): Converter object.
        """
        pname = "qpll"

        pll_config = {"type": pname}
        for k in ["m", "d", "n"]:
            pll_config[k] = self._get_val(
                config[converter.name + "_" + k + "_" + pname]
            )

        pll_config["vco"] = fpga_ref * pll_config["n"] / pll_config["m"]
        pll_clk_out = fpga_ref * pll_config["n"] / (pll_config["m"] * 2)
        # Check
        assert (
            pll_clk_out * 2 / pll_config["d"] == converter.bit_clock  # type: ignore # noqa: B950
        ), f"Invalid QPLL lane rate {pll_config['vco'] * 2 / pll_config['d']} != {converter.bit_clock}"

        return pll_config
