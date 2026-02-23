from collections import ChainMap
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


def get_coupled_modflow_metaswap_nodes(
    mf6_msw_node_map: Path,
    mf6_msw_recharge_map: Path,
    msw_workdir: Path,
    mf6_msw_sprinkling_map_groundwater: Path | None,
) -> dict[str, NDArray[np.int32]]:
    def svats2index(
        svat: NDArray[np.int32], svat_layer: NDArray[np.int32]
    ) -> NDArray[np.int32]:
        return np.array(
            [svat_lookup[svat[ii], svat_layer[ii]] for ii in range(len(svat))],
            dtype=np.int32,
        )

    # create a lookup, with the svat tuples (id, lay) as keys and the
    # metaswap internal indexes as values
    svat_lookup: dict[tuple[np.int32, np.int32], int] = {}
    msw_mod2svat_file = msw_workdir / "mod2svat.inp"
    if msw_mod2svat_file.is_file():
        svat_data: NDArray[np.int32] = np.loadtxt(
            msw_mod2svat_file, dtype=np.int32, ndmin=2
        )
        svat_id = svat_data[:, 1]
        svat_lay = svat_data[:, 2]
        for vi in range(svat_id.size):
            svat_lookup[(svat_id[vi], svat_lay[vi])] = vi
    else:
        raise ValueError(f"Can't find {msw_mod2svat_file}.")
    coupling_tables: dict[str, NDArray[np.int32]] = {}
    gwf_table = np.loadtxt(mf6_msw_node_map, dtype=np.int32, ndmin=2)
    coupling_tables["mf6_gwf_nodes"] = gwf_table[:, 0] - 1  # mf6 nodes are one based
    coupling_tables["msw_gwf_nodes"] = svats2index(gwf_table[:, 1], gwf_table[:, 2])
    rch_table: NDArray[np.int32] = np.loadtxt(
        mf6_msw_recharge_map, dtype=np.int32, ndmin=2
    )
    coupling_tables["mf6_rch_nodes"] = rch_table[:, 0] - 1
    coupling_tables["msw_rch_nodes"] = svats2index(rch_table[:, 1], rch_table[:, 2])
    if mf6_msw_sprinkling_map_groundwater is not None:
        well_table: NDArray[np.int32] = np.loadtxt(
            mf6_msw_sprinkling_map_groundwater,
            dtype=np.int32,
            ndmin=2,
        )
        coupling_tables["mf6_well_nodes"] = well_table[:, 0] - 1
        coupling_tables["msw_well_nodes"] = svats2index(
            well_table[:, 1], well_table[:, 2]
        )
    return coupling_tables


def get_coupled_ribasim_metaswap_nodes(
    rib_msw_ponding_map_surface_water: Path | None,
    rib_msw_sprinkling_map_surface_water: Path | None,
) -> dict[str, NDArray[np.int32]]:
    coupling_tables: dict[str, NDArray[np.int32]] = {}
    if rib_msw_ponding_map_surface_water is not None:
        table_node2svat = np.loadtxt(
            rib_msw_ponding_map_surface_water,
            dtype=np.int32,
            skiprows=1,
            ndmin=2,
        )
        coupling_tables["ribasim_ponding_nodes"] = table_node2svat[:, 0]
        coupling_tables["metaswap_ponding_nodes"] = table_node2svat[:, 1] - 1
    if rib_msw_sprinkling_map_surface_water is not None:
        table_node2svat = np.loadtxt(
            rib_msw_sprinkling_map_surface_water,
            dtype=np.int32,
            skiprows=1,
            ndmin=2,
        )
        coupling_tables["ribasim_sprinkling_nodes"] = table_node2svat[:, 0]
        coupling_tables["metaswap_sprinkling_nodes"] = table_node2svat[:, 1] - 1
    return coupling_tables


def get_coupled_ribasim_modflow_nodes(
    coupling_config: ChainMap[str, Path],
) -> dict[str, dict[str, NDArray[np.int32]]]:
    coupling_tables = {}
    for key, path in coupling_config.items():
        table = np.loadtxt(path, delimiter="\t", dtype=int, skiprows=1, ndmin=2)
        _, ncol = table.shape
        if ncol == 2:
            basin_index, bound_index = table.T
            coupling_tables[key] = {
                "basin_index": basin_index,
                "bound_index": bound_index,
            }
        else:
            basin_index, bound_index, subgrid_index = table.T
            coupling_tables[key] = {
                "basin_index": basin_index,
                "bound_index": bound_index,
                "subgrid_index": subgrid_index,
            }
    return coupling_tables
