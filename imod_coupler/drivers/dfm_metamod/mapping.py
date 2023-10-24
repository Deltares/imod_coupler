import errno
import os
from pathlib import Path
from typing import Any, Dict, Optional, Type

import numpy as np
from numpy import float_, int_
from numpy.typing import NDArray
from pydantic import BaseModel
from scipy.sparse import csr_matrix, dia_matrix, diags
from scipy.spatial import KDTree
from xmipy import XmiWrapper

from imod_coupler.drivers.dfm_metamod.config import Coupling
from imod_coupler.utils import Operator, create_mapping


class Mapping:
    def __init__(
        self,
        coupling: Coupling,
        msw_working_directory: Path,
        array_dims: dict[str, int],
    ) -> None:
        self.coupling = coupling
        self.msw_working_directory = msw_working_directory
        self.array_dims = array_dims
        self.get_svat_lookup()

    def mapping_mf_msw(
        self, mf6_conversion_matrix: NDArray[np.float_]
    ) -> tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]:
        """function creates dictionary with mapping tables for mapping arrays between modflow6 and metaswap and dflow1d
        (both ways).

            # mapping includes MF-MSW coupling:
            #   1 Storage:      msw -> mf6
            #   2 heads:        msw <- mf6
            #   3 volume:       msw -> mf6
            #   3 sprinkling:   msw <- mf6

        Args:
        mf_conversion_matrix (NDArray[np.float_])
            the area conversion matrix to be used between the exchange from msw to mf6

        Returns:
            tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]: dicts with mapping and masks for exchange types
        """

        map_mf_msw: Dict[str, csr_matrix] = {}
        mask_mf_msw: Dict[str, NDArray[Any]] = {}

        # read_coupling file
        table_node2svat: NDArray[np.int32] = np.loadtxt(
            self.coupling.mf6_msw_node_map, dtype=np.int32, ndmin=2
        )
        node_idx = table_node2svat[:, 0] - 1
        msw_idx = [
            self.svat_lookup[table_node2svat[ii, 1], table_node2svat[ii, 2]]
            for ii in range(len(table_node2svat))
        ]

        # storage exchange from metaswap to mf6
        map_mf_msw["msw2mf_storage"], mask_mf_msw["msw2mf_storage"] = create_mapping(
            msw_idx,
            node_idx,
            self.array_dims["msw_storage"],
            self.array_dims["mf6_storage"],
            Operator.SUM,
        )
        # MetaSWAP gives SC1*area, MODFLOW by default needs SS.
        # When MODFLOW is configured to use SC1 explicitly via the
        # STORAGECOEFFICIENT option in the STO package, only the multiplication
        # by area needs to be undone
        map_mf_msw["msw2mf_storage"] = (
            mf6_conversion_matrix * map_mf_msw["msw2mf_storage"]
        )

        # head exchange from mf6 to msw
        map_mf_msw["mod2msw_head"], mask_mf_msw["mod2msw_head"] = create_mapping(
            node_idx,
            msw_idx,
            self.array_dims["mf6_head"],
            self.array_dims["msw_head"],
            Operator.AVERAGE,
        )
        table_rch2svat: NDArray[np.int32] = np.loadtxt(
            self.coupling.mf6_msw_recharge_map, dtype=np.int32, ndmin=2
        )
        rch_idx = table_rch2svat[:, 0] - 1
        msw_idx = [
            self.svat_lookup[table_rch2svat[ii, 1], table_rch2svat[ii, 2]]
            for ii in range(len(table_rch2svat))
        ]

        # recharge exchange from msw to mf6
        (
            map_mf_msw["msw2mod_recharge"],
            mask_mf_msw["msw2mod_recharge"],
        ) = create_mapping(
            msw_idx,
            rch_idx,
            self.array_dims["msw_volume"],
            self.array_dims["mf6_recharge"],
            Operator.SUM,
        )
        # optional sprinkling from mf6 to msw
        if self.coupling.enable_sprinkling():
            assert isinstance(self.coupling.mf6_msw_well_pkg, str)
            assert isinstance(self.coupling.mf6_msw_sprinkling_map, Path)

            table_well2svat: NDArray[np.int32] = np.loadtxt(
                self.coupling.mf6_msw_sprinkling_map, dtype=np.int32, ndmin=2
            )
            well_idx = table_well2svat[:, 0] - 1
            msw_idx = [
                self.svat_lookup[table_well2svat[ii, 1], table_well2svat[ii, 2]]
                for ii in range(len(table_well2svat))
            ]

            (
                map_mf_msw["msw2mod_sprinkling"],
                mask_mf_msw["msw2mod_sprinkling"],
            ) = create_mapping(
                msw_idx,
                well_idx,
                self.array_dims["msw_volume"],
                self.array_dims["mf6_sprinkling_wells"],
                Operator.SUM,
            )
        return map_mf_msw, mask_mf_msw

    def mapping_active_mf_dflow1d(
        self,
    ) -> tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]:
        """
        function creates dictionary with mapping tables for mapping arrays between MF and dflow1d
        (both ways).

            # mapping includes active MF coupling:
            #   1 MF RIV 1                      -> DFLOW-FM 1D flux
            #   2 DFLOW FM 1D (correction)flux  -> MF RIV 1
            #   3 DFLOW FM 1D stage             -> MF RIV 1

        Parameters
        ----------
        None

        Returns
        -------
        tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]
            The first return value is a dict containing as key, the exchange type,
            and as value, the sparse matrix used for this kind of exchange.
            The second return value is a dict containing as key, the exchange type,
            and as value, the mask used for this kind of exchange.

        """
        #
        map_active_mod_dflow1d: Dict[str, csr_matrix] = {}
        mask_active_mod_dflow1d: Dict[str, NDArray[Any]] = {}

        # MF RIV 1 -> DFLOW 1D (flux)
        map_active_mod_dflow1d["mf-riv2dflow1d_flux"] = None
        mask_active_mod_dflow1d["mf-riv2dflow1d_flux"] = np.array([])
        map_active_mod_dflow1d["dflow1d2mf-riv_flux"] = None
        mask_active_mod_dflow1d["dflow1d2mf-riv_flux"] = np.array([])

        if self.coupling.mf6_river_to_dfm_1d_q_dmm is not None:
            table_active_mfriv2dflow1d: NDArray[np.single] = np.loadtxt(
                self.coupling.mf6_river_to_dfm_1d_q_dmm,
                dtype=np.single,
                ndmin=2,
                skiprows=1,
            )
            ptx = table_active_mfriv2dflow1d[:, 0]
            pty = table_active_mfriv2dflow1d[:, 1]
            mf_idx = table_active_mfriv2dflow1d[:, 2].astype(int) - 1
            _, dflow_idx = self.dflow1d_lookup.query(np.c_[ptx, pty])

            (
                map_active_mod_dflow1d["mf-riv2dflow1d_flux"],
                mask_active_mod_dflow1d["mf-riv2dflow1d_flux"],
            ) = create_mapping(
                mf_idx,
                dflow_idx,
                self.array_dims["mf6_riv_active"],
                self.array_dims["dfm_1d"],
                Operator.SUM,
            )
            # DFLOW 1D  -> MF RIV 1 (flux) (non weighted)
            (
                map_active_mod_dflow1d["dflow1d2mf-riv_flux"],
                mask_active_mod_dflow1d["dflow1d2mf-riv_flux"],
            ) = create_mapping(
                dflow_idx, mf_idx, max(dflow_idx) + 1, max(mf_idx) + 1, Operator.SUM
            )

        # DFLOW 1D -> MF RIV 1 (stage)
        map_active_mod_dflow1d["dflow1d2mf-riv_stage"] = None
        mask_active_mod_dflow1d["dflow1d2mf-riv_stage"] = np.array([])
        if self.coupling.dfm_1d_waterlevel_to_mf6_river_stage_dmm is not None:
            table_active_dflow1d2mfriv: NDArray[np.single] = np.loadtxt(
                self.coupling.dfm_1d_waterlevel_to_mf6_river_stage_dmm,
                dtype=np.single,
                ndmin=2,
                skiprows=1,
            )
            mf_idx = table_active_dflow1d2mfriv[:, 0].astype(int) - 1
            ptx = table_active_dflow1d2mfriv[:, 1]
            pty = table_active_dflow1d2mfriv[:, 2]
            weight = table_active_dflow1d2mfriv[:, 3]
            _, dflow_idx = self.dflow1d_lookup.query(np.c_[ptx, pty])

            (
                map_active_mod_dflow1d["dflow1d2mf-riv_stage"],
                mask_active_mod_dflow1d["dflow1d2mf-riv_stage"],
            ) = create_mapping(
                dflow_idx,
                mf_idx,
                self.array_dims["dfm_1d"],
                self.array_dims["mf6_riv_active"],
                Operator.WEIGHT,
                weight,
            )
        return map_active_mod_dflow1d, mask_active_mod_dflow1d

    def mapping_passive_mf_dflow1d(
        self,
    ) -> tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]:
        """
        function creates dictionary with mapping tables for mapping MF <-> dflow1d
        To be used for passive MF coupling:
          1 MF RIV 2                      -> DFLOW-FM 1D flux
          2 MF DRN                        -> DFLOW-FM 1D flux

        Parameters
        ----------

        None

        Returns
        -------
        tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]
            The first return value is a dict containing as key, the exchange type,
            and as value, the sparse matrix used for this kind of exchange.
            The second return value is a dict containing as key, the exchange type,
            and as value, the mask used for this kind of exchange.
        """

        map_passive_mod_dflow1d: Dict[str, csr_matrix] = {}
        mask_passive_mod_dflow1d: Dict[str, NDArray[Any]] = {}

        # MF RIV 2 -> DFLOW 1D (flux)
        map_passive_mod_dflow1d["mf-riv2dflow1d_passive_flux"] = None
        mask_passive_mod_dflow1d["mf-riv2dflow1d_passive_flux"] = np.array([])
        if self.coupling.mf6_river2_to_dfm_1d_q_dmm is not None:
            table_passive_mfriv2dflow1d: NDArray[np.single] = np.loadtxt(
                self.coupling.mf6_river2_to_dfm_1d_q_dmm,
                dtype=np.single,
                ndmin=2,
                skiprows=1,
            )
            ptx = table_passive_mfriv2dflow1d[:, 0]
            pty = table_passive_mfriv2dflow1d[:, 1]
            mf_idx = table_passive_mfriv2dflow1d[:, 2].astype(int) - 1
            _, dflow_idx = self.dflow1d_lookup.query(np.c_[ptx, pty])

            (
                map_passive_mod_dflow1d["mf-riv2dflow1d_passive_flux"],
                mask_passive_mod_dflow1d["mf-riv2dflow1d_passive_flux"],
            ) = create_mapping(
                mf_idx,
                dflow_idx,
                self.array_dims["mf6_riv_passive"],
                self.array_dims["dfm_1d"],
                Operator.SUM,
            )
        # MF DRN -> DFLOW 1D (flux)
        map_passive_mod_dflow1d["mf-drn2dflow1d_flux"] = None
        mask_passive_mod_dflow1d["mf-drn2dflow1d_flux"] = np.array([])
        if self.coupling.mf6_drainage_to_dfm_1d_q_dmm is not None:
            table_passive_mfdrn2dflow1d: NDArray[np.single] = np.loadtxt(
                self.coupling.mf6_drainage_to_dfm_1d_q_dmm,
                dtype=np.single,
                ndmin=2,
                skiprows=1,
            )
            ptx = table_passive_mfdrn2dflow1d[:, 0]
            pty = table_passive_mfdrn2dflow1d[:, 1]
            mf_idx = table_passive_mfdrn2dflow1d[:, 2].astype(int) - 1
            _, dflow_idx = self.dflow1d_lookup.query(np.c_[ptx, pty])

            (
                map_passive_mod_dflow1d["mf-drn2dflow1d_flux"],
                mask_passive_mod_dflow1d["mf-drn2dflow1d_flux"],
            ) = create_mapping(
                mf_idx,
                dflow_idx,
                self.array_dims["mf6_drn"],
                self.array_dims["dfm_1d"],
                Operator.SUM,
            )
        return map_passive_mod_dflow1d, mask_passive_mod_dflow1d

    def mapping_msw_dflow1d(
        self,
    ) -> tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]:
        """
        function creates dictionary with mapping tables for mapping MSW -> dflow1d
        mapping includes MSW 1D coupling:
        1 MSW sprinkling flux            -> DFLOW-FM 1D flux
        2 DFLOW-FM 1D flux               -> MSW sprinkling flux
        3 MSW ponding flux               -> DFLOW-FM 1D flux (optional if no 2D network is availble)

        Parameters
        ----------

        None

        Returns
        -------
            The first return value is a dict containing as key, the exchange type,
            and as value, the sparse matrix used for this kind of exchange.
            The second return value is a dict containing as key, the exchange type,
            and as value, the mask used for this kind of exchange.
        """
        map_msw_dflow1d: Dict[str, csr_matrix] = {}
        mask_msw_dflow1d: Dict[str, NDArray[int_]] = {}

        map_msw_dflow1d["msw-sprinkling2dflow1d_flux"] = None
        mask_msw_dflow1d["msw-sprinkling2dflow1d_flux"] = np.array([])
        map_msw_dflow1d["dflow1d_flux2sprinkling_msw"] = None
        mask_msw_dflow1d["dflow1d_flux2sprinkling_msw"] = np.array([])

        # MSW -> DFLOW 1D (sprinkling)
        if self.coupling.msw_sprinkling_to_dfm_1d_q_dmm is not None:
            table_mswsprinkling2dflow1d: NDArray[np.single] = np.loadtxt(
                self.coupling.msw_sprinkling_to_dfm_1d_q_dmm,
                dtype=np.single,
                ndmin=2,
                skiprows=1,
            )
            ptx = table_mswsprinkling2dflow1d[:, 0]
            pty = table_mswsprinkling2dflow1d[:, 1]
            msw_idx = table_mswsprinkling2dflow1d[:, 2].astype(int) - 1
            _, dflow_idx = self.dflow1d_lookup.query(np.c_[ptx, pty])

            (
                map_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
                mask_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
            ) = create_mapping(
                msw_idx,
                dflow_idx,
                self.array_dims["msw_sw_sprinkling"],
                self.array_dims["dfm_1d"],
                Operator.SUM,
            )
            # MSW <- DFLOW 1D (sprinkling)
            (
                map_msw_dflow1d["dflow1d_flux2sprinkling_msw"],
                mask_msw_dflow1d["dflow1d_flux2sprinkling_msw"],
            ) = create_mapping(
                dflow_idx,
                msw_idx,
                self.array_dims["dfm_1d"],
                self.array_dims["msw_sw_sprinkling"],
                Operator.SUM,
            )
        map_msw_dflow1d["msw-ponding2dflow1d_flux"] = None
        mask_msw_dflow1d["msw-ponding2dflow1d_flux"] = np.array([])
        if self.coupling.msw_runoff_to_dfm_1d_q_dmm is not None:
            # MSW -> DFLOW 1D (ponding)
            table_mswponding2dflow1d: NDArray[np.single] = np.loadtxt(
                self.coupling.msw_runoff_to_dfm_1d_q_dmm,
                dtype=np.single,
                ndmin=2,
                skiprows=1,
            )
            ptx = table_mswponding2dflow1d[:, 0]
            pty = table_mswponding2dflow1d[:, 1]
            msw_idx = table_mswponding2dflow1d[:, 2].astype(int) - 1
            _, dflow_idx = self.dflow1d_lookup.query(np.c_[ptx, pty])

            (
                map_msw_dflow1d["msw-ponding2dflow1d_flux"],
                mask_msw_dflow1d["msw-ponding2dflow1d_flux"],
            ) = create_mapping(
                msw_idx,
                dflow_idx,
                self.array_dims["msw_sw_ponding"],
                self.array_dims["dfm_1d"],
                Operator.SUM,
            )
        return map_msw_dflow1d, mask_msw_dflow1d

    def mapping_msw_dflow2d(
        self,
    ) -> tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]:
        """
        # dictionary with mapping tables for msw-dflow-2d coupling
        # mapping includes MSW 2D coupling:
        #   1 MSW ponding flux               -> DFLOW-FM 2D flux (optional)
        #   2 DFLOW-FM 2D flux               -> MSW ponding flux (optional)
        #   3 DFLOW-FM 2D stage              -> MSW ponding stage (optional)

        Parameters
        ----------
        None

        Returns
        -------
            The first return value is a dict containing as key, the exchange type,
            and as value, the sparse matrix used for this kind of exchange.
            The second return value is a dict containing as key, the exchange type,
            and as value, the mask used for this kind of exchange.
        """

        map_msw_dflow2d: Dict[str, csr_matrix] = {}
        mask_msw_dflow2d: Dict[str, NDArray[Any]] = {}

        # MSW -> DFLOW 2D (ponding)

        # ---mapping of msw ponding to dflow2d---
        table_mswponding2dflow2d = np.array([], dtype=np.single)
        map_msw_dflow2d["msw-ponding2dflow2d_flux"] = None
        mask_msw_dflow2d["msw-ponding2dflow2d_flux"] = np.array([])
        map_msw_dflow2d["dflow2d_flux2msw-ponding"] = None
        mask_msw_dflow2d["dflow2d_flux2msw-ponding"] = np.array([])

        if self.coupling.msw_ponding_to_dfm_2d_dv_dmm is not None:
            table_mswponding2dflow2d = np.loadtxt(
                self.coupling.msw_ponding_to_dfm_2d_dv_dmm,
                dtype=np.single,
                ndmin=2,
                skiprows=1,
            )

        if table_mswponding2dflow2d.size > 0:
            ptx = table_mswponding2dflow2d[:, 0]
            pty = table_mswponding2dflow2d[:, 1]

            msw_idx = table_mswponding2dflow2d[:, 2].astype(int) - 1
            _, dflow_idx = self.dflow2d_lookup.query(np.c_[ptx, pty])

            (
                map_msw_dflow2d["msw-ponding2dflow2d_flux"],
                mask_msw_dflow2d["msw-ponding2dflow2d_flux"],
            ) = create_mapping(
                msw_idx,
                dflow_idx,
                self.array_dims["msw_sw_ponding"],
                self.array_dims["dfm_2d"],
                Operator.SUM,
            )

        # DFLOW 2D -> MSW (stage/innudation)
        table_dflow2d_stage2mswponding = np.array([], dtype=np.single)
        map_msw_dflow2d["dflow2d_stage2msw-ponding"] = None
        mask_msw_dflow2d["dflow2d_stage2msw-ponding"] = np.array([])

        if self.coupling.dfm_2d_waterlevels_to_msw_h_dmm is not None:
            table_dflow2d_stage2mswponding = np.loadtxt(
                self.coupling.dfm_2d_waterlevels_to_msw_h_dmm,
                dtype=np.single,
                ndmin=2,
                skiprows=1,
            )

        if table_dflow2d_stage2mswponding.size > 0:
            msw_idx = (table_dflow2d_stage2mswponding[:, 0] - 1).astype(int)
            ptx = table_dflow2d_stage2mswponding[:, 1]
            pty = table_dflow2d_stage2mswponding[:, 2]
            weight = table_dflow2d_stage2mswponding[:, 3]
            _, dflow_idx = self.dflow2d_lookup.query(np.c_[ptx, pty])

            (
                map_msw_dflow2d["dflow2d_stage2msw-ponding"],
                mask_msw_dflow2d["dflow2d_stage2msw-ponding"],
            ) = create_mapping(
                dflow_idx,
                msw_idx,
                self.array_dims["dfm_2d"],
                self.array_dims["msw_sw_ponding"],
                Operator.WEIGHT,
                weight,
            )
        return map_msw_dflow2d, mask_msw_dflow2d

    def calc_correction(
        self,
        mapping: csr_matrix,
        q_pre1: NDArray[float_],
        q_pre2: NDArray[float_],
        q_post2: NDArray[float_],
    ) -> NDArray[float_]:
        """
        this function computes the not-realized amounts in system1
        by comparing demand and realization in system2 and applying the resulting
        fraction realized back on system1, which gives the not-realized values in system1

        Parameters
        ----------
        mapping : csr_matrix
            Un-weighted mapping from system1 to system2
        q_pre1 : NDArray[float_]
            Input array of demand values in system1
        q_pre2:  NDArray[float_]
            Input array of demand values in system2
        q_post2:  NDArray[float_]
            realized values in system2

        Returns
        -------
        NDArray[float_]:
            the amounts in system1 that were NOT realized (i.o.w. correction terms)

        """
        alpha = np.maximum(0.0, (1.0 - q_post2 / np.maximum(q_pre2, 1.0e-13)))
        qcorr = np.array(alpha * (mapping.dot(diags(q_pre1))))
        return qcorr

    def get_svat_lookup(self) -> None:
        """
        read file with all coupled MetaSWAP svat. Function creates a lookup, with the svat tuples (id, lay) as keys and the metaswap internal indexes as values

        Parameters
        ----------
        workdir_msw : Path
            directory where MetaSWAP mapping input files can be found

        Returns
        -------
        tuple[dict[tuple[int, int], int]
           The first value of the tupple is a dictionary of pairs svat and layer to internal svat-number.
        """

        svat_lookup = {}
        msw_mod2svat_file = self.msw_working_directory / "mod2svat.inp"
        if msw_mod2svat_file.is_file():
            svat_data: NDArray[np.int32] = np.loadtxt(
                msw_mod2svat_file, dtype=np.int32, ndmin=2
            )
            svat_id = svat_data[:, 1]
            svat_lay = svat_data[:, 2]
            for vi in range(svat_id.size):
                svat_lookup[(svat_id[vi], svat_lay[vi])] = vi
        else:
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), msw_mod2svat_file
            )
        self.svat_lookup = svat_lookup

    def set_dfm_lookup(self, kdtree_1D: KDTree, kdtree_2D: KDTree) -> None:
        self.dflow1d_lookup = kdtree_1D
        self.dflow2d_lookup = kdtree_2D
