import numpy as np

from adijif.converters.adc import adc


class ad9680_bf(adc):
    """Brute force methods for calculating clocks

    These are currently meant for debug to compare against
    the solver solutions
    """

    def device_clock_available(self):
        """Generate list of possible device clocks"""
        aicd = sorted(self.input_clock_divider_available)

        dev_clocks = []
        for div in aicd:
            in_clock = self.sample_clock * self.decimation * div
            if in_clock <= self.input_clock_max:
                dev_clocks.append(in_clock)
        if not dev_clocks:
            raise Exception(
                "No device clocks possible in current config. Sample rate too high"
            )
        return dev_clocks

    def device_clock_ranges(self):
        """Generate min and max values for device clock"""

        clks = self.device_clock_available()
        return np.min(clks), np.max(clks)

    def sysref_clock_ranges(self):
        """sysref must be multiple of LMFC"""
        lmfc = self.multiframe_clock
        return lmfc / 2048, lmfc / 2

    def sysref_met(self, sysref_clock, sample_clock):
        if sysref_clock % self.multiframe_clock != 0:
            raise Exception("SYSREF not a multiple of LMFC")
        if (self.multiframe_clock / sysref_clock) < 2 * self.input_clock_divider:
            raise Exception("SYSREF not a multiple of LMFC > 1")
