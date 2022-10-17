import os
import shutil
import tempfile

from create_dflowfm_model import create_dflowfm_model, run_dflowfm_model
from create_discretization import create_discretization
from create_metaswap_model import create_metaswap_model
from create_modflow_model import create_modflow_model

# before running this file, copy and unpack N:\Deltabox\Postbox\Slooten, Luit Jan\voor_lumbricus\dflowfm_dll.7z
# into ./dflowfm_dll


workdir = tempfile.mkdtemp()
try:
    idomain, top, bottom, times = create_discretization()
    mf6model = create_modflow_model(
        idomain, top, bottom, times, workdir + os.sep + "mf6"
    )
    swmodel = create_metaswap_model(
        idomain, top, bottom, times, workdir + os.sep + "msw"
    )
    dfmmodel = create_dflowfm_model(idomain, top, times, workdir + os.sep + "dfm")
    run_dflowfm_model(dfmmodel, workdir + os.sep + "dfm")


except:
    print("An exception occurred")
finally:
    shutil.rmtree(workdir)
    # directory cannot be removed because dfm\\DFM_OUTPUT_model\\model_map.nc is in use.
    # that could be a defect.
