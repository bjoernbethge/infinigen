# Copyright (C) 2023, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory
# of this source tree.

# Authors: Alexander Raistrick

# Acknowledgement: This file draws inspiration from https://github.com/pytorch/pytorch/blob/main/setup.py


import os
import subprocess
import sys
from pathlib import Path

import numpy
from Cython.Build import cythonize
from setuptools import Extension, setup

cwd = Path(__file__).parent

str_true = "True"
MINIMAL_INSTALL = os.environ.get("INFINIGEN_MINIMAL_INSTALL") == str_true
BUILD_TERRAIN = os.environ.get("INFINIGEN_INSTALL_TERRAIN", str_true) == str_true
BUILD_OPENGL = os.environ.get("INFINIGEN_INSTALL_CUSTOMGT", "False") == str_true
BUILD_BNURBS = os.environ.get("INFINIGEN_INSTALL_BNURBS", "False") == str_true

dont_build_steps = ["clean", "egg_info", "dist_info", "sdist", "--help"]
is_build_step = not any(x in sys.argv[1] for x in dont_build_steps)


def ensure_submodules():
    # Inspired by https://github.com/pytorch/pytorch/blob/main/setup.py
    # Only run during development, not during build
    
    # Skip submodule updates during build
    if "build" in sys.argv or "bdist" in sys.argv or "sdist" in sys.argv:
        print("Note: Skipping submodule updates during build")
        return

    try:
        with (cwd / ".gitmodules").open() as f:
            submodule_folders = [
                cwd / line.split("=", 1)[1].strip()
                for line in f.readlines()
                if line.strip().startswith("path")
            ]

        if any(not p.exists() or not any(p.iterdir()) for p in submodule_folders):
            subprocess.run(
                ["git", "submodule", "update", "--init", "--recursive"], cwd=cwd, check=True
            )
    except Exception as e:
        print(f"Warning: Could not update submodules: {e}")
        print("This is normal during build processes")


if not MINIMAL_INSTALL:
    ensure_submodules()

# inspired by https://github.com/pytorch/pytorch/blob/161ea463e690dcb91a30faacbf7d100b98524b6b/setup.py#L290
# theirs seems to not exclude dist_info but this causes duplicate compiling in my tests
if is_build_step and not MINIMAL_INSTALL:
    # Check if we're on Windows
    is_windows = sys.platform.startswith('win')
    
    if BUILD_TERRAIN and not is_windows:
        try:
            subprocess.run(["make", "terrain"], cwd=cwd, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: Failed to build terrain components. Continuing without terrain support.")
    
    if BUILD_OPENGL and not is_windows:
        try:
            subprocess.run(["make", "customgt"], cwd=cwd, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: Failed to build OpenGL components. Continuing without OpenGL support.")
    
    if is_windows:
        print("Note: On Windows, advanced features (terrain, OpenGL) are limited.")
        print("Core functionality is fully supported.")

cython_extensions = []

if not MINIMAL_INSTALL:
    # Only build Cython extensions on non-Windows platforms or if explicitly requested
    if BUILD_BNURBS and not sys.platform.startswith('win'):
        cython_extensions.append(
            Extension(
                name="bnurbs",
                sources=["infinigen/assets/utils/geometry/cpp_utils/bnurbs.pyx"],
                include_dirs=[numpy.get_include()],
            )
        )
    
    # Only build terrain extensions on non-Windows platforms
    if BUILD_TERRAIN and not sys.platform.startswith('win'):
        cython_extensions.append(
            Extension(
                name="infinigen.terrain.marching_cubes",
                sources=[
                    "infinigen/terrain/marching_cubes/_marching_cubes_lewiner_cy.pyx"
                ],
                include_dirs=[numpy.get_include()],
            )
        )

setup(
    ext_modules=[*cythonize(cython_extensions)]
    # other opts come from pyproject.toml
)
