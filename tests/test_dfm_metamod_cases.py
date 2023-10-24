from pathlib import Path

import pytest
from hydrolib.core.dflowfm.mdu.models import FMModel
from imod.mf6 import Modflow6Simulation
from imod.msw import MetaSwapModel

from imod_coupler.drivers.dfm_metamod.dfm_metamod_model import DfmMetaModModel

""" 
this file contains testcases for the dfm_metamod coupling.
"""


def case_with_river(
    mf6_model_with_river: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
    prepared_dflowfm_model: FMModel,
) -> DfmMetaModModel:
    with_river = DfmMetaModModel(
        prepared_msw_model,
        mf6_model_with_river,
        prepared_dflowfm_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_river_active_pkgkey="Oosterschelde",
        mf6_river_passive_pkgkey="Westerschelde",
        mf6_wel_correction_pkgkey="RIV_CORR",
        mf6_wel_pkgkey="wells_msw",
        mf6_river_to_dfm_1d_q_dmm_path=Path("sample.xyz"),
        dfm_1d_waterlevel_to_mf6_river_stage_dmm_path=Path("sample.xyz"),
        mf6_river2_to_dfm_1d_q_dmm_path=Path("sample.xyz"),
        mf6_drainage_to_dfm_1d_q_dmm_path=Path("sample.xyz"),
        msw_runoff_to_dfm_1d_q_dmm_path=Path("sample.xyz"),
        msw_ponding_to_dfm_2d_dv_dmm_path=Path("sample.xyz"),
        msw_sprinkling_to_dfm_1d_q_dmm_path=Path("sample.xyz"),
        dfm_2d_waterlevels_to_msw_h_dmm_path=Path("sample.xyz"),
        dfm_1d_points_dat_path=Path("sample.xyz"),
        output_config_file=Path("output_config.toml"),
    )

    # sample.xyz is in fact not a real mapping file- it is used here because there are no valid mapping files
    # for this example
    return with_river
