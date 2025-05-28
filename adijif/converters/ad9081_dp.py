"""AD9081 Datapath Description Class."""


class ad9081_dp_rx:
    """AD9081 RX Data Path Configuration."""

    cddc_enabled = [True, True, True, True]
    cddc_decimations = [1, 1, 1, 1]
    cddc_decimations_available = [1, 2, 3, 4, 6]
    cddc_nco_frequencies = [0, 0, 0, 0]
    cddc_nco_phases = [0, 0, 0, 0]

    fddc_enabled = [False, False, False, False, False, False, False, False]
    fddc_decimations = [1, 1, 1, 1, 1, 1, 1, 1]
    fddc_decimations_available = [1, 2, 3, 4, 6, 8, 12, 16, 24]
    fddc_nco_frequencies = [0, 0, 0, 0, 0, 0, 0, 0]
    fddc_nco_phases = [0, 0, 0, 0, 0, 0, 0, 0]
    fddc_source = [1, 1, 2, 2, 3, 3, 4, 4]

    __isfrozen = False

    def __init__(self) -> None:
        """Initialize the AD9081 RX datapath."""
        self._freeze()

    def __setattr__(self, key: str, value: any) -> None:
        """Set attribute intercept.

        Only allow setting of attributes that already exist.

        Args:
            key (str): attribute name
            value (any): attribute value

        Raises:
            TypeError: if attribute does not exist
        """
        if self.__isfrozen and not hasattr(self, key):
            raise TypeError("Property %r does not exist" % key)

        if key in ["cddc_decimations", "fddc_decimations"]:
            # Error if decimations are not a list
            if not isinstance(value, list):
                raise TypeError("Decimations must be a list")
            if key == "cddc_decimations":
                if len(value) != 4:
                    raise TypeError("CDDC Decimations must be a list of length 4")
                for v in value:
                    if v not in [1, 2, 3, 4, 6]:
                        raise TypeError("CDDC Decimations must be 1, 2, 3, 4, or 6")
            if key == "fddc_decimations":
                if len(value) != 8:
                    raise TypeError("FDDC Decimations must be a list of length 8")
                for v in value:
                    if v not in [1, 2, 3, 4, 6, 8, 12, 16, 24]:
                        raise TypeError(
                            "FDDC Decimations must be 1, 2, 4, 6, 8, 12, 16, or 24"
                        )
        object.__setattr__(self, key, value)

    def _freeze(self) -> None:
        self.__isfrozen = True

    def get_config(self) -> dict:
        """Get the datapath configuration for the AD9081 RX.

        Returns:
            dict: datapath configuration
        """
        datapath = {}
        datapath["cddc"] = {}
        datapath["cddc"]["enabled"] = self.cddc_enabled
        datapath["cddc"]["decimations"] = self.cddc_decimations
        datapath["cddc"]["nco_frequencies"] = self.cddc_nco_frequencies
        datapath["cddc"]["nco_phases"] = self.cddc_nco_phases

        datapath["fddc"] = {}
        datapath["fddc"]["enabled"] = self.fddc_enabled
        datapath["fddc"]["decimations"] = self.fddc_decimations
        datapath["fddc"]["nco_frequencies"] = self.fddc_nco_frequencies
        datapath["fddc"]["nco_phases"] = self.fddc_nco_phases
        datapath["fddc"]["source"] = self.fddc_source

        return datapath

    @property
    def decimation_overall(self) -> int:
        """Minimum Overall Decimation factor.

        Raises:
            Exception: No FDDC or CDDC enabled
            Exception: Enabled FDDC's source CDDC not enabled

        Returns:
            int: minimum overall decimation factor
        """
        if (not any(self.fddc_enabled)) and (not any(self.cddc_enabled)):
            raise Exception("No FDDCs or CDDCs enabled")

        min_dec = -1
        if any(self.fddc_enabled):
            for i, fdec in enumerate(self.fddc_decimations):
                if self.fddc_enabled[i]:
                    cddc = self.fddc_source[i] - 1
                    if not self.cddc_enabled:
                        raise Exception(f"Source CDDC {cddc} not enabled for FDDC {i}")
                    cdec = self.cddc_decimations[cddc]
                    if (cdec * fdec < min_dec) or min_dec == -1:
                        min_dec = cdec * fdec
        else:
            for i, cdec in enumerate(self.cddc_decimations):
                if self.cddc_enabled[i] and (min_dec == -1 or cdec < min_dec):
                    min_dec = cdec

        return min_dec


