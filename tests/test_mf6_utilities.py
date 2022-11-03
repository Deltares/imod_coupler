from xmipy import XmiWrapper
import tempfile
from imod import mf6
from pathlib import Path
from imod_coupler.drivers.dfm_metamod.mf6_utilities import MF6Utilities


def test_mf6_get_flowmodel(
    mf6_model_with_river: mf6.Modflow6Simulation, modflow_dll_regression: Path
):

    flowmodels = MF6Utilities.get_flow_models(mf6_model_with_river)
    assert len(flowmodels) == 1
    assert isinstance(flowmodels[0], mf6.GroundwaterFlowModel)


def test_mf6_get_package_keys(
    mf6_model_with_river: mf6.Modflow6Simulation, modflow_dll_regression: Path
):

    flowmodel = MF6Utilities.get_flow_models(mf6_model_with_river)[0]
    river_packs = MF6Utilities.get_modflow_package_keys(flowmodel, mf6.River)
    assert len(river_packs) == 1
    assert river_packs[0] == "Oosterschelde"
