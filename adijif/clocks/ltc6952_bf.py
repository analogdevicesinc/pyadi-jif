# flake8: noqa
import numpy as np

from adijif.clocks.clock import clock


class ltc6952_bf(clock):
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
            "n2": 2,
            "vco": 3000000000,
            "r2": 24,
            "required_output_divs": np.array([1.0]),
        }
        for key in ref:
            if key not in divider_set:
                raise Exception(
                    "Input must be of type dict with fields: " + str(ref.keys())
                )
        return [divider_set["vco"] / div for div in self.d_available]

    def find_dividers(self, vcxo, rates, find=3):
        v = []
        for mp in range(0, 32):
            for nx in range(0, 8):
                val = (mp + 1) * pow(2, nx)
                v.append(val)

        odivs = np.unique(v)

        mod = np.gcd.reduce(np.array(rates, dtype=int))
        vcos = []
        configs = []

        for n in range(self.n2_divider_min, self.n2_divider_max):
            for r in range(self.r2_divider_min, self.r2_divider_max):
                # Check VCO in range and output clock a multiple of required reference
                f = vcxo * n / r
                if f >= self.vco_min and f <= self.vco_max:
                    # Check if required dividers for output clocks are in set
                    if f % mod == 0:
                        d = f / rates
                        if np.all(np.in1d(d, odivs)) and f not in vcos:
                            if f not in vcos:
                                vcos.append(f)
                                config = {
                                    "n2": n,
                                    "r2": r,
                                    "vco": f,
                                    "required_output_divs": d,
                                }
                                configs.append(config)
                                if len(configs) >= find:
                                    return configs

        return configs
