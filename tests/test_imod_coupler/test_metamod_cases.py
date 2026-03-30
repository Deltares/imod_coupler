import pytest
from imod.mf6 import Modflow6Simulation
from imod.msw import MetaSwapModel
from imod.msw.fixed_format import VariableMetaData
from primod import MetaMod, MetaModDriverCoupling
from imod.msw.meteo_grid import MeteoGridCopy
from pathlib import Path
from test_utilities import write_mete_grid_inp_abs_path, get_mf6_gwf_model_names


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


def case_multi_model_no_sprinkling_two_subdomains(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
    tmp_path_dev: Path,
) -> MetaMod:

    # Remove the sprinkling package
    prepared_msw_model.pop("sprinkling")

    # Create meteo output directory, write the meteo data
    meteo_output_dir = tmp_path_dev / "metaswap" / "meteo"
    meteo_output_dir.mkdir(exist_ok=True, parents=True)
    prepared_msw_model["meteo_grid"].write(meteo_output_dir)
    mete_grid = meteo_output_dir / Path("mete_grid.inp")

    # WORKAROUND: set absolute paths in mete_grid.inp
    write_mete_grid_inp_abs_path(meteo_output_dir, mete_grid)

    # Set MeteGridCopy instance
    del prepared_msw_model["meteo_grid"]
    prepared_msw_model["meteo_grid"] = MeteoGridCopy(mete_grid)

    # Set the partions array
    partitions_array = coupled_mf6_model["GWF_1"]["dis"]["idomain"].isel(
        layer=0, drop=True
    )
    partitions_array = partitions_array.where(partitions_array.x > 300, 0)

    # Split the MetaSWAP and MODFLOW 6 models
    mf6_splitted = coupled_mf6_model.split(partitions_array)
    msw_splitted = prepared_msw_model.split(partitions_array)

    # Get the submodel names
    mf6_model_name_list = get_mf6_gwf_model_names(mf6_splitted)
    msw_model_name_list = msw_splitted.keys()

    # Generate the couplings
    coupling_list = []
    for mf6_model_name, msw_model_name in zip(mf6_model_name_list, msw_model_name_list):
        coupling_list.append(
            MetaModDriverCoupling(
                mf6_model=mf6_model_name,
                msw_model=msw_model_name,
                mf6_recharge_package="rch_msw",
            )
        )

    # Couple MetaSWAP and MODFLOW 6
    return MetaMod(msw_splitted, mf6_splitted, coupling_list=coupling_list)


def case_multi_model_no_sprinkling_three_subdomains(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
    tmp_path_dev: Path,
) -> MetaMod:

    # Remove the sprinkling package
    prepared_msw_model.pop("sprinkling")

    # Create meteo output directory, write the meteo data
    meteo_output_dir = tmp_path_dev / "metaswap" / "meteo"
    meteo_output_dir.mkdir(exist_ok=True, parents=True)
    prepared_msw_model["meteo_grid"].write(meteo_output_dir)
    mete_grid = meteo_output_dir / Path("mete_grid.inp")

    # WORKAROUND: set absolute paths in mete_grid.inp
    write_mete_grid_inp_abs_path(meteo_output_dir, mete_grid)

    # Set MeteGridCopy instance
    del prepared_msw_model["meteo_grid"]
    prepared_msw_model["meteo_grid"] = MeteoGridCopy(mete_grid)

    # Set the partions array
    partitions_array = coupled_mf6_model["GWF_1"]["dis"]["idomain"].isel(
        layer=0, drop=True
    )
    partitions_array = partitions_array.where(partitions_array.y > 100, 2)
    partitions_array = partitions_array.where(partitions_array.y < 300, 0)

    # Split the MetaSWAP and MODFLOW 6 models
    mf6_splitted = coupled_mf6_model.split(partitions_array)
    msw_splitted = prepared_msw_model.split(partitions_array)

    # Get the submodel names
    mf6_model_name_list = get_mf6_gwf_model_names(mf6_splitted)
    msw_model_name_list = msw_splitted.keys()

    # Generate the couplings
    coupling_list = []
    for mf6_model_name, msw_model_name in zip(mf6_model_name_list, msw_model_name_list):
        coupling_list.append(
            MetaModDriverCoupling(
                mf6_model=mf6_model_name,
                msw_model=msw_model_name,
                mf6_recharge_package="rch_msw",
            )
        )

    # Couple MetaSWAP and MODFLOW 6
    return MetaMod(msw_splitted, mf6_splitted, coupling_list=coupling_list)


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
