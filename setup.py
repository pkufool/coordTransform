#!/usr/bin/env python
#-*- coding:utf-8 -*-

#############################################
# File Name: setup.py
# Author: kingway8816
# Mail: njukingway@163.com
# Created Time:  2018-7-28 01:25:34 AM
#############################################


from setuptools import setup, find_packages

setup(
    name = "coordtransform",
    version = "0.1.1",
    description = "Coordinate transformation for maps",
    long_description = "Coordinate transformation for maps",
    license = "MIT Licence",

    url = "https://github.com/pkufool/coordTransform.git",
    author = "kingway8816",
    author_email = "njukingway@163.com",

    packages = find_packages(),
    include_package_data = True,
    platforms = "any",
    install_requires = [""]
)