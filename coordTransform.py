# -*- coding: utf-8 -*-
import math
import numbers

x_pi = 3.14159265358979324 * 3000.0 / 180.0
pi = 3.1415926535897932384626  # π
a = 6378245.0  # 长半轴
ee = 0.00669342162296594323  # 偏心率平方

try:
    from . import _coordTransform as _c
    HAS_C_EXTENSION = True
except Exception:
    try:
        import _coordTransform as _c
        HAS_C_EXTENSION = True
    except Exception:
        _c = None
        HAS_C_EXTENSION = False

try:
    import numpy as _np
except Exception:
    _np = None


def gcj02_to_bd09(lng, lat):
    """
    火星坐标系(GCJ-02)转百度坐标系(BD-09)
    谷歌、高德——>百度
    :param lng:火星坐标经度
    :param lat:火星坐标纬度
    :return:
    """
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * x_pi)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * x_pi)
    bd_lng = z * math.cos(theta) + 0.0065
    bd_lat = z * math.sin(theta) + 0.006
    return [bd_lng, bd_lat]


def bd09_to_gcj02(bd_lon, bd_lat):
    """
    百度坐标系(BD-09)转火星坐标系(GCJ-02)
    百度——>谷歌、高德
    :param bd_lat:百度坐标纬度
    :param bd_lon:百度坐标经度
    :return:转换后的坐标列表形式
    """
    x = bd_lon - 0.0065
    y = bd_lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)
    gg_lng = z * math.cos(theta)
    gg_lat = z * math.sin(theta)
    return [gg_lng, gg_lat]


def wgs84_to_gcj02(lng, lat):
    """
    WGS84转GCJ02(火星坐标系)
    :param lng:WGS84坐标系的经度
    :param lat:WGS84坐标系的纬度
    :return:
    """
    if out_of_china(lng, lat):  # 判断是否在国内
        return [lng, lat]
    dlat = _transformlat(lng - 105.0, lat - 35.0)
    dlng = _transformlng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
    mglat = lat + dlat
    mglng = lng + dlng
    return [mglng, mglat]


def gcj02_to_wgs84(lng, lat):
    """
    GCJ02(火星坐标系)转GPS84
    :param lng:火星坐标系的经度
    :param lat:火星坐标系纬度
    :return:
    """
    if out_of_china(lng, lat):
        return [lng, lat]
    dlat = _transformlat(lng - 105.0, lat - 35.0)
    dlng = _transformlng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
    mglat = lat + dlat
    mglng = lng + dlng
    return [lng * 2 - mglng, lat * 2 - mglat]


def bd09_to_wgs84(bd_lon, bd_lat):
    lon, lat = bd09_to_gcj02(bd_lon, bd_lat)
    return gcj02_to_wgs84(lon, lat)


def wgs84_to_bd09(lon, lat):
    lon, lat = wgs84_to_gcj02(lon, lat)
    return gcj02_to_bd09(lon, lat)


def _transformlat(lng, lat):
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + \
          0.1 * lng * lat + 0.2 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 *
            math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * pi) + 40.0 *
            math.sin(lat / 3.0 * pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * pi) + 320 *
            math.sin(lat * pi / 30.0)) * 2.0 / 3.0
    return ret


def _transformlng(lng, lat):
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + \
          0.1 * lng * lat + 0.1 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 *
            math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * pi) + 40.0 *
            math.sin(lng / 3.0 * pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * pi) + 300.0 *
            math.sin(lng / 30.0 * pi)) * 2.0 / 3.0
    return ret


def out_of_china(lng, lat):
    """
    判断是否在国内，不在国内不做偏移
    :param lng:
    :param lat:
    :return:
    """
    return not (lng > 73.66 and lng < 135.05 and lat > 3.86 and lat < 53.55)


_py_gcj02_to_bd09 = gcj02_to_bd09
_py_bd09_to_gcj02 = bd09_to_gcj02
_py_wgs84_to_gcj02 = wgs84_to_gcj02
_py_gcj02_to_wgs84 = gcj02_to_wgs84
_py_bd09_to_wgs84 = bd09_to_wgs84
_py_wgs84_to_bd09 = wgs84_to_bd09


def _is_scalar(value):
    return isinstance(value, numbers.Real)


