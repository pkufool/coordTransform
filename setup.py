#!/usr/bin/env python
#-*- coding:utf-8 -*-

#############################################
# File Name: setup.py
# Author: kingway8816
# Mail: njukingway@163.com
# Created Time:  2018-9-8 22:25:34 AM
#############################################


from setuptools import setup, find_packages

LONGDOC = """
coordTransform
========
coordTransform 坐标转换模块用于百度坐标系(bd09)、火星坐标系(国测局坐标系、gcj02)、WGS84坐标系的相互转换。

主流地图使用坐标系
------------
-  百度地图: bd09
-  高德地图、谷歌地图（国内）: gcj02
-  高德地图、谷歌地图（国外）: wgs84
-  GPS原始坐标: wgs84

安装说明
-------------
Install using `pip <http://www.pip-installer.org/en/latest/>`__ with:
::

    pip install coordTransform

使用说明
--------
.. code::python
    import coordTransform as ct

    lng = 128.543
    lat = 37.065

    #火星坐标系->百度坐标系
    result1 = ct.gcj02_to_bd09(lng, lat)
    #百度坐标系->火星坐标系
    result2 = ct.bd09_to_gcj02(lng, lat)
    #WGS84坐标系->火星坐标系
    result3 = ct.wgs84_to_gcj02(lng, lat)
    #火星坐标系->WGS84坐标系
    result4 = ct.gcj02_to_wgs84(lng, lat)
    #百度坐标系->WGS84坐标系
    result5 = ct.bd09_to_wgs84(lng, lat)
    #WGS84坐标系->百度坐标系
    result6 = ct.wgs84_to_bd09(lng, lat)

    print (result1, result2, result3, result4, result5, result6)

坐标系简介
----------
- WGS－84原始坐标系，一般用国际GPS纪录仪记录下来的经纬度，通过GPS定位拿到的原始经纬度，Google和高德地图定位的的经纬度（国外）都是基于WGS－84坐标系的；但是在国内是不允许直接用WGS84坐标系标注的，必须经过加密后才能使用。
- GCJ－02坐标系，又名“火星坐标系”，是我国国测局独创的坐标体系，由WGS－84加密而成，在国内，必须至少使用GCJ－02坐标系，或者使用在GCJ－02加密后再进行加密的坐标系，如百度坐标系。高德和Google在国内都是使用GCJ－02坐标系，可以说，GCJ－02是国内最广泛使用的坐标系。
- 百度坐标系:bd-09，百度坐标系是在GCJ－02坐标系的基础上再次加密偏移后形成的坐标系，只适用于百度地图。
"""

setup(
    name = "coordTransform",
    version = "0.1.3",
    description = "Coordinate transformation for maps",
    long_description = LONGDOC,
    license = "MIT Licence",

    url = "https://github.com/pkufool/coordTransform.git",
    author = "kingway8816",
    author_email = "njukingway@163.com",

    packages = find_packages(),
    include_package_data = True,
    platforms = "any",
    install_requires = [""]
)