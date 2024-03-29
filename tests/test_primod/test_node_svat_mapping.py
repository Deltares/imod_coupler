import tempfile
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from imod import mf6
from numpy.testing import assert_equal
from primod import mapping


def test_simple_model(fixed_format_parser):
    x = [1.0, 2.0, 3.0]
    y = [3.0, 2.0, 1.0]
    subunit = [0, 1]
    dx = 1.0
    dy = -1.0
    # fmt: off
    svat = xr.DataArray(
        np.array(
            [
                [[0, 1, 0],
                 [0, 0, 0],
                 [0, 2, 0]],

                [[0, 3, 0],
                 [0, 4, 0],
                 [0, 0, 0]],
            ]
        ),
        dims=("subunit", "y", "x"),
        coords={"subunit": subunit, "y": y, "x": x, "dx": dx, "dy": dy}
    )
    # fmt: on
    index = (svat != 0).to_numpy().ravel()

    like = xr.full_like(svat.sel(subunit=1, drop=True), 1.0, dtype=float).expand_dims(
        layer=[1, 2, 3]
    )

    dis = mf6.StructuredDiscretization(
        top=1.0,
        bottom=xr.full_like(like, 0.0),
        idomain=xr.full_like(like, 1, dtype=int),
    )

    grid_data = mapping.node_svat_mapping.NodeSvatMapping(svat, dis, index=index)

    with tempfile.TemporaryDirectory() as output_dir:
        output_dir = Path(output_dir)
        grid_data.write(output_dir)

        results = fixed_format_parser(
            output_dir / mapping.node_svat_mapping.NodeSvatMapping._file_name,
            mapping.node_svat_mapping.NodeSvatMapping._metadata_dict,
        )

    assert_equal(results["mod_id"], np.array([2, 8, 2, 5]))
    assert_equal(results["svat"], np.array([1, 2, 3, 4]))
    assert_equal(results["layer"], np.array([1, 1, 1, 1]))


def test_simple_model_1_subunit(fixed_format_parser):
    x = [1.0, 2.0, 3.0]
    y = [3.0, 2.0, 1.0]
    subunit = [0]
    dx = 1.0
    dy = -1.0
    # fmt: off
    svat = xr.DataArray(
        np.array(
            [
                [[0, 1, 0],
                 [0, 0, 0],
                 [0, 2, 0]],
            ]
        ),
        dims=("subunit", "y", "x"),
        coords={"subunit": subunit, "y": y, "x": x, "dx": dx, "dy": dy}
    )
    # fmt: on
    index = (svat != 0).to_numpy().ravel()

    like = xr.full_like(svat.sel(subunit=0, drop=True), 1.0, dtype=float).expand_dims(
        layer=[1, 2, 3]
    )

    dis = mf6.StructuredDiscretization(
        top=1.0,
        bottom=xr.full_like(like, 0.0),
        idomain=xr.full_like(like, 1, dtype=int),
    )

    grid_data = mapping.node_svat_mapping.NodeSvatMapping(svat, dis, index=index)

    with tempfile.TemporaryDirectory() as output_dir:
        output_dir = Path(output_dir)
        grid_data.write(output_dir)

        results = fixed_format_parser(
            output_dir / mapping.node_svat_mapping.NodeSvatMapping._file_name,
            mapping.node_svat_mapping.NodeSvatMapping._metadata_dict,
        )

    assert_equal(results["mod_id"], np.array([2, 8]))
    assert_equal(results["svat"], np.array([1, 2]))
    assert_equal(results["layer"], np.array([1, 1]))


def test_inactive_idomain_in_svat():
    x = [1.0, 2.0, 3.0]
    y = [3.0, 2.0, 1.0]
    subunit = [0, 1]
    dx = 1.0
    dy = -1.0
    # fmt: off
    svat = xr.DataArray(
        np.array(
            [
                [[0, 1, 0],
                 [0, 0, 0],
                 [0, 2, 0]],

                [[0, 3, 0],
                 [0, 4, 0],
                 [0, 0, 0]],
            ]
        ),
        dims=("subunit", "y", "x"),
        coords={"subunit": subunit, "y": y, "x": x, "dx": dx, "dy": dy}
    )
    # fmt: on

    like = xr.full_like(svat.sel(subunit=1, drop=True), 1.0, dtype=float).expand_dims(
        layer=[1, 2, 3]
    )

    idomain = xr.full_like(like, 1, dtype=int)
    idomain[:, 1, :] = 0

    dis = mf6.StructuredDiscretization(
        top=1.0,
        bottom=xr.full_like(like, 0.0),
        idomain=idomain,
    )
    index = (svat != 0).to_numpy().ravel()

    with pytest.raises(ValueError):
        mapping.node_svat_mapping.NodeSvatMapping(svat, dis, index=index)
