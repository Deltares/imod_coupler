"""Module containing mixins for specific kernels, for example MODFLOW."""

from imod.mf6 import Modflow6Simulation, StructuredDiscretization
from imod.mf6.mf6_wel_adapter import Mf6Wel


class MetaModMixin:
    """MetaSWAP-Modflow coupling specific methods."""

    @staticmethod
    def get_mf6_pkgs_for_metaswap(
        coupling_dict_list: list[dict[str, str]], mf6_simulation: Modflow6Simulation
    ) -> tuple[dict[str, StructuredDiscretization], dict[str, Mf6Wel]]:
        """
        Get names of DIS and possibly WEL packages from coupling_dict then fetch
        these MODFLOW 6 packages from simulation.
        """
        mf6_dis_pkg: dict[str, StructuredDiscretization] = {}
        mf6_wel_pkg: dict[str, Mf6Wel] = {}
        for coupling in coupling_dict_list:
            if ("mf6_model" in coupling) and ("msw_model" in coupling):
                mf6_model_name = coupling["mf6_model"]
                msw_model_name = coupling["msw_model"]
                gwf_model = mf6_simulation[mf6_model_name]
                mf6_dis_key = gwf_model.get_diskey()
                mf6_dis_pkg[msw_model_name] = gwf_model[mf6_dis_key]

                if "mf6_msw_well_pkg" in coupling:
                    mf6_wel_pkg[msw_model_name] = gwf_model.prepare_wel_for_mf6(
                        coupling["mf6_msw_well_pkg"], True, True
                    )
                else:
                    mf6_wel_pkg[msw_model_name] = None

        return mf6_dis_pkg, mf6_wel_pkg
