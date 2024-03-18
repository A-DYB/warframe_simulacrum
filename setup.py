from setuptools import setup, Extension
from Cython.Build import cythonize
# python setup.py build_ext --inplace

extensions = [Extension("unit", ["unit.pyx"]), Extension("weapon", ["weapon.pyx"])]
setup(
    ext_modules=cythonize(
        extensions,  
        ),                 
)