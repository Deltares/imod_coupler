from collections import ChainMap
from typing import Any, Dict

from numpy.typing import NDArray
from scipy.sparse import csr_matrix

from imod_coupler.drivers.ribametamod.config import Coupling


class set_mapping:
    mod2rib: Dict[str, csr_matrix]
    rib2mod: Dict[str, csr_matrix]

    def __init__(self, coupling: Coupling, packages: Dict[str, NDArray]):
        self.coupling = coupling
        self.set_ribasim_mapping(packages)

    def set_ribasim_mapping(self, packages: Dict[str, NDArray]) -> None:
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
