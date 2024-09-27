# flake8: noqa
# pytype: skip-file
import numpy as np

from adijif.clocks.clock import clock


class ad9528_bf(clock):
    """Brute force methods for calculating clocks

    These are currently meant for debug to compare against
    the solver solutions
    """

    def list_available_references(self, divider_set):
        """list_available_references: Based on config list possible
        references that can be generated based on VCO and output
        dividers
        """
        # Check input
        ref = {
            "m1": 3,
            "n2": 2,
            "vco": 3000000000,
            "r1": 24,
            "required_output_divs": np.array([1.0]),
        }
        for key in ref:
            if key not in divider_set:
                raise Exception(
                    "Input must be of type dict with fields: " + str(ref.keys())
                )
        return [
            divider_set["vco"] / divider_set["m1"] / div for div in self.d_available
        ]

    def find_dividers(self, vcxo, required_output_rates, find=3):
        if self.use_vcxo_double:
            vcxo *= 2

        mod = np.gcd.reduce(np.array(required_output_rates, dtype=int))
        configs = []

        for r1 in self.r1_available:
            pfd = vcxo / r1
            if pfd > self.pfd_max:
                continue
            for m1 in self.m1_available:
                for n2 in self.n2_available:
                    # RECHECK THIS. NOT WELL DOCUMENTED
                    vco = pfd * m1 * n2
                    # Check bounds and integer
                    if (
                        vco > self.vco_min
                        and vco < self.vco_max
                        and (vco / m1) % mod == 0
                    ):
                        required_output_divs = (vco / m1) / required_output_rates
                        if np.all(np.in1d(required_output_divs, self.d_available)):
                            configs.append(
                                {
                                    "m1": m1,
                                    "vco": vco,
                                    "n2": n2,
                                    "r1": r1,
                                    "required_output_divs": required_output_divs,
                                }
                            )

        return configs
