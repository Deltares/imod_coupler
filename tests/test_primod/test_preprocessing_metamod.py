import numpy as np
import pytest
from numpy.testing import assert_equal
from primod import MetaMod, MetaModDriverCoupling
from primod.mapping import (
    NodeSvatMapping,
    RechargeSvatMapping,
    WellSvatMapping,
)

# tomllib part of Python 3.11, else use tomli
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def test_metamod_write(prepared_msw_model, coupled_mf6_model, tmp_path):
    output_dir = tmp_path / "metamod"

    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_wel_package="wells_msw", mf6_recharge_package="rch_msw"
    )
    coupled_models = MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        coupling_list=[driver_coupling],
    )

    coupled_models.write(output_dir, "./modflow6.dll", "./metaswap.dll", "./metaswap")

    # Test metaswap files written
    assert len(list(output_dir.rglob(r"*.inp"))) == 16
    assert len(list(output_dir.rglob(r"*.asc"))) == 426
    # Test exchanges written
    assert len(list(output_dir.rglob(r"*.dxc"))) == 3
    assert len(list(output_dir.rglob(r"*.toml"))) == 1
    # Test mf6 files written
    assert len(list(output_dir.rglob(r"*.bin"))) == 216
    assert len(list(output_dir.rglob(r"*.nam"))) == 2
    assert len(list(output_dir.rglob(r"*.chd"))) == 1
    assert len(list(output_dir.rglob(r"*.rch"))) == 1
    assert len(list(output_dir.rglob(r"*.wel"))) == 1


def test_metamod_write_exchange(
    prepared_msw_model, coupled_mf6_model, fixed_format_parser, tmp_path
):
    output_dir = tmp_path
    output_dir.mkdir(exist_ok=True, parents=True)

    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_wel_package="wells_msw", mf6_recharge_package="rch_msw"
    )
    coupled_models = MetaMod(
        prepared_msw_model, coupled_mf6_model, coupling_list=[driver_coupling]
    )

    coupled_models.write_exchanges(
        output_dir,
    )

    exchange_dir = output_dir / "exchanges"
    nodes_dxc = fixed_format_parser(
        exchange_dir / NodeSvatMapping._file_name,
        NodeSvatMapping._metadata_dict,
    )

    rch_dxc = fixed_format_parser(
        exchange_dir / RechargeSvatMapping._file_name,
        RechargeSvatMapping._metadata_dict,
    )

    wel_dxc = fixed_format_parser(
        exchange_dir / WellSvatMapping._file_name,
        WellSvatMapping._metadata_dict,
    )

    assert_equal(
        nodes_dxc["mod_id"],
        np.array([2, 3, 4, 5, 12, 13, 14, 15, 2, 3, 4, 5, 7, 8, 9, 10]),
    )
    assert_equal(
        nodes_dxc["svat"],
        np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]),
    )
    assert_equal(
        nodes_dxc["layer"], np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    )

    assert_equal(
        rch_dxc["rch_id"], np.array([1, 2, 3, 4, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8])
    )
    assert_equal(
        rch_dxc["svat"],
        np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]),
    )
    assert_equal(
        rch_dxc["layer"], np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    )

    assert_equal(
        wel_dxc["wel_id"],
        np.array([2, 3, 4, 5, 12, 13, 14, 15, 2, 3, 4, 5, 7, 8, 9, 10]),
    )
    assert_equal(
        wel_dxc["svat"],
        np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]),
    )
    assert_equal(
        wel_dxc["layer"], np.array([3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3])
    )


def test_metamod_write_exchange_no_sprinkling(
    prepared_msw_model, coupled_mf6_model, fixed_format_parser, tmp_path
):
    # Remove sprinkling package
    prepared_msw_model.pop("sprinkling")

    output_dir = tmp_path
    output_dir.mkdir(exist_ok=True, parents=True)

    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw"
    )

    coupled_models = MetaMod(
        prepared_msw_model, coupled_mf6_model, coupling_list=[driver_coupling]
    )

    coupled_models.write_exchanges(
        output_dir,
    )

    exchange_dir = output_dir / "exchanges"
    nodes_dxc = fixed_format_parser(
        exchange_dir / NodeSvatMapping._file_name,
        NodeSvatMapping._metadata_dict,
    )

    rch_dxc = fixed_format_parser(
        exchange_dir / RechargeSvatMapping._file_name,
        RechargeSvatMapping._metadata_dict,
    )

    well_dxc_written = (exchange_dir / WellSvatMapping._file_name).exists()

    assert well_dxc_written is False

    assert_equal(
        nodes_dxc["mod_id"],
        np.array([2, 3, 4, 5, 12, 13, 14, 15, 2, 3, 4, 5, 7, 8, 9, 10]),
    )
    assert_equal(
        nodes_dxc["svat"],
        np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]),
    )
    assert_equal(
        nodes_dxc["layer"], np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    )

    assert_equal(
        rch_dxc["rch_id"], np.array([1, 2, 3, 4, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8])
    )
    assert_equal(
        rch_dxc["svat"],
        np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]),
    )
    assert_equal(
        rch_dxc["layer"], np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    )


