from typing import Tuple

import xarray as xr
from imod.couplers.metamod import MetaMod
from imod.mf6 import Modflow6Simulation
from imod.msw import MetaSwapModel
from imod.msw.fixed_format import VariableMetaData


def case_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )


def case_no_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    prepared_msw_model.pop("sprinkling")

    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey=None,
    )


def case_storage_coefficient(
    coupled_mf6_model_storage_coefficient: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model_storage_coefficient,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )


def case_storage_coefficient_no_sprinkling(
    coupled_mf6_model_storage_coefficient: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    prepared_msw_model.pop("sprinkling")

    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model_storage_coefficient,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey=None,
    )


def case_inactive_cell(
    coupled_mf6_model_inactive: Modflow6Simulation,
    prepared_msw_model_inactive: MetaSwapModel,
) -> MetaMod:
    return MetaMod(
        prepared_msw_model_inactive,
        coupled_mf6_model_inactive,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )


def fail_write_inactive_cell(
    coupled_mf6_model_inactive: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    """
    Force an error by having an active MetaSWAP cell in an inactive Modflow 6
    cell during writing.
    """

    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model_inactive,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )


def fail_run_msw_input(
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    """
    Force an error by having an active MetaSWAP cell in an inactive Modflow 6
    cell during writing.
    """

    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model_inactive,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
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

    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )


def fail_run_mf6_input(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    """
    Creates a MetaMod object which will result in a MODFLOW 6 input error.
    """

    coupled_mf6_model["GWF_1"]["npf"]["k"] *= 0.0

    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )


def cases_no_sprinkling(
    prepared_msw_model: MetaSwapModel,
    coupled_mf6_model: Modflow6Simulation,
    coupled_mf6_model_storage_coefficient: Modflow6Simulation,
) -> Tuple[MetaMod, MetaMod]:
    """
    Two MetaMod objects, both without sprinkling. One with specific storage, one
    with storage coefficient.
    """

    prepared_msw_model.pop("sprinkling")
    kwargs = dict(
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey=None,
    )

    metamod_ss = MetaMod(prepared_msw_model, coupled_mf6_model, **kwargs)

    metamod_sc = MetaMod(
        prepared_msw_model, coupled_mf6_model_storage_coefficient, **kwargs
    )

    return metamod_ss, metamod_sc


def cases_sprinkling(
    prepared_msw_model: MetaSwapModel,
    coupled_mf6_model: Modflow6Simulation,
    coupled_mf6_model_storage_coefficient: Modflow6Simulation,
) -> Tuple[MetaMod, MetaMod]:
    """
    Two MetaMod objects, both with sprinkling. One with specific storage, one
    with storage coefficient.
    """

    kwargs = dict(
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )

    metamod_ss = MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        **kwargs,
    )

    metamod_sc = MetaMod(
        prepared_msw_model,
        coupled_mf6_model_storage_coefficient,
        **kwargs,
    )

    return metamod_ss, metamod_sc
