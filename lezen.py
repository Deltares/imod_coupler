from pathlib import Path

import geopandas as gpd
import imod
import pandas as pd
import pyarrow as pa

from imod_coupler.__main__ import run_coupler

# ribamod = gpd.read_file(
#     r"c:\werkmap\TKI_ribasim\test_driver\develop_ribamod\ribasim\database.gpkg"
# )
#
# ons = gpd.read_file(
#     r"c:\werkmap\TKI_ribasim\test_driver\develop_no_metaSWAP\ribasim\database.gpkg"
# )
# table = (
#     pa.ipc.open_file(
#         r"c:\werkmap\TKI_ribasim\test_driver\develop_ribamod\ribasim\results\flow.arrow"
#     )
#     .read_all()
#     .to_pandas()
# )
# subset = table[(table["to_node_id"] == 2) & (table["from_node_id"] == 2)]
# subset.to_csv(
#     r"c:\werkmap\TKI_ribasim\test_driver\develop_ribamod\ribasim\results\flow2.csv"
# )


def read_heads(headfile, grbfile):
    heads = imod.mf6.open_hds(headfile, grbfile, False)
    starttime = pd.to_datetime("2000/01/01")
    timedelta = pd.to_timedelta(heads["time"] - 1.0, "D")
    return heads.assign_coords(time=starttime + timedelta)


dir = Path(r"c:\werkmap\TKI_ribasim\test_driver\develop_no_metaSWAP_subgrid")

run_coupler(dir / "imod_coupler.toml")

headfile = dir / "modflow6" / "GWF_1" / "GWF_1.hds"
grbfile = dir / "modflow6" / "GWF_1" / "dis.dis.grb"

heads = read_heads(headfile, grbfile)

out = dir / "heads.idf"
imod.idf.save(out, heads)

pass
