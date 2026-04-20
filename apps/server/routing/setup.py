from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        "astar",
        ["astar.pyx"],
        language="c++",
        extra_compile_args=["-O3", "-std=c++11"],
    )
]

setup(
    name="EventFlowRouting",
    ext_modules=cythonize(extensions, annotate=True),
)
