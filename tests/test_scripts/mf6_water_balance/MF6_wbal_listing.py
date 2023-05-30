#!/usr/bin/env python

import re
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd


class status(Enum):
    NO_OPERATION = 0
    VOLUME_IN = 1
    VOLUME_OUT = 2


def listfile_to_dataframe(file_in: Path) -> pd.DataFrame:
    ignore = ["IN - OUT", "DISCREPANCY"]
    df_data_out = pd.DataFrame()
    budgetblock_counter = -1
    with open(file_in, "r") as fnin_mflist:
        stat = status.NO_OPERATION
        for line in fnin_mflist:
            if re.match(r"^.*TIME SUMMARY", line):
                stat = status.NO_OPERATION
            elif re.match(r"\s*OUT:\s+OUT:", line):
                stat = status.VOLUME_OUT
                postfix = "_OUT"
            elif re.match(r"\s*IN:\s+IN:", line):
                stat = status.VOLUME_IN
                postfix = "_IN"
            elif m := re.match(r"^\s*VOLUME.* BUDGET.*STRESS PERIOD\s+(\d+)", line):
                loose_words_in_string = m.string.strip().split()
                time_step = int(loose_words_in_string[-4][:-1])
                stress_period = int(loose_words_in_string[-1])
                budgetblock_counter = budgetblock_counter + 1
                df_data_out.at[budgetblock_counter, "timestep"] = int(time_step)
                df_data_out.at[budgetblock_counter, "stress_period"] = int(
                    stress_period
                )
                stat = status.NO_OPERATION
            elif any([pattern in line for pattern in ignore]):
                continue
            elif stat in [status.VOLUME_IN, status.VOLUME_OUT]:
                matches = re.match(r"^\s*([\s\w\-]+\s*=)\s*([^\s]+)", line)
                if matches:
                    if "TOTAL IN" in line or "TOTAL OUT" in line:
                        continue
                    splitter = matches.group(1)
                    _, part2 = re.split(splitter, line)[-2:]
                    thisval = float(part2.split()[0])
                    pkgtype = re.sub(r"\s+", "_", re.sub(r"\s*=\s*", "", splitter))
                    pkgname = "%s:%s" % (
                        pkgtype,
                        part2.split()[1],
                    )  # modflow6 format
                    df_data_out.at[budgetblock_counter, pkgname + postfix] = thisval
        return df_data_out
