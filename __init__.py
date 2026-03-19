# -*- coding: utf-8 -*-
import numbers

from . import coordTransform as _py

try:
    from . import _coordTransform as _c
    HAS_C_EXTENSION = True
except ImportError:
    _c = None
    HAS_C_EXTENSION = False

try:
    import numpy as _np
except Exception:
    _np = None


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
    return _dispatch(_py.gcj02_to_bd09, "gcj02_to_bd09", lng, lat)


def bd09_to_gcj02(lng, lat=None):
    return _dispatch(_py.bd09_to_gcj02, "bd09_to_gcj02", lng, lat)


def wgs84_to_gcj02(lng, lat=None):
    return _dispatch(_py.wgs84_to_gcj02, "wgs84_to_gcj02", lng, lat)


def gcj02_to_wgs84(lng, lat=None):
    return _dispatch(_py.gcj02_to_wgs84, "gcj02_to_wgs84", lng, lat)


def bd09_to_wgs84(lng, lat=None):
    return _dispatch(_py.bd09_to_wgs84, "bd09_to_wgs84", lng, lat)


def wgs84_to_bd09(lng, lat=None):
    return _dispatch(_py.wgs84_to_bd09, "wgs84_to_bd09", lng, lat)


out_of_china = _py.out_of_china
_transformlat = _py._transformlat
_transformlng = _py._transformlng

__all__ = [
    "gcj02_to_bd09",
    "bd09_to_gcj02",
    "wgs84_to_gcj02",
    "gcj02_to_wgs84",
    "bd09_to_wgs84",
    "wgs84_to_bd09",
    "out_of_china",
]