class ad9081_dp_tx:
    """AD9081 TX Data Path Configuration."""

    cduc_enabled = [True, True, True, True]
    cduc_interpolation = 1
    cduc_nco_frequencies = [0, 0, 0, 0]
    cduc_nco_phases = [0, 0, 0, 0]

    fduc_enabled = [False, False, False, False, False, False, False, False]
    fduc_interpolation = 1
    fduc_nco_frequencies = [0, 0, 0, 0, 0, 0, 0, 0]
    fduc_nco_phases = [0, 0, 0, 0, 0, 0, 0, 0]

    cduc_sources = [[1], [1], [3], [3]]

    __isfrozen = False

    def __init__(self) -> None:
        """Initialize the AD9081 TX datapath."""
        self._freeze()

    def __setattr__(self, key: str, value: any) -> None:
        """Set attribute intercept.

        Only allow setting of attributes that already exist.

        Args:
            key (str): attribute name
            value (any): attribute value

        Raises:
            TypeError: if attribute does not exist
        """
        if self.__isfrozen and not hasattr(self, key):
            raise TypeError("Property %r does not exist" % key)

        if key in ["cduc_interpolation", "fduc_interpolation"]:
            # Error if interpolation is a list
            if isinstance(value, list):
                raise TypeError("Interpolation must be an integer, not a list")
            if key == "cduc_interpolation" and value not in [1, 2, 4, 6, 8, 12]:
                raise TypeError("CDUC Interpolation must be 1, 2, 4, 6, 8, or 12")
            if key == "fduc_interpolation" and value not in [1, 2, 3, 4, 6, 8]:
                raise TypeError("FDUC Interpolation must be 1, 2, 3, 4, 6, or 8")
        object.__setattr__(self, key, value)

    def _freeze(self) -> None:
        self.__isfrozen = True

    def get_config(self) -> dict:
        """Get the datapath configuration for the AD9081 TX.

        Returns:
            dict: Datapath configuration
        """
        datapath = {}
        datapath["cduc"] = {}
        datapath["cduc"]["enabled"] = self.cduc_enabled
        datapath["cduc"]["interpolation"] = self.cduc_interpolation
        datapath["cduc"]["nco_frequencies"] = self.cduc_nco_frequencies
        datapath["cduc"]["nco_phases"] = self.cduc_nco_phases
        datapath["cduc"]["sources"] = self.cduc_sources

        datapath["fduc"] = {}
        datapath["fduc"]["enabled"] = self.fduc_enabled
        datapath["fduc"]["interpolation"] = self.fduc_interpolation
        datapath["fduc"]["nco_frequencies"] = self.fduc_nco_frequencies
        datapath["fduc"]["nco_phases"] = self.fduc_nco_phases

        return datapath

    @property
    def interpolation_overall(self) -> int:
        """Minimum Overall Interpolation factor.

        Raises:
            Exception: No FDDC or CDDC enabled
            Exception: Enabled FDDC's source CDDC not enabled

        Returns:
            int: minimum overall interpolation factor
        """
        if (not any(self.fduc_enabled)) and (not any(self.cduc_enabled)):
            raise Exception("No FDUCs or CDUCs enabled")

        if any(self.fduc_enabled):
            return self.fduc_interpolation * self.cduc_interpolation
        else:
            return self.cduc_interpolation
