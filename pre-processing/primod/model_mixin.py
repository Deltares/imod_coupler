"""Module containing mixins for specific kernels, for example MODFLOW."""

import numpy as np
from imod.mf6 import Modflow6Simulation, StructuredDiscretization
from imod.mf6.mf6_wel_adapter import Mf6Wel
from imod.mf6.wel import LayeredWell


class MetaModMixin:
    """MetaSWAP-Modflow coupling specific methods."""

    @staticmethod
    def get_mf6_pkgs_for_metaswap(
        coupling_dicts: list[dict[str, str]], mf6_simulation: Modflow6Simulation
    ) -> tuple[dict[str, StructuredDiscretization], dict[str, Mf6Wel]]:
        """
        Get names of DIS and possibly WEL packages from coupling_dict then fetch
        these MODFLOW 6 packages from simulation.
        """
        mf6_model_keys = [
            coupling_dict["mf6_model"] for coupling_dict in coupling_dicts
        ]
        msw_model_keys = [
            coupling_dict["msw_model"] for coupling_dict in coupling_dicts
        ]

        mf6_wel_pkg_keys = [
            coupling_dict["mf6_msw_well_pkg"]
            if "mf6_msw_well_pkg" in coupling_dict.keys()
            else None
            for coupling_dict in coupling_dicts
        ]
        mf6_dis_pkg: dict[str, StructuredDiscretization] = {}
        mf6_wel_pkg: dict[str, Mf6Wel]

        for mf6_model_key, msw_model_key, mf6_wel_pkg_key in zip(
            mf6_model_keys, msw_model_keys, mf6_wel_pkg_keys
        ):
            gwf_model = mf6_simulation[mf6_model_key]
            mf6_dis_key = gwf_model.get_diskey()
            mf6_dis_pkg[msw_model_key] = gwf_model[mf6_dis_key]

            if mf6_wel_pkg_key is not None:
                mf6_wel_pkg[msw_model_key] = gwf_model.prepare_wel_for_mf6(
                    mf6_wel_pkg_key, True, True
                )
            else:
                mf6_wel_pkg[msw_model_key] = None

        return mf6_dis_pkg, mf6_wel_pkg
