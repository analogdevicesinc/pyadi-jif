"""AD9152 Datapath Description Class."""

class ad9152_dp:
    """AD9152 TX Data Path Configuration."""

    interpolation = 1
    interpolation_available = [1, 2, 4, 8]

    __isfrozen = False

    def __init__(self) -> None:
        """Initialize the AD9152 TX datapath."""
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

        if key == "interpolation" and value not in self.interpolation_available:
            raise TypeError(f"Interpolation must be in {self.interpolation_available}")
            
        object.__setattr__(self, key, value)

    def _freeze(self) -> None:
        self.__isfrozen = True

    def get_config(self) -> dict:
        """Get the datapath configuration for the AD9152 TX.

        Returns:
            dict: Datapath configuration
        """
        return {"interpolation": self.interpolation}

    @property
    def interpolation_overall(self) -> int:
        """Overall Interpolation factor.

        Returns:
            int: overall interpolation factor
        """
        return self.interpolation
