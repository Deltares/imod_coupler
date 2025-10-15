from collections import ChainMap
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import csr_matrix, dia_matrix

from imod_coupler.drivers.ribametamod.config import Coupling
from imod_coupler.utils import create_mapping


class SetMapping:
    # TODO: check who should be leading if no changes are defined
    map_mod2rib: dict[str, csr_matrix]
    map_rib2mod_stage: dict[str, csr_matrix]
    map_rib2mod_flux: dict[str, csr_matrix]
    mask_rib2mod: dict[str, csr_matrix]
    msw2mod: dict[str, csr_matrix]
    mod2msw: dict[str, csr_matrix]
    msw2rib: dict[str, csr_matrix]
    coupled_mod2rib: NDArray[np.bool_]

    def __init__(
        self,
        coupling: Coupling,
        array_info: ChainMap[str, Any],
        has_metaswap: bool,
        has_ribasim: bool,
        mod2svat: Path | None,
    ):
        self.coupling = coupling
        if has_ribasim:
            self.set_ribasim_modflow_mapping(array_info)
            self.coupled_index = self.coupled_mod2rib
        if has_metaswap and mod2svat is not None:
            self.set_metaswap_modflow_mapping(array_info, mod2svat)
        if has_ribasim and has_metaswap and mod2svat is not None:
            self.set_metaswap_ribasim_mapping(array_info, mod2svat)
            self.coupled_index |= self.coupled_msw2rib

    def set_ribasim_modflow_mapping(self, array_info: ChainMap[str, Any]) -> None:
        self.map_mod2rib = {}
        self.coupled_mod2rib = np.full(array_info["ribasim_nbasin"], False)
        self.map_rib2mod_stage = {}
        self.map_rib2mod_flux = {}
        self.mask_rib2mod = {}
        active_tables = ChainMap(
            self.coupling.mf6_active_river_packages,
            self.coupling.mf6_active_drainage_packages,
        )
        for key, path in active_tables.items():
            table = np.loadtxt(path, delimiter="\t", dtype=int, skiprows=1, ndmin=2)
            basin_index, bound_index, subgrid_index = table.T
            data = np.ones_like(basin_index, dtype=np.float64)

            mod2rib = csr_matrix(
                (data, (basin_index, bound_index)),
                shape=(array_info["ribasim_nbasin"], array_info[key]),
            )
            rib2mod = csr_matrix(
                (data, (bound_index, subgrid_index)),
                shape=(array_info[key], array_info["ribasim_nsubgrid"]),
            )

            # check rib2mod for multiple subgrid per modflow node (should not occur)
            count_list = rib2mod.indptr[1:] - rib2mod.indptr[:-1]
            too_many = np.flatnonzero(count_list > 1)
            if np.size(too_many) > 0:
                raise ValueError(
                    f"More than one ribasim subgrid element associated with MODFLOW6 node {too_many}."
                )

            self.map_mod2rib[key] = mod2rib
            self.map_rib2mod_stage[key] = (
                rib2mod  # for mapping stages between subgrid levels and riv nodes
            )
            self.map_rib2mod_flux[key] = (
                mod2rib.T
            )  # for mapping fluxes between basins and riv nodes

            self.mask_rib2mod[key] = (rib2mod.getnnz(axis=1) == 0).astype(int)
            # In-place bitwise or
            self.coupled_mod2rib |= mod2rib.getnnz(axis=1) > 0

        passive_tables = ChainMap(
            self.coupling.mf6_passive_river_packages,
            self.coupling.mf6_passive_drainage_packages,
        )
        for key, path in passive_tables.items():
            table = np.loadtxt(path, delimiter="\t", dtype=int, skiprows=1, ndmin=2)
            basin_index, bound_index = table.T
            data = np.ones_like(basin_index, dtype=np.float64)
            mod2rib = csr_matrix(
                (data, (basin_index, bound_index)),
                shape=(array_info["ribasim_nbasin"], array_info[key]),
            )
            self.map_mod2rib[key] = mod2rib
            # In-place bitwise or
            self.coupled_mod2rib |= mod2rib.getnnz(axis=1) > 0

    def set_metaswap_modflow_mapping(
        self, array_info: ChainMap[str, Any], mod2svat: Path
    ) -> None:
        if self.coupling.mf6_msw_node_map is None:
            return
        if self.coupling.mf6_msw_recharge_map is None:
            return

        svat_lookup = set_svat_lookup(mod2svat)

        self.mod2msw = {}
        self.msw2mod = {}

        table_node2svat: NDArray[np.int32] = np.loadtxt(
            self.coupling.mf6_msw_node_map, dtype=np.int32, ndmin=2
        )
        node_idx = table_node2svat[:, 0] - 1
        msw_idx = [
            svat_lookup[table_node2svat[ii, 1], table_node2svat[ii, 2]]
            for ii in range(len(table_node2svat))
        ]
        self.msw2mod["storage"], self.msw2mod["storage_mask"] = create_mapping(
            msw_idx,
            node_idx,
            array_info["msw_storage"].size,
            array_info["mf6_storage"].size,
            "sum",
        )
        # MetaSWAP gives SC1*area, MODFLOW by default needs SS, convert here.
        # When MODFLOW is configured to use SC1 explicitly via the
        # STORAGECOEFFICIENT option in the STO package, only the multiplication
        # by area needs to be undone
        if array_info["mf6_has_sc1"]:
            conversion_terms = 1.0 / array_info["mf6_area"]
        else:
            conversion_terms = 1.0 / (
                array_info["mf6_area"] * (array_info["mf6_top"] - array_info["mf6_bot"])
            )

        conversion_matrix = dia_matrix(
            (conversion_terms, [0]),
            shape=(array_info["mf6_area"].size, array_info["mf6_area"].size),
            dtype=array_info["mf6_area"].dtype,
        )
        self.msw2mod["storage"] = conversion_matrix * self.msw2mod["storage"]

        self.mod2msw["head"], self.mod2msw["head_mask"] = create_mapping(
            node_idx,
            msw_idx,
            array_info["mf6_head"].size,
            array_info["msw_head"].size,
            "avg",
        )
        table_rch2svat: NDArray[np.int32] = np.loadtxt(
            self.coupling.mf6_msw_recharge_map, dtype=np.int32, ndmin=2
        )
        rch_idx = table_rch2svat[:, 0] - 1
        msw_idx = [
            svat_lookup[table_rch2svat[ii, 1], table_rch2svat[ii, 2]]
            for ii in range(len(table_rch2svat))
        ]

        self.msw2mod["recharge"], self.msw2mod["recharge_mask"] = create_mapping(
            msw_idx,
            rch_idx,
            array_info["msw_volume"].size,
            array_info["mf6_recharge"].size,
            "sum",
        )

        if self.coupling.mf6_msw_sprinkling_map_groundwater is not None:
            assert isinstance(self.coupling.mf6_msw_well_pkg, str)
            assert isinstance(self.coupling.mf6_msw_sprinkling_map_groundwater, Path)

            # in this case we have a sprinkling demand from MetaSWAP
            table_well2svat: NDArray[np.int32] = np.loadtxt(
                self.coupling.mf6_msw_sprinkling_map_groundwater,
                dtype=np.int32,
                ndmin=2,
            )
            well_idx = table_well2svat[:, 0] - 1
            msw_idx = [
                svat_lookup[table_well2svat[ii, 1], table_well2svat[ii, 2]]
                for ii in range(len(table_well2svat))
            ]

            (
                self.msw2mod["gw_sprinkling"],
                self.msw2mod["gw_sprinkling_mask"],
            ) = create_mapping(
                msw_idx,
                well_idx,
                array_info["msw_volume"].size,
                array_info["mf6_sprinkling_wells"].size,
                "sum",
            )

    def set_metaswap_ribasim_mapping(
        self, array_info: ChainMap[str, Any], mod2svat: Path
    ) -> None:
        table_node2svat: NDArray[np.int32]
        self.coupled_msw2rib: NDArray[np.bool_] = np.full(
            array_info["ribasim_nbasin"], False
        )
        self.msw2rib = {}

        # surface water ponding mapping
        if self.coupling.rib_msw_ponding_map_surface_water is not None:
            table_node2svat = np.loadtxt(
                self.coupling.rib_msw_ponding_map_surface_water,
                dtype=np.int32,
                skiprows=1,
                ndmin=2,
            )
            rib_idx = table_node2svat[:, 0]
            msw_idx = table_node2svat[:, 1] - 1
            (
                self.msw2rib["sw_ponding"],
                self.msw2rib["sw_ponding_mask"],
            ) = create_mapping(
                msw_idx,
                rib_idx,
                array_info["ribmsw_nbound"],
                array_info["ribasim_nbasin"],
                "sum",
            )
            self.coupled_msw2rib |= self.msw2rib["sw_ponding"].getnnz(axis=1) > 0

        # surface water sprinkling mapping
        if self.coupling.rib_msw_sprinkling_map_surface_water is not None:
            table_node2svat = np.loadtxt(
                self.coupling.rib_msw_sprinkling_map_surface_water,
                dtype=np.int32,
                skiprows=1,
                ndmin=2,
            )
            rib_idx = table_node2svat[:, 0]
            msw_idx = table_node2svat[:, 1] - 1
            (
                self.msw2rib["sw_sprinkling"],
                self.msw2rib["sw_sprinkling_mask"],
            ) = create_mapping(
                msw_idx,
                rib_idx,
                array_info["ribmsw_nbound"],
                array_info["ribasim_nuser"],
                "sum",
            )
            # should become shape of 'users'-array in Ribasim


def set_svat_lookup(mod2svat: Path) -> dict[Any, Any]:
    svat_lookup = {}
    msw_mod2svat_file = mod2svat
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
    return svat_lookup
