#!/usr/bin/env python
from pathlib import Path
import os, re
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from enum import Enum
class status(Enum):
    NO_OPERATION = 0
    VOLUME = 1
    VOLUME_IN = 2
    VOLUME_OUT = 3

def listfile2df(file_in):
    ignore = ["IN - OUT","DISCREPANCY"]
    df_data_out = pd.DataFrame()
    df_data_out_cumulative = pd.DataFrame()
    data_out_cumulative = {}
    with open(file_in,"r") as fnin_mflist: 
        stat = status.NO_OPERATION
        for regel in fnin_mflist:
            if re.match(r"^.*TIME SUMMARY", regel):
                stat=status.NO_OPERATION
                continue
            if re.match(r"\s*OUT:\s+OUT:",regel):
                stat=status.VOLUME_OUT
                postfix = "_OUT"
                continue
            if re.match(r"\s*IN:\s+IN:",regel):
                stat=status.VOLUME_IN
                postfix = "_IN"
                continue
            m = re.match(r"^\s*VOLUME.* BUDGET.*STRESS PERIOD\s+(\d+)", regel)
            if m:
                stress_period = int(m.group(1)) - 1
                stat=status.VOLUME
                continue
            if any([pattern in regel for pattern in ignore]):
                continue
            if stat in [status.VOLUME_IN, status.VOLUME_OUT]:
                m=re.match(r"^\s+([\s\w\-]+\s*=\s*)([^\s]+)",regel)
                if m:
                    splitter = m.group(1)
                    part1, part2 = re.split(splitter,regel)[-2:]
                    cumval = float(part1)
                    thisval = float(part2.split()[0])

                    pkgtype = re.sub(r"\s+","_",re.sub(r"\s*=\s*","",splitter)) 
                    pkgname = pkgtype
                    try:
                            pkgname = "%s:%s"%(pkgtype,part2.split()[1])   # modflow6 format
                    except:
                        pass
                    df_data_out.at[stress_period,pkgname+postfix] = thisval
                    df_data_out_cumulative.at[stress_period,pkgname+postfix] = cumval
                continue
        return df_data_out, df_data_out_cumulative
    



# output_dir = Path(r"c:\werkmap")
# model_name = 'T-MODEL-D'
# path_mf_listing = r"c:\werkmap\Lumbricus_MF6\test-modellen\mf6\T-MODEL-D\GWF_1"

if __name__ == '__main__':
#   output_dir = path_mf_listing        # output dir = input dir
    output_dir = '.'                    # output dir = cwd
    if len(sys.argv)>3:
        output_dir = sys.argv[3]        # 3 = optional output directory
    
    file_in = sys.argv[1]
    df_data_out, df_data_out_cumulative = listfile2df(file_in)
    
    df_data_out.to_csv(os.path.join(output_dir, 'waterbalance.csv'), float_format="%10.2f",index=True)
    df_data_out_cumulative.to_csv(os.path.join(output_dir, 'waterbalance_cumulative.csv'), float_format="%10.2f",index=True)
