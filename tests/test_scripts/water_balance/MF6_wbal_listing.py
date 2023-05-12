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


def listfile_to_dataframe(file_in: Path) -> pd.DataFrame:
    ignore = ["IN - OUT", "DISCREPANCY"]
    df_data_out = pd.DataFrame()
    budgetblock_counter = -1
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
                loose_words_in_string = m.string.strip().split()
                time_step = int(loose_words_in_string[-4][:-1])
                stress_period =  int(loose_words_in_string[-1])
                budgetblock_counter=budgetblock_counter+1
                df_data_out.at[budgetblock_counter,"timestep"] = int(time_step)
                df_data_out.at[budgetblock_counter, "stress_period"] = int(stress_period)

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

                    pkgtype = re.sub(r"\s+", "_", re.sub(r"\s*=\s*", "", splitter))
                    pkgname = pkgtype
                    try:
                        pkgname = "%s:%s" % (
                            pkgtype,
                            part2.split()[1],
                        )  # modflow6 format
                    except:
                        pass
                    df_data_out.at[budgetblock_counter, pkgname + postfix] = thisval

                continue
        return df_data_out
