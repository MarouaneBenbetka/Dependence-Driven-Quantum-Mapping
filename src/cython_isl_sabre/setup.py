# setup.py
from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension("dag", ["dag.pyx"]),
    Extension("isl_to_python", ["isl_to_python.pyx"]),
    Extension("python_to_isl", ["python_to_isl.pyx"]),
    Extension("poly_heuristic", ["poly_heuristic.pyx"]),
    Extension("poly_circuit_preprocess", ["poly_circuit_preprocess.pyx"]),
    Extension("poly_circuit_utils", ["poly_circuit_utils.pyx"]),
    Extension("poly_sabre", ["poly_sabre.pyx"]),
]

setup(
    name="cython_isl_sabre",
    ext_modules=cythonize(
        extensions,
        language_level="3",
        compiler_directives={
            "boundscheck": False,
            "wraparound": False,
        },
    ),
)
