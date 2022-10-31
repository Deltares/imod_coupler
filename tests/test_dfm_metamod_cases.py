import pytest
from imod_coupler.drivers.dfm_metamod.dfm_metamod_model import DfmMetaModModel
from imod.mf6 import Modflow6Simulation
from imod.msw import MetaSwapModel
from hydrolib.core.io.mdu.models import FMModel

''' 
this file contains testcases for the dfm_metamod coupling.
'''

def case_default(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
    prepared_dflowfm_model: FMModel,
)-> DfmMetaModModel:

    default = DfmMetaModModel(
        prepared_msw_model,
        coupled_mf6_model,
        prepared_dflowfm_model, 
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )
    return default
