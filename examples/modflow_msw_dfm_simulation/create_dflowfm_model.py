import os
import shutil
from distutils.dir_util import copy_tree
from pathlib import Path

import matplotlib.pyplot as plt
from bmi.wrapper import BMIWrapper
from hydrolib.core.io.bc.models import Astronomic, ForcingModel, QuantityUnitPair
from hydrolib.core.io.ext.models import Boundary, ExtModel
from hydrolib.core.io.inifield.models import (
    DataFileType,
    IniFieldModel,
    InitialField,
    InterpolationMethod,
)
from hydrolib.core.io.mdu.models import FMModel
from hydrolib.core.io.xyz.models import XYZModel, XYZPoint


def create_dflowfm_model(idomain, top, times, workdir):

    x = idomain.coords["x"].values
    y = idomain.coords["y"].values
    dx = idomain.coords["dx"].values
    dy = idomain.coords["dy"].values

    # Initialize model dir
    modelname = "model"
    if Path(workdir).exists():
        shutil.rmtree(workdir)

    os.mkdir(workdir)
    os.chdir(workdir)

    # Create new model object
    fm_model = FMModel()
    fm_model.filepath = Path(workdir + os.sep + f"{modelname}.mdu")

    network = fm_model.geometry.netfile.network
   
    extent = (x.min(), y.min(), x.max(), y.max())
    print(f"extent {extent}")
    network.mesh2d_create_rectilinear_within_extent(extent=extent, dx=dx, dy=-dy)

    # Create bed level
    delta_x = (x.max() - x.min()) / 100
    delta_y = (y.max() - y.min()) / 100
    xyz_model = XYZModel(points=[])
    xyz_model.points = [
        XYZPoint(x=x.min() + delta_x, y=y.min() + delta_y, z=top),
        XYZPoint(x=x.min() + delta_x, y=y.max() - delta_y, z=top),
        XYZPoint(x=x.max() - delta_x, y=y.min() + delta_y, z=top),
        XYZPoint(x=x.max() - delta_x, y=y.max() - delta_y, z=top),
    ]
    xyz_model.save()
    bed_level = InitialField(
        quantity="bedlevel",
        datafile=xyz_model.filepath,
        datafiletype=DataFileType.sample,
        interpolationmethod=InterpolationMethod.triangulation,
    )
    fm_model.geometry.inifieldfile = IniFieldModel(initial=[bed_level])

    # Create boundary
    forcing_1 = Astronomic(
        name="Boundary01_0001",
        quantityunitpair=[
            QuantityUnitPair(quantity="astronomic component", unit="-"),
            QuantityUnitPair(quantity="waterlevelbnd amplitude", unit="m"),
            QuantityUnitPair(quantity="waterlevelbnd phase", unit="deg"),
        ],
        datablock=[
            ["A0", "0", "0"],
            ["M2", "0", "0"],
        ],
    )
    forcing_2 = Astronomic(
        name="Boundary01_0002",
        quantityunitpair=[
            QuantityUnitPair(quantity="astronomic component", unit="-"),
            QuantityUnitPair(quantity="waterlevelbnd amplitude", unit="m"),
            QuantityUnitPair(quantity="waterlevelbnd phase", unit="deg"),
        ],
        datablock=[
            ["A0", "0", "0"],
            ["M2", "0", "0"],
        ],
    )
    forcing_model = ForcingModel(forcing=[forcing_1, forcing_2])
    forcing_model.save(recurse=True)
    boundary = Boundary(
        quantity="waterlevelbnd",
        locationfile="Boundary01.pli",
        forcingfile=forcing_model.filepath,
    )
    external_forcing = ExtModel(boundary=[boundary])
    fm_model.external_forcing.extforcefilenew = external_forcing

    # Save model
    fm_model.save(recurse=True)
    return fm_model


def run_dflowfm_model(fm_model, workdir):

    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Add dflowfm dll folder to PATH so that it can be found by the BMIWrapper
    os.environ["PATH"] = (
        script_dir + os.sep + "dflowfm_dll" + os.pathsep + os.environ["PATH"]
    )

    # We workaround
    # - https://github.com/Deltares/HYDROLIB-core/issues/295 and
    # - https://github.com/Deltares/HYDROLIB-core/issues/290
    # by creating these files ourselves and then copying them

    inifiles_dir = script_dir + os.sep + "initial_dflowfm_files"
    copy_tree(inifiles_dir, workdir)

    # Initialize the BMI Wrapper
    with BMIWrapper(
        engine="dflowfm", configfile=os.path.abspath(fm_model.filepath)
    ) as dflowfm:
        dflowfm.initialize()

        # Time loop
        index_timestep = 0
        while dflowfm.get_current_time() < dflowfm.get_end_time():
            dflowfm.update()
            if index_timestep == 10 and False:
                x = dflowfm.get_var("xz")
                y = dflowfm.get_var("yz")
                water_depth = dflowfm.get_var("hs")
                fig, ax = plt.subplots()
                sc = ax.scatter(x, y, c=water_depth)
                fig.colorbar(sc)
                plt.show()

            index_timestep += 1

        # Finalize
        dflowfm.finalize()
