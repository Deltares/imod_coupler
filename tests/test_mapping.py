import numpy as np
from numpy.testing import assert_almost_equal, assert_array_equal
import pytest
from pytest_cases import parametrize_with_cases

from imod_coupler.utils import create_mapping
from imod import mf6
from imod import msw

from primod.mapping.rch_svat_mapping import RechargeSvatMapping


@parametrize_with_cases(
    "src_idx,tgt_idx,nsrc,ntgt,operator,expected_map_dense,expected_mask",
    prefix="util_",
)
def test_create_mapping(
    src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask
):
    """
    Test create_mapping function. Argument names are equivalent to those in the
    create_mapping function.
    """

    map_out, mask = create_mapping(src_idx, tgt_idx, nsrc, ntgt, operator)

    assert issubclass(map_out.dtype.type, np.floating)
    assert issubclass(mask.dtype.type, np.integer)

    assert map_out.shape == (ntgt, nsrc)
    assert map_out.nnz == len(src_idx)
    assert mask.shape == (ntgt,)

    assert_almost_equal(map_out.toarray(), expected_map_dense)
    assert_array_equal(mask, expected_mask)


@parametrize_with_cases("recharge", prefix="rch", has_tag="succeed")
def test_recharge_mapping(
    recharge: mf6.Recharge, prepared_msw_model: msw.MetaSwapModel
):
    """
    Test Recharge package validation
    """
    _, svat = prepared_msw_model["grid"].generate_index_array()

    rch_svat_mapping = RechargeSvatMapping(svat, recharge)

    assert np.all(rch_svat_mapping.dataset["layer"] == 1)
    assert np.all(rch_svat_mapping.dataset["svat"] == svat)
    assert rch_svat_mapping.dataset["rch_id"].max() == 12
    assert rch_svat_mapping.dataset["rch_active"].sum() == 12


@parametrize_with_cases("recharge", prefix="rch", has_tag="fail")
def test_recharge_mapping_fail(
    recharge: mf6.Recharge, prepared_msw_model: msw.MetaSwapModel
):
    _, svat = prepared_msw_model["grid"].generate_index_array()

    with pytest.raises(ValueError):
        RechargeSvatMapping(svat, recharge)
