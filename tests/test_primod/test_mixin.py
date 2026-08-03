from imod.mf6 import Modflow6Simulation, StructuredDiscretization
from imod.mf6.mf6_wel_adapter import Mf6Wel
from primod.model_mixin import MetaModMixin
from pytest import fixture


@fixture(scope="function")
def coupling_dict() -> dict[str, str]:
    return {
        "mf6_model": "GWF_1",
        "mf6_recharge_package": "rch_msw",
        "mf6_msw_well_pkg": "wells_msw",
    }


def test_get_mf6_pkgs_for_metaswap__sprinkling(
    coupling_dict: dict[str, str], coupled_mf6_model: Modflow6Simulation
):
    coupling_dicts = [coupling_dict]
    coupling_dicts[0]["msw_model"] = "MSW"
    mf6_dis, mf6_wel = MetaModMixin.get_mf6_pkgs_for_metaswap(
        coupling_dicts, coupled_mf6_model
    )

    assert isinstance(mf6_dis["MSW"], StructuredDiscretization)
    assert isinstance(mf6_wel["MSW"], Mf6Wel)


def test_get_mf6_pkgs_for_metaswap__no_sprinkling(
    coupling_dict: dict[str, str], coupled_mf6_model: Modflow6Simulation
):
    coupling_dict.pop("mf6_msw_well_pkg")
    coupling_dicts = [coupling_dict]
    coupling_dicts[0]["msw_model"] = "MSW"
    mf6_dis, mf6_wel = MetaModMixin.get_mf6_pkgs_for_metaswap(
        coupling_dicts, coupled_mf6_model
    )

    assert isinstance(mf6_dis["MSW"], StructuredDiscretization)
    assert mf6_wel["MSW"] is None
