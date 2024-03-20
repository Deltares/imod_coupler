import abc
from pathlib import Path
from typing import Any

from primod.driver_coupling.driver_coupling_base import DriverCoupling


class CoupledModel(abc.ABC):
    coupling_list: list[DriverCoupling]

    @abc.abstractmethod
    def write(self, directory: str | Path, *args: Any, **kwargs: Any) -> None:
        pass

    @abc.abstractmethod
    def write_toml(self, directory: str | Path, *args: Any, **kwargs: Any) -> None:
        pass

    @staticmethod
    def _merge_coupling_dicts(dicts: list[dict[str, Any]]) -> dict[str, Any]:
        coupling_dict: dict[str, dict[str, Any] | Any] = {}
        for top_dict in dicts:
            for top_key, top_value in top_dict.items():
                if isinstance(top_value, dict):
                    if top_key not in coupling_dict:
                        coupling_dict[top_key] = {}
                    for key, filename in top_value.items():
                        coupling_dict[top_key][key] = filename
                else:
                    coupling_dict[top_key] = top_value
        return coupling_dict

    def write_exchanges(self, directory: str | Path) -> dict[str, Any]:
        """
        Write exchanges and return their filenames for the coupler
        configuration file.
        """
        directory = Path(directory)
        exchange_dir = Path(directory) / "exchanges"
        exchange_dir.mkdir(exist_ok=True, parents=True)

        coupling_dicts = []
        for coupling in self.coupling_list:
            coupling_dict = coupling.write_exchanges(
                directory=exchange_dir, coupled_model=self
            )
            coupling_dicts.append(coupling_dict)

        # FUTURE: if we support multiple MF6 models, group them by name before
        # merging, and return a list of coupling_dicts.
        merged_coupling_dict = self._merge_coupling_dicts(coupling_dicts)
        return merged_coupling_dict
