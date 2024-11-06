import abc
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from imod.mf6 import Modflow6Simulation, StructuredDiscretization
from imod.mf6.mf6_wel_adapter import Mf6Wel

from primod.driver_coupling.driver_coupling_base import DriverCoupling


def get_mf6_pkgs_from_coupling_dict(
    coupling_dict: dict[str, Any], mf6_simulation: Modflow6Simulation
) -> tuple[StructuredDiscretization, Mf6Wel]:
    """
    Get MODFLOW 6 packages names from coupling_dict then fetch MODFLOW 6
    packages from simulation.
    """
    mf6_model_key = coupling_dict["mf6_model"]
    gwf_model = mf6_simulation[mf6_model_key]
    mf6_dis_key = gwf_model._get_diskey()
    mf6_well_key = coupling_dict["mf6_msw_well_pkg"]

    mf6_dis_pkg = gwf_model[mf6_dis_key]
    mf6_wel_pkg = gwf_model.prepare_wel_for_mf6(mf6_well_key, True, True)
    return mf6_dis_pkg, mf6_wel_pkg


class CoupledModel(abc.ABC):
    coupling_list: Sequence[DriverCoupling]

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
