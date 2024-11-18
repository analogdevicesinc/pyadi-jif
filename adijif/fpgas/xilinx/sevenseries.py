from .pll import XilinxPLL


class SevenSeries(XilinxPLL):

    # References
    # GTXs
    # https://docs.amd.com/v/u/en-US/ug476_7Series_Transceivers

    transceiver_types_available = ["GTXE2", "GTHE2"]


class SevenSeriesCPLL:

    M_available = [1, 2]
    _M = [1, 2]

    @property
    def M(self):
        return self._M

    @M.setter
    def M(self, value):
        if value in self.M_available:
            self._M = value
        else:
            raise ValueError(f"M value not available. Choose from {self.M_available}")
        
    
