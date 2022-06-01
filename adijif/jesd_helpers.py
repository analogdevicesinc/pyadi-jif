"""A set of helper functions to simplify JESD core programming."""


# from adijif.converters.converter import converter


class jesd_math:
    def _jesd_simple_table(self, mode_table: dict) -> dict:
        """Convert JESD mode table to simple mode table where each configuration
        set is converted to a simple scalar
        """
        pass

    def _lookup_bit_clock(self) -> dict:
        """Lookup bit clock from soultion and table"""
        if not hasattr(self, "solution") or not self.solution.is_solution():
            raise Exception("No valid solution for bit_clock lookup")

        for a_b_c in self.quick_configuration_modes:
            if a_b_c == "jesd204b":
                encoding = "8b10b"
            else:
                encoding = "64b66b"
            for mode in self.quick_configuration_modes[a_b_c]:
                mode_d = self.quick_configuration_modes[a_b_c][mode]
                key = f"jesd_mode_enable_{self.name}_{a_b_c}_{mode}"
                if self.solution.get_value(key) > 0:
                    return (
                        mode_d["M"]
                        / mode_d["L"]
                        * mode_d["Np"]
                        * self.encodings_d[encoding]
                        / self.encodings_n[encoding]
                        * self.sample_clock
                    )

        raise Exception("No valid solution for bit_clock lookup")

    def _generate_variable_bit_clock(self, model) -> dict:
        if self.solver != "CPLEX":
            raise Exception("Solver must be CPLEX")

        self.config = {}
        bit_clocks = []
        valids = []
        ref = self.sample_clock

        for a_b_c in self.quick_configuration_modes:
            if a_b_c == "jesd204b":
                encoding = self.encodings_d["8b10b"] / self.encodings_n["8b10b"]
            else:
                encoding = self.encodings_d["64b66b"] / self.encodings_n["64b66b"]

            for mode_d in self.quick_configuration_modes[a_b_c]:
                mode = self.quick_configuration_modes[a_b_c][mode_d]

                self.config[
                    f"jesd_table_{self.name}_{a_b_c}_mode_{mode_d}"
                ] = self._convert_input(
                    [0, 1], f"jesd_mode_enable_{self.name}_{a_b_c}_{mode_d}"
                )
                valids.append(
                    self.config[f"jesd_table_{self.name}_{a_b_c}_mode_{mode_d}"]
                )

                bit_clocks.append(
                    mode["M"]
                    / mode["L"]
                    * mode["Np"]
                    * encoding
                    * ref
                    * self.config[f"jesd_table_{self.name}_{a_b_c}_mode_{mode_d}"]
                )

        # Set constraint only one bit_clock is selected
        model.add_constraint([model.sum(valids) == 1])

        self.config["bit_clock"] = model.sum(bit_clocks)
        # self.config['bit_clock'] = v_bit_clocks
        # self.config = config
        return self.config["bit_clock"]
