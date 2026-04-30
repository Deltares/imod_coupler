from imod_coupler.__main__ import run_coupler
from pathlib import Path
import os

#modeldir = 'd:\\leander\\imod_coupler\\vanFrans\snellius\\Testmodel-Snellius\\TA-MF6-reken\\'
#modelconfig = 'ZZL_BASIS50_TA-MF6-reken.TOML'
modeldir = 'D:\\leander\\MetaSWAP\\test_compare_megaswap\\bofek\\'
modelconfig = 'imod_coupler_sss.toml'
os.chdir(Path(modeldir))

print ("PID = :", os.getpid())
input("Press Enter to continue...")

run_coupler(Path(modeldir) / Path(modelconfig))