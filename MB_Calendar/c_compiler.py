import shutil
import subprocess
from pathlib import Path

def run_cython_compiler():
    src=str(Path(__file__).resolve().parent).replace("\\", "/")+"/planner_utils_to_c.py"
    dst=str(Path(__file__).resolve().parent).replace("\\", "/")+"/c_utils.pyx"
    shutil.copy(src,dst)
    r = subprocess.call("python MB_Calendar\setup_c_utils.py build_ext --inplace", shell=True)
