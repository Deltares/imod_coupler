import pytest
from imod.mf6 import Modflow6Simulation
from imod.mf6.model_gwf import GroundwaterFlowModel
from imod.msw import MetaSwapModel
from imod.msw.fixed_format import VariableMetaData
from primod import MetaMod, MetaModDriverCoupling
import numpy as np
from imod.msw.meteo_grid import MeteoGridCopy
from pathlib import Path
import pandas as pd
import csv


def case_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw", mf6_wel_package="wells_msw"
    )
    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        coupling_list=[driver_coupling],
    )


def case_no_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    prepared_msw_model.pop("sprinkling")

    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw"
    )
    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        coupling_list=[driver_coupling],
    )


def case_storage_coefficient(
    coupled_mf6_model_storage_coefficient: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw", mf6_wel_package="wells_msw"
    )
    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model_storage_coefficient,
        coupling_list=[driver_coupling],
    )


def case_storage_coefficient_no_sprinkling(
    coupled_mf6_model_storage_coefficient: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    prepared_msw_model.pop("sprinkling")

    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw"
    )
    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model_storage_coefficient,
        coupling_list=[driver_coupling],
    )


def case_inactive_cell(
    coupled_mf6_model_inactive: Modflow6Simulation,
    prepared_msw_model_inactive: MetaSwapModel,
) -> MetaMod:
    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw", mf6_wel_package="wells_msw"
    )
    return MetaMod(
        prepared_msw_model_inactive,
        coupled_mf6_model_inactive,
        coupling_list=[driver_coupling],
    )


def case_multi_model_no_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
    tmp_path_dev: Path,
) -> MetaMod:
    prepared_msw_model.pop("sprinkling")
    partitions_array = coupled_mf6_model["GWF_1"]["dis"]["idomain"].isel(
        layer=0, drop=True
    )

    # Create meteo output directory, write the meteo data, and copy metegrid.
    meteo_output_dir = tmp_path_dev / "metaswap" / "meteo"
    meteo_output_dir.mkdir(exist_ok=True, parents=True)
    prepared_msw_model["meteo_grid"].write(meteo_output_dir)
    del prepared_msw_model["meteo_grid"]
    mete_grid = meteo_output_dir / Path("mete_grid.inp")

    # WORKAROUND: set absolute paths in file mete_grid.inp
    df = pd.read_csv(mete_grid, header=None)
    for row in range(df.shape[0]):
        df[2][row] = str(meteo_output_dir / Path(df[2][row]))
        df[3][row] = str(meteo_output_dir / Path(df[3][row]))
    for col in [2, 3, 4, 5, 6]:
        df.loc[:, col] = '"' + df[col] + '"'
    df.to_csv(
        mete_grid,
        header=False,
        quoting=csv.QUOTE_NONE,
        float_format="%.4f",
        index=False,
    )

    prepared_msw_model["meteo_grid"] = MeteoGridCopy(mete_grid)

    partitions_array = partitions_array.where(partitions_array.x > 300, 0)

    mf6_splitted = coupled_mf6_model.split(partitions_array)
    msw_splitted = prepared_msw_model.split(partitions_array)

    mf6_model_name_list = [
        model_name
        for model_name, model in mf6_splitted.items()
        if isinstance(model, GroundwaterFlowModel)
    ]
    msw_model_name_list = msw_splitted.keys()

    coupling_list = []
    for mf6_model_name, msw_model_name in zip(mf6_model_name_list, msw_model_name_list):
        coupling_list.append(
            MetaModDriverCoupling(
                mf6_model=mf6_model_name,
                msw_model=msw_model_name,
                mf6_recharge_package="rch_msw",
            )
        )

    return MetaMod(msw_splitted, mf6_splitted, coupling_list=coupling_list)


