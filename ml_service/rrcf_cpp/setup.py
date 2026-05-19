import os
from setuptools import setup, Extension
import pybind11

cpp_args = ['-std=c++17', '-O3', '-march=native', '-ffast-math', '-DNDEBUG']

ext_modules = [
    Extension(
        '_rrcf_core',
        sources=['src/bindings.cpp'],
        include_dirs=[
            pybind11.get_include(),
            pybind11.get_include(user=True),
            os.path.join(os.path.dirname(__file__), 'include'),
        ],
        language='c++',
        extra_compile_args=cpp_args,
    ),
]

setup(
    name='_rrcf_core',
    version='1.0.0',
    description='C++ accelerated RRCF',
    ext_modules=ext_modules,
)
