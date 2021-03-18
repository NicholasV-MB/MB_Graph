from setuptools import setup
from Cython.Build import cythonize

setup(
    #package_dir={'MB_Calendar': 'MB_Calendar'},
    ext_modules = cythonize("MB_Calendar/c_utils.pyx")
)
