import pytest
from imod.mf6 import Modflow6Simulation
from imod.msw import MetaSwapModel
from imod.msw.fixed_format import VariableMetaData
from primod import MetaMod, MetaModDriverCoupling


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


@pytest.mark.skip("for now we cant deal with multiple well packages")
def case_multi_model_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    partitions_array = coupled_mf6_model["GWF_1"]["dis"]["idomain"].isel(
        layer=0, drop=True
    )
    partitions_array = partitions_array.where(partitions_array.x > 300, 0)
    simulation = coupled_mf6_model.split(partitions_array)
    driver_coupling0 = MetaModDriverCoupling(
        mf6_model="GWF_1_0", mf6_recharge_package="rch_msw", mf6_wel_package="wells_msw"
    )
    driver_coupling1 = MetaModDriverCoupling(
        mf6_model="GWF_1_1", mf6_recharge_package="rch_msw", mf6_wel_package="wells_msw"
    )
    return MetaMod(
        prepared_msw_model,
        simulation,
        coupling_list=[driver_coupling0, driver_coupling1],
    )


def case_multi_model_no_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    prepared_msw_model.pop("sprinkling")
    partitions_array = coupled_mf6_model["GWF_1"]["dis"]["idomain"].isel(
        layer=0, drop=True
    )
    partitions_array = partitions_array.where(partitions_array.x > 300, 0)
    simulation = coupled_mf6_model.split(partitions_array)
    driver_coupling0 = MetaModDriverCoupling(
        mf6_model="GWF_1_0", mf6_recharge_package="rch_msw"
    )
    driver_coupling1 = MetaModDriverCoupling(
        mf6_model="GWF_1_1", mf6_recharge_package="rch_msw"
    )
    return MetaMod(
        prepared_msw_model,
        simulation,
        coupling_list=[driver_coupling0, driver_coupling1],
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
