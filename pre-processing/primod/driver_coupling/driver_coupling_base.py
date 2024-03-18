import abc
from pathlib import Path
from typing import Any


class DriverCoupling(abc.ABC):
    """
    Abstract base class for driver couplings.
    """

    @abc.abstractmethod
    def derive_mapping(self, *args, **kwargs) -> Any:
        pass

    @abc.abstractmethod
    def write_exchanges(self, directory: Path, coupled_model: Any) -> dict[str, Any]:
        pass
