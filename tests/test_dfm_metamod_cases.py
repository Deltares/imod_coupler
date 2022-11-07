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
    )
    return with_river
