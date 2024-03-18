import abc


class DriverCoupling(abc.ABC):
    """
    Abstract base class for driver couplings.
    """

    @abc.abstractmethod
    def derive_mapping(self, *args, **kwargs):
        pass
