# flake8: noqa
# pytype: skip-file
import numpy as np

from adijif.clocks.clock import clock


class ad9523_1_bf(clock):
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
            "vco": 3000000000,
            "r2": 24,
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

        # even =  np.arange(2, 4096, 2, dtype=int)
        # odivs = np.append([1, 3, 5], even)

        mod = np.gcd.reduce(np.array(required_output_rates, dtype=int))
        configs = []

        for n2 in self.n2_available:
            for r2 in self.r2_available:
                pfb = vcxo / r2
                if pfb > self.pfd_max:
                    continue
                vco = pfb * n2
                if vco > self.vco_min and vco < self.vco_max:
                    for m1 in self.m1_available:
                        # print("vco",vco,mod,m1)
                        if (vco / m1) % mod == 0:
                            # See if we can use only m1 and not both m1+m2
                            rods = (vco / m1) / required_output_rates
                            if np.all(np.in1d(rods, self.d_available)):
                                configs.append(
                                    {
                                        "m1": m1,
                                        "n2": n2,
                                        "vco": vco,
                                        "r2": r2,
                                        "required_output_divs": rods,
                                    }
                                )
                            else:
                                # Try to use m2 as well to meet required out clocks
                                f1 = np.in1d(rods, self.d_available)
                                for m2 in self.m1_available:
                                    rods2 = (vco / m2) / required_output_rates
                                    f2 = np.in1d(rods2, self.d_available)
                                    if np.logical_or(f1, f2).all():
                                        configs.append(
                                            {
                                                "m1": m1,
                                                "m2": m2,
                                                "n2": n2,
                                                "vco": vco,
                                                "r2": r2,
                                                "required_output_divs": rods[
                                                    f1
                                                ].tolist(),
                                                "required_output_divs2": rods2[
                                                    f2
                                                ].tolist(),
                                            }
                                        )

        return configs
