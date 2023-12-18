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
    mod2rib: dict[str, csr_matrix]
    rib2mod: dict[str, csr_matrix]
    msw2mod: dict[str, csr_matrix]
    mod2msw: dict[str, csr_matrix]

    def __init__(
        self,
        coupling: Coupling,
        packages: ChainMap[str, Any],
        has_metaswap: bool,
        has_ribasim: bool,
        mod2svat: Path | None,
    ):
        self.coupling = coupling
        if has_ribasim:
            self.set_ribasim_modflow_mapping(packages)
        if has_metaswap and mod2svat is not None:
            self.set_metaswap_modflow_mapping(packages, mod2svat)
        if has_ribasim and has_metaswap and mod2svat is not None:
            self.set_metaswap_ribasim_mapping(packages, mod2svat)

    def set_ribasim_modflow_mapping(self, packages: ChainMap[str, Any]) -> None:
        coupling_tables = ChainMap(
            self.coupling.mf6_active_river_packages,
            self.coupling.mf6_passive_river_packages,
            self.coupling.mf6_active_drainage_packages,
            self.coupling.mf6_passive_drainage_packages,
        )
        self.mod2rib = {}
        self.rib2mod = {}
        for key, path in coupling_tables.items():
            table = np.loadtxt(path, delimiter="\t", dtype=int, skiprows=1, ndmin=2)
            # Ribasim sorts the basins during initialization.
            row, col = table.T
            data = np.ones_like(row, dtype=float)
            # Many to one
            matrix = csr_matrix(
                (data, (row, col)),
                shape=(packages["ribasim_nbound"], packages[key].n_bound),
            )
            self.mod2rib[key] = matrix
            # One to many, just transpose
            self.rib2mod[key] = matrix.T

    def set_metaswap_modflow_mapping(
        self, packages: ChainMap[str, Any], mod2svat: Path
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
            packages["msw_storage"].size,
            packages["mf6_storage"].size,
            "sum",
        )
        # MetaSWAP gives SC1*area, MODFLOW by default needs SS, convert here.
        # When MODFLOW is configured to use SC1 explicitly via the
        # STORAGECOEFFICIENT option in the STO package, only the multiplication
        # by area needs to be undone
        if packages["mf6_has_sc1"]:
            conversion_terms = 1.0 / packages["mf6_area"]
        else:
            conversion_terms = 1.0 / (
                packages["mf6_area"] * (packages["mf6_top"] - packages["mf6_bot"])
            )

        conversion_matrix = dia_matrix(
            (conversion_terms, [0]),
            shape=(packages["mf6_area"].size, packages["mf6_area"].size),
            dtype=packages["mf6_area"].dtype,
        )
        self.msw2mod["storage"] = conversion_matrix * self.msw2mod["storage"]

        self.mod2msw["head"], self.mod2msw["head_mask"] = create_mapping(
            node_idx,
            msw_idx,
            packages["mf6_head"].size,
            packages["msw_head"].size,
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
            packages["msw_volume"].size,
            packages["mf6_recharge"].size,
            "sum",
        )

        if self.coupling.enable_sprinkling:
            assert isinstance(self.coupling.mf6_msw_well_pkg, str)
            assert isinstance(self.coupling.mf6_msw_sprinkling_map, Path)

            # in this case we have a sprinkling demand from MetaSWAP
            table_well2svat: NDArray[np.int32] = np.loadtxt(
                self.coupling.mf6_msw_sprinkling_map, dtype=np.int32, ndmin=2
            )
            well_idx = table_well2svat[:, 0] - 1
            msw_idx = [
                svat_lookup[table_well2svat[ii, 1], table_well2svat[ii, 2]]
                for ii in range(len(table_well2svat))
            ]

            (
                self.msw2mod["sprinkling"],
                self.msw2mod["sprinkling_mask"],
            ) = create_mapping(
                msw_idx,
                well_idx,
                packages["msw_volume"].size,
                packages["mf6_sprinkling_wells"].size,
                "sum",
            )

    def set_metaswap_ribasim_mapping(
            self, packages: ChainMap[str, Any], mod2svat: Path
        ) -> None:
            if self.coupling.rib_msw_sprinkling_map_surface_water is None:
                return
            svat_lookup = set_svat_lookup(mod2svat)

            self.mod2msw = {}
            self.msw2mod = {}

            table_node2svat: NDArray[np.int32] = np.loadtxt(
                self.coupling.rib_msw_sprinkling_map_surface_water, dtype=np.int32, ndmin=2
            )
            rib_idx = table_node2svat[:, 0] - 1
            msw_idx = [
                svat_lookup[table_node2svat[ii, 1], table_node2svat[ii, 2]]
                for ii in range(len(table_node2svat))
            ]
            self.msw2rib['sprinkling'], self.msw2rib['sprinkling_mask'] = create_mapping(
                msw_idx,
                rib_idx,
                packages["msw_volume"].size,
                packages["ribasim_nbound"],  # should become shape of 'users'-array in Ribasim
                "sum",
            )
    
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
