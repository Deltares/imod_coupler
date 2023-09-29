from pathlib import Path

import numpy as np

from imod_coupler.kernelwrappers.swap_wrapper import SwapWrapper


def example_swap_get_recharge(
    swap_work_dir: Path,
    swap_dll_devel: Path,
) -> None:
    """
    For example, swap_work_dir contains a SWAP model that should contain 10
    columns.
    """

    swap_wrapper = SwapWrapper(
        lib_path=swap_dll_devel,
        working_directory=swap_work_dir,
    )
    swap_wrapper.initialize()
    swap_recharge = swap_wrapper.get_volume_ptr()
    assert swap_recharge.size == 10
    assert swap_recharge.dtype == np.float64

    swap_wrapper.prepare_time_step(1.0)  # 1 day
    swap_wrapper.finalize_time_step()
    # Test whether the computed recharge equals 0.001 m/d
    assert np.allclose(swap_recharge, 0.001)