def _is_array_like(value):
    if _is_scalar(value):
        return False
    if isinstance(value, (str, bytes, bytearray)):
        return False
    try:
        len(value)
    except TypeError:
        return False
    return True


def _as_buffer(value):
    if _np is None:
        return value
    if isinstance(value, _np.ndarray):
        if value.dtype != _np.float64 or not value.flags.c_contiguous:
            value = _np.ascontiguousarray(value, dtype=_np.float64)
        return memoryview(value)
    return value


def _batch_from_arrays_py(func, lngs, lats):
    if len(lngs) != len(lats):
        raise ValueError("lngs and lats must have the same length")
    out_lngs = []
    out_lats = []
    for lng, lat in zip(lngs, lats):
        out_lng, out_lat = func(lng, lat)
        out_lngs.append(out_lng)
        out_lats.append(out_lat)
    return out_lngs, out_lats


def _batch_from_pairs_py(func, points):
    out = []
    for lng, lat in points:
        out.append(func(lng, lat))
    return out


_C_FUNCS = {}
if _c is not None:
    def _c_get(name):
        return getattr(_c, name, None)

    _C_FUNCS = {
        "gcj02_to_bd09": (_c_get("gcj02_to_bd09_batch_xy"), _c_get("gcj02_to_bd09_batch_pairs")),
        "bd09_to_gcj02": (_c_get("bd09_to_gcj02_batch_xy"), _c_get("bd09_to_gcj02_batch_pairs")),
        "wgs84_to_gcj02": (_c_get("wgs84_to_gcj02_batch_xy"), _c_get("wgs84_to_gcj02_batch_pairs")),
        "gcj02_to_wgs84": (_c_get("gcj02_to_wgs84_batch_xy"), _c_get("gcj02_to_wgs84_batch_pairs")),
        "bd09_to_wgs84": (_c_get("bd09_to_wgs84_batch_xy"), _c_get("bd09_to_wgs84_batch_pairs")),
        "wgs84_to_bd09": (_c_get("wgs84_to_bd09_batch_xy"), _c_get("wgs84_to_bd09_batch_pairs")),
    }


def _dispatch(func_py, name, lng, lat):
    func_c_xy, func_c_pairs = _C_FUNCS.get(name, (None, None))
    if lat is None:
        if not _is_array_like(lng):
            raise TypeError("points must be a sequence of (lng, lat)")
        if func_c_pairs is not None:
            return func_c_pairs(lng)
        return _batch_from_pairs_py(func_py, lng)
    if _is_scalar(lng) and _is_scalar(lat):
        return func_py(lng, lat)
    if _is_array_like(lng) and _is_array_like(lat):
        if func_c_xy is not None:
            return func_c_xy(_as_buffer(lng), _as_buffer(lat))
        return _batch_from_arrays_py(func_py, lng, lat)
    raise TypeError("lng and lat must be both scalars or both sequences")


def gcj02_to_bd09(lng, lat=None):
    return _dispatch(_py_gcj02_to_bd09, "gcj02_to_bd09", lng, lat)


def bd09_to_gcj02(lng, lat=None):
    return _dispatch(_py_bd09_to_gcj02, "bd09_to_gcj02", lng, lat)


def wgs84_to_gcj02(lng, lat=None):
    return _dispatch(_py_wgs84_to_gcj02, "wgs84_to_gcj02", lng, lat)


def gcj02_to_wgs84(lng, lat=None):
    return _dispatch(_py_gcj02_to_wgs84, "gcj02_to_wgs84", lng, lat)


def bd09_to_wgs84(lng, lat=None):
    return _dispatch(_py_bd09_to_wgs84, "bd09_to_wgs84", lng, lat)


def wgs84_to_bd09(lng, lat=None):
    return _dispatch(_py_wgs84_to_bd09, "wgs84_to_bd09", lng, lat)


if __name__ == '__main__':
    lng = 128.543
    lat = 37.065
    result1 = gcj02_to_bd09(lng, lat)
    result2 = bd09_to_gcj02(lng, lat)
    result3 = wgs84_to_gcj02(lng, lat)
    result4 = gcj02_to_wgs84(lng, lat)
    result5 = bd09_to_wgs84(lng, lat)
    result6 = wgs84_to_bd09(lng, lat)

    print (result1, result2, result3, result4, result5, result6)
