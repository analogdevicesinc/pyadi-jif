# flake8: noqa
from adijif.fpgas.fpga import fpga


class xilinx_bf(fpga):
    """Brute force methods for calculating clocks

    These are currently meant for debug to compare against
    the solver solutions
    """

    def determine_cpll(self, bit_clock, fpga_ref_clock):
        """
        Parameters:
            bit_clock:
                Equivalent to lane rate in bits/second
            fpga_ref_clock:
                System reference clock
        """
        assert isinstance(bit_clock, int), "bit_clock must be an int"
        assert isinstance(fpga_ref_clock, int), "fpga_ref_clock must be an int"

        # VCO = ( REF_CLK * N1 * N2 ) / M
        # bit_clock = ( VCO * 2 ) / D

        for m in [1, 2]:
            for d in [1, 2, 4, 8]:
                for n1 in [5, 4]:
                    for n2 in [5, 4, 3, 2, 1]:
                        vco = fpga_ref_clock * n1 * n2 / m
                        # print("VCO", self.vco_min/1e9, vco/1e9, self.vco_max/1e9)
                        if vco > self.vco_max or vco < self.vco_min:
                            continue
                        # print("VCO", vco)
                        # fpga_lane_rate = vco * 2 / d
                        # print("lane rate", fpga_lane_rate)

                        # VCO == 5,10,20,40 GHz

                        # print(fpga_ref_clock / m / d, bit_clock / (2 * n1 * n2))
                        if fpga_ref_clock / m / d == bit_clock / (2 * n1 * n2):
                            return {
                                "vco": vco,
                                "d": d,
                                "m": m,
                                "n1": n1,
                                "n2": n2,
                                "type": "CPLL",
                            }

        raise Exception("No valid CPLL configuration found")

    def determine_qpll(self, bit_clock, fpga_ref_clock):
        """
        Parameters:
            bit_clock:
                Equivalent to lane rate in bits/second
            fpga_ref_clock:
                System reference clock
        """

        if self.ref_clock_max < fpga_ref_clock or fpga_ref_clock < self.ref_clock_min:
            raise Exception("fpga_ref_clock not within range")

        for m in [1, 2, 3, 4]:
            for d in [1, 2, 4, 8, 16]:
                for n in self.N:
                    vco = fpga_ref_clock * n / m
                    if self.vco1_min <= vco <= self.vco1_max:
                        band = 1
                    elif self.vco0_min <= vco <= self.vco0_max:
                        band = 0
                    else:
                        continue

                    if fpga_ref_clock / m / d == bit_clock / n:
                        return {
                            "vco": vco,
                            "band": band,
                            "d": d,
                            "m": m,
                            "n": n,
                            "qty4_full_rate": 0,
                            "type": "QPLL",
                        }

                    if self.transciever_type != "GTY4":
                        continue

                    if fpga_ref_clock / m / d == bit_clock / 2 / n:
                        return {
                            "vco": vco,
                            "band": band,
                            "d": d,
                            "m": m,
                            "n": n,
                            "qty4_full_rate": 1,
                            "type": "QPLL",
                        }

        raise Exception("No valid QPLL configuration found")
