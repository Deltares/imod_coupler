import abc
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class DriverCoupling(BaseModel, abc.ABC):
    """
    Abstract base class for driver couplings.
    """

    # Config required for e.g. geodataframes
    model_config = {"arbitrary_types_allowed": True}

    @abc.abstractmethod
    def derive_mapping(self, *args: Any, **kwargs: Any) -> Any:
        pass

    @abc.abstractmethod
    def write_exchanges(self, directory: Path, coupled_model: Any) -> dict[str, Any]:
        pass
