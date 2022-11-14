from pathlib import Path

import pytest
from hydrolib.core.io.mdu.models import FMModel
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
        mf6_river_pkgkey="Oosterschelde",
        mf6_wel_pkgkey="wells_msw",
        mf6_river_to_dfm_1d_q_dmm_path=Path("A.BAT"),
        dfm_1d_waterlevel_to_mf6_river_stage_dmm_path=Path("b.BAT"),
        mf6_river2_to_dmf_1d_q_dmm_path=Path("C.BAT"),
        mf6_drainage_to_dfm_1d_q_dmm_path=Path("d.BAT"),
        msw_sprink_to_dfm_1d_q_dmm_path=Path("E.BAT"),
        msw_runoff_to_dfm_1d_q_dmm_path=Path("f.BAT"),
        dfm_2d_waterlevels_to_msw_h_dmm_path=Path("G.BAT"),
        dfm_1d_points_dat_path=Path("H.BAT"),
    )
    return with_river
