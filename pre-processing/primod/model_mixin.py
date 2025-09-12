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
    ) -> tuple[StructuredDiscretization, Mf6Wel | None]:
        """
        Get names of DIS and possibly WEL packages from coupling_dict then fetch
        these MODFLOW 6 packages from simulation.
        """
        mf6_model_keys = [
            coupling_dict["mf6_model"] for coupling_dict in coupling_dicts
        ]
        mf6_wel_pkg_keys = [
            coupling_dict["mf6_msw_well_pkg"]
            if "mf6_msw_well_pkg" in coupling_dict.keys()
            else None
            for coupling_dict in coupling_dicts
        ]
        dis_datasets = None
        mf6_wel_pkg = None
        for mf6_model_key, mf6_wel_pkg_key in zip(mf6_model_keys, mf6_wel_pkg_keys):
            gwf_model = mf6_simulation[mf6_model_key]
            mf6_dis_key = gwf_model.get_diskey()
            dis_dataset = gwf_model[mf6_dis_key].dataset
            dis_datasets = (
                dis_dataset if dis_datasets is None else dis_datasets.merge(dis_dataset)
            )
            if mf6_wel_pkg_key is not None:
                # wel_dataset = gwf_model[mf6_wel_pkg_key]
                mf6_wel_pkg = gwf_model.prepare_wel_for_mf6(mf6_wel_pkg_key, True, True)
                # wel_datasets = (
                #     wel_dataset
                #     if wel_datasets is None
                #     else wel_datasets.merge(wel_dataset)
                # )
        # mf6_wel_pkg = None
        # if wel_datasets is not None:
        #     mf6_wel_pkg = LayeredWell(
        #         x=wel_datasets["x"].to_numpy(),
        #         y=wel_datasets["y"].to_numpy(),
        #         layer=wel_datasets["layer"].astype(dtype=np.int32).to_numpy(),
        #         rate=wel_datasets["rate"].to_numpy(),
        #     )
        # gwf_model.prepare_wel_for_mf6(mf6_wel_pkg_key, True, True)
        assert dis_datasets is not None  # mypy
        mf6_dis_pkg = StructuredDiscretization(
            top=dis_datasets["top"],
            bottom=dis_datasets["bottom"],
            idomain=dis_datasets["idomain"].astype(dtype=np.int32),
        )
        return mf6_dis_pkg, mf6_wel_pkg