def case_multi_model_no_sprinkling_three_subs(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    prepared_msw_model.pop("sprinkling")
    partitions_array = coupled_mf6_model["GWF_1"]["dis"]["idomain"].isel(
        layer=0, drop=True
    )
    partitions_array = partitions_array.where(partitions_array.y > 100, 2)
    partitions_array = partitions_array.where(partitions_array.y < 300, 0)

    simulation = coupled_mf6_model.split(partitions_array)
    driver_coupling0 = MetaModDriverCoupling(
        mf6_model="GWF_1_0", msw_model="unsa_1", mf6_recharge_package="rch_msw"
    )
    driver_coupling1 = MetaModDriverCoupling(
        mf6_model="GWF_1_1", msw_model="unsa_2", mf6_recharge_package="rch_msw"
    )
    driver_coupling2 = MetaModDriverCoupling(
        mf6_model="GWF_1_2", msw_model="unsa_3", mf6_recharge_package="rch_msw"
    )

    msw_model_dict = {}
    np = int(partitions_array.max().values) + 1
    hdx = 0.5 * partitions_array.dx.values.item()
    hdy = 0.5 * abs(partitions_array.dy.values.item())
    for ip in range(np):
        part_array = partitions_array.where(partitions_array == ip, drop=True)

        xmin = part_array["x"].min().values.item() - hdx
        xmax = part_array["x"].max().values.item() + hdx
        ymin = part_array["y"].min().values.item() - hdy
        ymax = part_array["y"].max().values.item() + hdy

        msw_model_dict[f"unsa_{ip + 1}"] = prepared_msw_model.clip_box(
            x_min=xmin, x_max=xmax, y_min=ymin, y_max=ymax
        )

    return MetaMod(
        msw_model_dict,
        simulation,
        coupling_list=[driver_coupling0, driver_coupling1, driver_coupling2],
    )


def fail_write_inactive_cell(
    coupled_mf6_model_inactive: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    """
    Force an error by having an active MetaSWAP cell in an inactive Modflow 6
    cell during writing.
    """

    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw", mf6_wel_package="wells_msw"
    )
    return MetaMod(
        prepared_msw_model, coupled_mf6_model_inactive, coupling_list=[driver_coupling]
    )


def fail_run_msw_input(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    """
    Force an input error in MetaSWAP by providing an initial condition with
    a value of the wrong type.
    """

    prepared_msw_model["ic"]._metadata_dict["initial_pF"] = VariableMetaData(
        6, None, None, str
    )
    prepared_msw_model["ic"].dataset["initial_pF"] = "a"

    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw", mf6_wel_package="wells_msw"
    )
    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        coupling_list=[driver_coupling],
    )


def fail_run_mf6_input(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    """
    Creates a MetaMod object which will result in a MODFLOW 6 input error.
    """

    coupled_mf6_model["GWF_1"]["npf"]["k"] *= 0.0

    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw", mf6_wel_package="wells_msw"
    )
    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        coupling_list=[driver_coupling],
    )


def cases_metamod_no_sprinkling(
    prepared_msw_model: MetaSwapModel,
    coupled_mf6_model: Modflow6Simulation,
    coupled_mf6_model_storage_coefficient: Modflow6Simulation,
) -> tuple[MetaMod, MetaMod]:
    """
    Two MetaMod objects, both without sprinkling. One with specific storage, one
    with storage coefficient.
    """

    prepared_msw_model.pop("sprinkling")
    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw"
    )

    metamod_ss = MetaMod(prepared_msw_model, coupled_mf6_model, [driver_coupling])

    metamod_sc = MetaMod(
        prepared_msw_model, coupled_mf6_model_storage_coefficient, [driver_coupling]
    )

    return metamod_ss, metamod_sc


def cases_metamod_sprinkling(
    prepared_msw_model: MetaSwapModel,
    coupled_mf6_model: Modflow6Simulation,
    coupled_mf6_model_storage_coefficient: Modflow6Simulation,
) -> tuple[MetaMod, MetaMod]:
    """
    Two MetaMod objects, both with sprinkling. One with specific storage, one
    with storage coefficient.
    """

    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw", mf6_wel_package="wells_msw"
    )

    metamod_ss = MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        [driver_coupling],
    )

    metamod_sc = MetaMod(
        prepared_msw_model,
        coupled_mf6_model_storage_coefficient,
        [driver_coupling],
    )

    return metamod_ss, metamod_sc