def test_metamod_write_toml(prepared_msw_model, coupled_mf6_model, tmp_path):
    output_dir = tmp_path
    output_dir.mkdir(exist_ok=True, parents=True)

    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_wel_package="wells_msw", mf6_recharge_package="rch_msw"
    )
    coupled_models = MetaMod(
        prepared_msw_model, coupled_mf6_model, coupling_list=[driver_coupling]
    )

    coupling_dict = {
        "mf6_model": "GWF_1",
        "mf6_msw_node_map": "./exchanges/nodenr2svat.dxc",
        "mf6_msw_recharge_map": "./exchanges/rchindex2svat.dxc",
        "mf6_msw_recharge_pkg": "rch_msw",
        "mf6_msw_well_pkg": "wells_msw",
        "mf6_msw_sprinkling_map_groundwater": "./exchanges/wellindex2svat.dxc",
    }

    coupled_models.write_toml(
        output_dir, "./modflow6.dll", "./metaswap.dll", "./metaswap", coupling_dict
    )

    with open(output_dir / "imod_coupler.toml", mode="rb") as f:
        toml_dict = tomllib.load(f)

    dict_expected = {
        "timing": False,
        "log_level": "INFO",
        "driver_type": "metamod",
        "driver": {
            "kernels": {
                "modflow6": {
                    "dll": "./modflow6.dll",
                    "work_dir": f".\\{coupled_models._modflow6_model_dir}",
                },
                "metaswap": {
                    "dll": "./metaswap.dll",
                    "work_dir": f".\\{coupled_models._metaswap_model_dir}",
                    "dll_dep_dir": "./metaswap",
                },
            },
            "coupling": [coupling_dict],
        },
    }

    assert toml_dict == dict_expected


def test_metamod_get_coupling_dict(prepared_msw_model, coupled_mf6_model, tmp_path):
    output_dir = tmp_path / "exchanges"

    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_wel_package="wells_msw", mf6_recharge_package="rch_msw"
    )
    coupled_models = MetaMod(
        prepared_msw_model, coupled_mf6_model, coupling_list=[driver_coupling]
    )

    dict_expected = {
        "mf6_model": "GWF_1",
        "mf6_msw_node_map": "./exchanges/nodenr2svat.dxc",
        "mf6_msw_recharge_map": "./exchanges/rchindex2svat.dxc",
        "mf6_msw_recharge_pkg": "rch_msw",
        "mf6_msw_well_pkg": "wells_msw",
        "mf6_msw_sprinkling_map_groundwater": "./exchanges/wellindex2svat.dxc",
    }

    coupled_dict = coupled_models.write_exchanges(
        output_dir,
    )

    assert dict_expected == coupled_dict


def test_metamod_get_coupling_dict_no_sprinkling(
    prepared_msw_model, coupled_mf6_model, tmp_path
):
    output_dir = tmp_path / "exchanges"

    # Remove sprinkling package
    prepared_msw_model.pop("sprinkling")

    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw"
    )
    coupled_models = MetaMod(
        prepared_msw_model, coupled_mf6_model, coupling_list=[driver_coupling]
    )

    dict_expected = {
        "mf6_model": "GWF_1",
        "mf6_msw_node_map": "./exchanges/nodenr2svat.dxc",
        "mf6_msw_recharge_map": "./exchanges/rchindex2svat.dxc",
        "mf6_msw_recharge_pkg": "rch_msw",
    }

    coupled_dict = coupled_models.write_exchanges(
        output_dir,
    )

    assert dict_expected == coupled_dict


def test_metamod_init_no_sprinkling_fail(
    prepared_msw_model, coupled_mf6_model, tmp_path
):
    # Remove sprinkling package
    prepared_msw_model.pop("sprinkling")
    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_wel_package="wells_msw", mf6_recharge_package="rch_msw"
    )

    output_dir = tmp_path / "exchanges"
    with pytest.raises(ValueError):
        metamod = MetaMod(
            prepared_msw_model, coupled_mf6_model, coupling_list=[driver_coupling]
        )
        metamod.write_exchanges(output_dir)


def test_metamod_init_no_mf6_well_fail(prepared_msw_model, coupled_mf6_model, tmp_path):
    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1",
        mf6_wel_package="does not exist",
        mf6_recharge_package="rch_msw",
    )

    output_dir = tmp_path / "exchanges"
    with pytest.raises(ValueError):
        metamod = MetaMod(
            prepared_msw_model, coupled_mf6_model, coupling_list=[driver_coupling]
        )
        metamod.write_exchanges(output_dir)


def test_metamod_init_no_mf6_well_fail2(
    prepared_msw_model, coupled_mf6_model, tmp_path
):
    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw"
    )
    output_dir = tmp_path / "exchanges"
    with pytest.raises(ValueError):
        metamod = MetaMod(
            prepared_msw_model, coupled_mf6_model, coupling_list=[driver_coupling]
        )
        metamod.write_exchanges(output_dir)


def test_metamod_init_no_mf6_rch_fail(prepared_msw_model, coupled_mf6_model, tmp_path):
    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1",
        mf6_recharge_package="does_not_exist",
        mf6_wel_package="wells_msw",
    )
    output_dir = tmp_path / "exchanges"
    with pytest.raises(ValueError):
        metamod = MetaMod(
            prepared_msw_model,
            coupled_mf6_model,
            coupling_list=[driver_coupling],
        )
        metamod.write_exchanges(output_dir)
