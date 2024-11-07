"""Module containing mixins for specific kernels, for example MODFLOW."""

from imod.mf6 import Modflow6Simulation, StructuredDiscretization
from imod.mf6.mf6_wel_adapter import Mf6Wel


class ModflowMixin:
    """Modflow specific methods to add to coupling objects."""

    @staticmethod
    def get_mf6_pkgs_with_coupling_dict(
        coupling_dict: dict[str, str], mf6_simulation: Modflow6Simulation
    ) -> tuple[StructuredDiscretization, Mf6Wel | None]:
        """
        Get names of DIS and possibly WEL packages from coupling_dict then fetch
        these MODFLOW 6 packages from simulation.
        """
        mf6_model_key = coupling_dict["mf6_model"]
        gwf_model = mf6_simulation[mf6_model_key]
        mf6_dis_key = gwf_model._get_diskey()
        mf6_dis_pkg = gwf_model[mf6_dis_key]

        mf6_wel_pkg = None
        if "mf6_msw_well_pkg" in coupling_dict.keys():
            mf6_well_key = coupling_dict["mf6_msw_well_pkg"]
            mf6_wel_pkg = gwf_model.prepare_wel_for_mf6(mf6_well_key, True, True)
        return mf6_dis_pkg, mf6_wel_pkg
