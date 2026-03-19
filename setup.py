#!/usr/bin/env python
# -*- coding:utf-8 -*-

from pathlib import Path
import sys
from setuptools import Extension, setup

ROOT = Path(__file__).resolve().parent
LONG_DESCRIPTION = (ROOT / "README.md").read_text(encoding="utf-8")

LIBRARIES = []
if sys.platform != "win32":
    LIBRARIES.append("m")

EXT_MODULES = [
    Extension(
        "coordTransform._coordTransform",
        sources=["src/_coordTransform.c"],
        libraries=LIBRARIES,
    )
]

setup(
    name="coordTransform",
    version="0.2.1",
    description="Coordinate transformation for maps",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/pkufool/coordTransform.git",
    author="kingway8816",
    author_email="njukingway@163.com",
    packages=["coordTransform"],
    package_dir={"coordTransform": "."},
    include_package_data=True,
    ext_modules=EXT_MODULES,
    platforms="any",
    python_requires=">=3.8",
    install_requires=[],
)