from imod.mf6 import Modflow6Simulation, StructuredDiscretization
from imod.mf6.mf6_wel_adapter import Mf6Wel
from primod.model_mixin import ModflowMixin
from pytest import fixture


@fixture(scope="function")
def coupling_dict() -> dict[str, str]:
    return {
        "mf6_model": "GWF_1",
        "mf6_recharge_package": "rch_msw",
        "mf6_msw_well_pkg": "wells_msw",
    }


def test_get_mf6_pkgs_with_coupling_dict__sprinkling(
    coupling_dict: dict[str, str], coupled_mf6_model: Modflow6Simulation
):
    mf6_dis, mf6_wel = ModflowMixin.get_mf6_pkgs_with_coupling_dict(
        coupling_dict, coupled_mf6_model
    )

    assert isinstance(mf6_dis, StructuredDiscretization)
    assert isinstance(mf6_wel, Mf6Wel)


def test_get_mf6_pkgs_with_coupling_dict__no_sprinkling(
    coupling_dict: dict[str, str], coupled_mf6_model: Modflow6Simulation
):
    coupling_dict.pop("mf6_msw_well_pkg")
    mf6_dis, mf6_wel = ModflowMixin.get_mf6_pkgs_with_coupling_dict(
        coupling_dict, coupled_mf6_model
    )

    assert isinstance(mf6_dis, StructuredDiscretization)
    assert mf6_wel is None
