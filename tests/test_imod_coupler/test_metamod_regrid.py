from collections.abc import Callable
from pathlib import Path

import xarray as xr
from primod.metamod import MetaMod
from pytest_cases import parametrize_with_cases


@parametrize_with_cases("metamod_regrid")
def test_metamod_original(
    tmp_path_dev: Path,
    metamod_regrid: MetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    run_coupler_function: Callable[[Path], None],
) -> None:
    """
    Test if coupled models run with the iMOD Coupler development version.
    """
    metamod_regrid.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    run_coupler_function(tmp_path_dev / metamod_regrid._toml_name)

    hds = metamod_regrid.mf6_simulation.open_head()
    print(hds.sel(layer=2).isel(time=126).values)
    pass


@parametrize_with_cases("metamod_regrid")
def test_metamod_regrid(
    tmp_path_dev: Path,
    metamod_regrid: MetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    run_coupler_function: Callable[[Path], None],
) -> None:
    """
    Test if coupled models run with the iMOD Coupler development version.
    """

    x = [100.0, 200.0, 300.0, 400.0, 500.0]
    y = [300.0, 250.0, 200.0, 150.0, 100.0]
    dx = 50.0
    dy = -50.0
    layer = [1, 2, 3]

    new_grid = xr.DataArray(
        1,
        dims=("layer", "y", "x"),
        coords={"layer": layer, "y": y, "x": x, "dx": dx, "dy": dy},
    )

    regridded_metamod = metamod_regrid.regrid_like(new_grid)

    regridded_metamod.msw_model.simulation_settings["unsa_svat_path"] = (
        metamod_regrid.msw_model.simulation_settings["unsa_svat_path"]
    )
    regridded_metamod.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    run_coupler_function(tmp_path_dev / regridded_metamod._toml_name)

    hds = regridded_metamod.mf6_simulation.open_head()
    print(hds.sel(layer=2).isel(time=126).values)
    pass
