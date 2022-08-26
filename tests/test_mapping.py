#%% Import

import numpy as np
from numpy.testing import assert_almost_equal, assert_array_equal
from pytest_cases import parametrize_with_cases

from imod_coupler.utils import create_mapping


#%% Test
@parametrize_with_cases(
    "src_idx,tgt_idx,nsrc,ntgt,operator,expected_map_dense,expected_mask"
)
def test_create_mapping(
    src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask
):
    map_out, mask = create_mapping(src_idx, tgt_idx, nsrc, ntgt, operator)

    assert issubclass(map_out.dtype.type, np.floating)
    assert issubclass(mask.dtype.type, np.integer)

    assert map_out.shape == (ntgt, nsrc)
    assert map_out.nnz == len(src_idx)
    assert mask.shape == (ntgt,)

    assert_almost_equal(map_out.toarray(), expected_map_dense)
    assert_array_equal(mask, expected_mask)
