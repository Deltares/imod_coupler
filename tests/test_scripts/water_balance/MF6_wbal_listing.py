#!/usr/bin/env python

import re
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd


class status(Enum):
    NO_OPERATION = 0
    VOLUME = 1
    VOLUME_IN = 2
    VOLUME_OUT = 3


defined_pkg_type = {
    "STORAGE": "STO-SS",
    "DRAINS": "DRN",
    "RIVER_LEAKAGE": "RIV",
    "DXC_FLUXES": "RCH",
    "CONSTANT_HEAD": "CHD",
}


def listfile_to_dataframe(file_in: Path) -> pd.DataFrame:
    ignore = ["IN - OUT", "DISCREPANCY"]
    df_data_out = pd.DataFrame()

    with open(file_in, "r") as fnin_mflist:
        stat = status.NO_OPERATION
        for regel in fnin_mflist:
            if re.match(r"^.*TIME SUMMARY", regel):
                stat = status.NO_OPERATION
                continue
            if re.match(r"\s*OUT:\s+OUT:", regel):
                stat = status.VOLUME_OUT
                postfix = "_OUT"
                continue
            if re.match(r"\s*IN:\s+IN:", regel):
                stat = status.VOLUME_IN
                postfix = "_IN"
                continue
            m = re.match(r"^\s*VOLUME.* BUDGET.*STRESS PERIOD\s+(\d+)", regel)
            if m:
                stress_period = int(m.group(1)) - 1
                stat = status.VOLUME
                continue
            if any([pattern in regel for pattern in ignore]):
                continue
            if stat in [status.VOLUME_IN, status.VOLUME_OUT]:
                m = re.match(r"^\s*([\s\w\-]+\s*=)\s*([^\s]+)", regel)
                if m:
                    splitter = m.group(1)
                    _, part2 = re.split(splitter, regel)[-2:]
                    thisval = float(part2.split()[0])

                    pkg1 = re.sub(r"\s+", "_", re.sub(r"\s*=\s*", "", splitter))
                    pkg2 = pkg1
                    try:
                        pkg2 = part2.split()[1]
                        pkgname = "%s:%s" % (pkg1, pkg2)  # modflow6 format
                    except:
                        if pkg1 in defined_pkg_type:
                            pkg2 = defined_pkg_type[pkg1]
                        else:
                            pkg2 = pkg1
                        pkgname = "%s:%s" % (pkg2, pkg1)  # modflow5 format
                    df_data_out.at[stress_period, pkgname + postfix] = thisval
                continue
        return df_data_out
