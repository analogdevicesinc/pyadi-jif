"""A set of helper functions to simplify JESD core programming."""


class jesd_math:
    def _jesd_simple_table(self, mode_table: dict) -> dict:
        """Convert JESD mode table to simple mode table where each configuration
        set is converted to a simple scalar
        """
        pass

    __internal_variable_clocks_setup: bool = False
    __internal_lookup_generated: bool = False

    def _update_jesd_mode(self, settings: dict, a_b_c: str):
        """Update individual JESD mode settings"""
        print("settings", settings)
        self.jesd_class = a_b_c
        for key in settings:
            setattr(self, key, settings[key])

    def _lookup_variable_clocks(self) -> dict:
        """Lookup bit clock from soultion and table"""
        if self.__internal_lookup_generated:
            return
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
                    self._update_jesd_mode(mode_d, a_b_c)
                    self._jesd_solve_mode = "complete"
                    self.__internal_lookup_generated = True
                    return

        raise Exception("No valid solution for bit_clock lookup")

    def _generate_variable_clocks(self, model) -> dict:
        if self.solver != "CPLEX":
            raise Exception("Solver must be CPLEX")

        if self.__internal_variable_clocks_setup:
            return

        if not hasattr(self, "config"):
            self.config = {}
        bit_clocks = []
        multiframe_clocks = []
        frame_clocks = []
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
                multiframe_clocks.append(
                    self.config[f"jesd_table_{self.name}_{a_b_c}_mode_{mode_d}"]
                    * ref
                    / mode["S"]
                    / mode["K"]
                )
                frame_clocks.append(
                    self.config[f"jesd_table_{self.name}_{a_b_c}_mode_{mode_d}"]
                    * ref
                    / mode["S"]
                )

        # Set constraint only one bit_clock is selected
        model.add_constraint([model.sum(valids) == 1])

        self.config["bit_clock"] = model.sum(bit_clocks)
        self.config["multiframe_clock"] = model.sum(multiframe_clocks)
        self.config["frame_clocks"] = model.sum(frame_clocks)

        self.__internal_variable_clocks_setup = True
        # self.config['bit_clock'] = v_bit_clocks
        # self.config = config
        return self.config["bit_clock"]
