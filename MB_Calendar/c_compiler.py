import shutil
import subprocess
import filecmp
from pathlib import Path
from MB_Calendar.planner_utils_to_c import *

def run_cython_compiler():
    src=str(Path(__file__).resolve().parent).replace("\\", "/")+"/planner_utils_to_c.py"
    dst=str(Path(__file__).resolve().parent).replace("\\", "/")+"/c_utils.pyx"
    no_changes = filecmp.cmp(src, dst) 
    if no_changes==False:
        shutil.copy(src,dst)
        r = subprocess.call("python MB_Calendar\setup_c_utils.py build_ext --inplace", shell=True)
