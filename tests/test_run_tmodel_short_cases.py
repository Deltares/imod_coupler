from typing import Set


def case_skiptest_skip_2d_coupling() -> Set[str]:
    return {"msw_ponding_to_dfm_2d_dv_dmm", "dfm_2d_waterlevels_to_msw_h_dmm"}


def case_skiptest_skip_river2_drain() -> Set[str]:
    return {"mf6_river2_to_dfm_1d_q_dmm", "mf6_drainage_to_dfm_1d_q_dmm"}


def case_skiptest_skip_sprinkling_and_drain() -> Set[str]:
    return {"msw_sprinkling_to_dfm_1d_q_dmm", "mf6_drainage_to_dfm_1d_q_dmm"}


def case_skiptest_skip_all_dflow() -> Set[str]:
    return {
        "msw_ponding_to_dfm_2d_dv_dmm",
        "dfm_2d_waterlevels_to_msw_h_dmm",
        "mf6_river2_to_dfm_1d_q_dmm",
        "mf6_drainage_to_dfm_1d_q_dmm",
        "msw_sprinkling_to_dfm_1d_q_dmm",
        "msw_runoff_to_dfm_1d_q_dmm",
        "mf6_river_to_dfm_1d_q_dmm",
        "dfm_1d_waterlevel_to_mf6_river_stage_dmm",
    }
