#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <math.h>
#include <string.h>

static const double kXPi = 3.14159265358979324 * 3000.0 / 180.0;
static const double kPi = 3.1415926535897932384626;
static const double kA = 6378245.0;
static const double kEe = 0.00669342162296594323;

typedef void (*TransformFunc)(double, double, double *, double *);

typedef struct {
    double *data;
    Py_ssize_t len;
    int needs_free;
    int has_view;
    Py_buffer view;
} DoubleArray;

static void init_double_array(DoubleArray *arr) {
    arr->data = NULL;
    arr->len = 0;
    arr->needs_free = 0;
    arr->has_view = 0;
}

static void release_double_array(DoubleArray *arr) {
    if (arr->has_view) {
        PyBuffer_Release(&arr->view);
        arr->has_view = 0;
    }
    if (arr->needs_free && arr->data) {
        PyMem_Free(arr->data);
    }
    arr->data = NULL;
    arr->len = 0;
    arr->needs_free = 0;
}

static int format_ends_with(const char *fmt, char code) {
    size_t len = fmt ? strlen(fmt) : 0;
    return len > 0 && fmt[len - 1] == code;
}

static int load_double_array(PyObject *obj, DoubleArray *out, const char *name) {
    init_double_array(out);
    if (obj == Py_None) {
        PyErr_Format(PyExc_TypeError, "%s must not be None", name);
        return -1;
    }

    Py_buffer view;
    if (PyObject_GetBuffer(obj, &view, PyBUF_FORMAT | PyBUF_C_CONTIGUOUS | PyBUF_ND) == 0) {
        if (view.ndim == 1 && view.itemsize > 0) {
            Py_ssize_t n = view.len / view.itemsize;
            if (format_ends_with(view.format, 'd')) {
                out->data = (double *)view.buf;
                out->len = n;
                out->has_view = 1;
                out->view = view;
                return 0;
            }
            if (format_ends_with(view.format, 'f')) {
                if (n > 0) {
                    double *buf = PyMem_Malloc((size_t)n * sizeof(double));
                    if (!buf) {
                        PyBuffer_Release(&view);
                        PyErr_NoMemory();
                        return -1;
                    }
                    float *src = (float *)view.buf;
                    for (Py_ssize_t i = 0; i < n; i++) {
                        buf[i] = (double)src[i];
                    }
                    out->data = buf;
                    out->len = n;
                    out->needs_free = 1;
                    out->has_view = 1;
                    out->view = view;
                    return 0;
                }
                out->data = NULL;
                out->len = 0;
                out->has_view = 1;
                out->view = view;
                return 0;
            }
        }
        PyBuffer_Release(&view);
    } else {
        PyErr_Clear();
    }

    PyObject *seq = PySequence_Fast(obj, "Expected a sequence of numbers");
    if (!seq) {
        return -1;
    }
    Py_ssize_t n = PySequence_Fast_GET_SIZE(seq);
    if (n == 0) {
        Py_DECREF(seq);
        out->data = NULL;
        out->len = 0;
        out->needs_free = 0;
        return 0;
    }

    double *buf = PyMem_Malloc((size_t)n * sizeof(double));
    if (!buf) {
        Py_DECREF(seq);
        PyErr_NoMemory();
        return -1;
    }

    PyObject **items = PySequence_Fast_ITEMS(seq);
    for (Py_ssize_t i = 0; i < n; i++) {
        double val = PyFloat_AsDouble(items[i]);
        if (PyErr_Occurred()) {
            Py_DECREF(seq);
            PyMem_Free(buf);
            return -1;
        }
        buf[i] = val;
    }

    Py_DECREF(seq);
    out->data = buf;
    out->len = n;
    out->needs_free = 1;
    return 0;
}

static int load_pair_arrays(PyObject *obj, DoubleArray *lngs, DoubleArray *lats) {
    init_double_array(lngs);
    init_double_array(lats);

    PyObject *seq = PySequence_Fast(obj, "Expected a sequence of (lng, lat) pairs");
    if (!seq) {
        return -1;
    }

    Py_ssize_t n = PySequence_Fast_GET_SIZE(seq);
    if (n == 0) {
        Py_DECREF(seq);
        lngs->data = NULL;
        lats->data = NULL;
        lngs->len = 0;
        lats->len = 0;
        lngs->needs_free = 0;
        lats->needs_free = 0;
        return 0;
    }

    double *lng_buf = PyMem_Malloc((size_t)n * sizeof(double));
    double *lat_buf = PyMem_Malloc((size_t)n * sizeof(double));
    if (!lng_buf || !lat_buf) {
        Py_DECREF(seq);
        PyMem_Free(lng_buf);
        PyMem_Free(lat_buf);
        PyErr_NoMemory();
        return -1;
    }

    PyObject **items = PySequence_Fast_ITEMS(seq);
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *pair_seq = PySequence_Fast(items[i], "Each point must be length 2");
        if (!pair_seq) {
            Py_DECREF(seq);
            PyMem_Free(lng_buf);
            PyMem_Free(lat_buf);
            return -1;
        }
        if (PySequence_Fast_GET_SIZE(pair_seq) != 2) {
            Py_DECREF(pair_seq);
            Py_DECREF(seq);
            PyMem_Free(lng_buf);
            PyMem_Free(lat_buf);
            PyErr_SetString(PyExc_ValueError, "Each point must have 2 elements");
            return -1;
        }
        PyObject **pair_items = PySequence_Fast_ITEMS(pair_seq);
        double lng = PyFloat_AsDouble(pair_items[0]);
        if (PyErr_Occurred()) {
            Py_DECREF(pair_seq);
            Py_DECREF(seq);
            PyMem_Free(lng_buf);
            PyMem_Free(lat_buf);
            return -1;
        }
        double lat = PyFloat_AsDouble(pair_items[1]);
        Py_DECREF(pair_seq);
        if (PyErr_Occurred()) {
            Py_DECREF(seq);
            PyMem_Free(lng_buf);
            PyMem_Free(lat_buf);
            return -1;
        }
        lng_buf[i] = lng;
        lat_buf[i] = lat;
    }

    Py_DECREF(seq);
    lngs->data = lng_buf;
    lats->data = lat_buf;
    lngs->len = n;
    lats->len = n;
    lngs->needs_free = 1;
    lats->needs_free = 1;
    return 0;
}

static PyObject *build_xy_lists(Py_ssize_t n, const double *lngs, const double *lats) {
    PyObject *lng_list = PyList_New(n);
    PyObject *lat_list = PyList_New(n);
    if (!lng_list || !lat_list) {
        Py_XDECREF(lng_list);
        Py_XDECREF(lat_list);
        return NULL;
    }

    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *py_lng = PyFloat_FromDouble(lngs[i]);
        PyObject *py_lat = PyFloat_FromDouble(lats[i]);
        if (!py_lng || !py_lat) {
            Py_XDECREF(py_lng);
            Py_XDECREF(py_lat);
            Py_DECREF(lng_list);
            Py_DECREF(lat_list);
            return NULL;
        }
        PyList_SET_ITEM(lng_list, i, py_lng);
        PyList_SET_ITEM(lat_list, i, py_lat);
    }

    PyObject *result = PyTuple_New(2);
    if (!result) {
        Py_DECREF(lng_list);
        Py_DECREF(lat_list);
        return NULL;
    }
    PyTuple_SET_ITEM(result, 0, lng_list);
    PyTuple_SET_ITEM(result, 1, lat_list);
    return result;
}

static PyObject *build_pairs_list(Py_ssize_t n, const double *lngs, const double *lats) {
    PyObject *pairs = PyList_New(n);
    if (!pairs) {
        return NULL;
    }

    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *pair = PyList_New(2);
        if (!pair) {
            Py_DECREF(pairs);
            return NULL;
        }
        PyObject *py_lng = PyFloat_FromDouble(lngs[i]);
        PyObject *py_lat = PyFloat_FromDouble(lats[i]);
        if (!py_lng || !py_lat) {
            Py_XDECREF(py_lng);
            Py_XDECREF(py_lat);
            Py_DECREF(pair);
            Py_DECREF(pairs);
            return NULL;
        }
        PyList_SET_ITEM(pair, 0, py_lng);
        PyList_SET_ITEM(pair, 1, py_lat);
        PyList_SET_ITEM(pairs, i, pair);
    }

    return pairs;
}

static PyObject *batch_xy(PyObject *lngs_obj, PyObject *lats_obj, TransformFunc func) {
    DoubleArray lngs;
    DoubleArray lats;
    init_double_array(&lngs);
    init_double_array(&lats);

    if (load_double_array(lngs_obj, &lngs, "lngs") < 0) {
        release_double_array(&lngs);
        return NULL;
    }
    if (load_double_array(lats_obj, &lats, "lats") < 0) {
        release_double_array(&lngs);
        release_double_array(&lats);
        return NULL;
    }

    if (lngs.len != lats.len) {
        release_double_array(&lngs);
        release_double_array(&lats);
        PyErr_SetString(PyExc_ValueError, "lngs and lats must have the same length");
        return NULL;
    }

    Py_ssize_t n = lngs.len;
    double *out_lngs = NULL;
    double *out_lats = NULL;
    if (n > 0) {
        out_lngs = PyMem_Malloc((size_t)n * sizeof(double));
        out_lats = PyMem_Malloc((size_t)n * sizeof(double));
        if (!out_lngs || !out_lats) {
            PyMem_Free(out_lngs);
            PyMem_Free(out_lats);
            release_double_array(&lngs);
            release_double_array(&lats);
            PyErr_NoMemory();
            return NULL;
        }

        Py_BEGIN_ALLOW_THREADS
        for (Py_ssize_t i = 0; i < n; i++) {
            func(lngs.data[i], lats.data[i], &out_lngs[i], &out_lats[i]);
        }
        Py_END_ALLOW_THREADS
    }

    PyObject *result = build_xy_lists(n, out_lngs, out_lats);

    PyMem_Free(out_lngs);
    PyMem_Free(out_lats);
    release_double_array(&lngs);
    release_double_array(&lats);
    return result;
}

static PyObject *batch_pairs(PyObject *points_obj, TransformFunc func) {
    DoubleArray lngs;
    DoubleArray lats;
    init_double_array(&lngs);
    init_double_array(&lats);

    if (load_pair_arrays(points_obj, &lngs, &lats) < 0) {
        release_double_array(&lngs);
        release_double_array(&lats);
        return NULL;
    }

    Py_ssize_t n = lngs.len;
    double *out_lngs = NULL;
    double *out_lats = NULL;
    if (n > 0) {
        out_lngs = PyMem_Malloc((size_t)n * sizeof(double));
        out_lats = PyMem_Malloc((size_t)n * sizeof(double));
        if (!out_lngs || !out_lats) {
            PyMem_Free(out_lngs);
            PyMem_Free(out_lats);
            release_double_array(&lngs);
            release_double_array(&lats);
            PyErr_NoMemory();
            return NULL;
        }

        Py_BEGIN_ALLOW_THREADS
        for (Py_ssize_t i = 0; i < n; i++) {
            func(lngs.data[i], lats.data[i], &out_lngs[i], &out_lats[i]);
        }
        Py_END_ALLOW_THREADS
    }

    PyObject *result = build_pairs_list(n, out_lngs, out_lats);

    PyMem_Free(out_lngs);
    PyMem_Free(out_lats);
    release_double_array(&lngs);
    release_double_array(&lats);
    return result;
}

static int out_of_china(double lng, double lat) {
    return !(lng > 73.66 && lng < 135.05 && lat > 3.86 && lat < 53.55);
}

static double transform_lat(double lng, double lat) {
    double ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat +
                 0.1 * lng * lat + 0.2 * sqrt(fabs(lng));
    ret += (20.0 * sin(6.0 * lng * kPi) + 20.0 * sin(2.0 * lng * kPi)) * 2.0 / 3.0;
    ret += (20.0 * sin(lat * kPi) + 40.0 * sin(lat / 3.0 * kPi)) * 2.0 / 3.0;
    ret += (160.0 * sin(lat / 12.0 * kPi) + 320.0 * sin(lat * kPi / 30.0)) * 2.0 / 3.0;
    return ret;
}

static double transform_lng(double lng, double lat) {
    double ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng +
                 0.1 * lng * lat + 0.1 * sqrt(fabs(lng));
    ret += (20.0 * sin(6.0 * lng * kPi) + 20.0 * sin(2.0 * lng * kPi)) * 2.0 / 3.0;
    ret += (20.0 * sin(lng * kPi) + 40.0 * sin(lng / 3.0 * kPi)) * 2.0 / 3.0;
    ret += (150.0 * sin(lng / 12.0 * kPi) + 300.0 * sin(lng / 30.0 * kPi)) * 2.0 / 3.0;
    return ret;
}

static void gcj02_to_bd09_inner(double lng, double lat, double *out_lng, double *out_lat) {
    double z = sqrt(lng * lng + lat * lat) + 0.00002 * sin(lat * kXPi);
    double theta = atan2(lat, lng) + 0.000003 * cos(lng * kXPi);
    *out_lng = z * cos(theta) + 0.0065;
    *out_lat = z * sin(theta) + 0.006;
}

static void bd09_to_gcj02_inner(double bd_lon, double bd_lat, double *out_lng, double *out_lat) {
    double x = bd_lon - 0.0065;
    double y = bd_lat - 0.006;
    double z = sqrt(x * x + y * y) - 0.00002 * sin(y * kXPi);
    double theta = atan2(y, x) - 0.000003 * cos(x * kXPi);
    *out_lng = z * cos(theta);
    *out_lat = z * sin(theta);
}

static void wgs84_to_gcj02_inner(double lng, double lat, double *out_lng, double *out_lat) {
    if (out_of_china(lng, lat)) {
        *out_lng = lng;
        *out_lat = lat;
        return;
    }
    double dlat = transform_lat(lng - 105.0, lat - 35.0);
    double dlng = transform_lng(lng - 105.0, lat - 35.0);
    double radlat = lat / 180.0 * kPi;
    double magic = sin(radlat);
    magic = 1 - kEe * magic * magic;
    double sqrtmagic = sqrt(magic);
    dlat = (dlat * 180.0) / ((kA * (1 - kEe)) / (magic * sqrtmagic) * kPi);
    dlng = (dlng * 180.0) / (kA / sqrtmagic * cos(radlat) * kPi);
    *out_lat = lat + dlat;
    *out_lng = lng + dlng;
}

static void gcj02_to_wgs84_inner(double lng, double lat, double *out_lng, double *out_lat) {
    if (out_of_china(lng, lat)) {
        *out_lng = lng;
        *out_lat = lat;
        return;
    }
    double dlat = transform_lat(lng - 105.0, lat - 35.0);
    double dlng = transform_lng(lng - 105.0, lat - 35.0);
    double radlat = lat / 180.0 * kPi;
    double magic = sin(radlat);
    magic = 1 - kEe * magic * magic;
    double sqrtmagic = sqrt(magic);
    dlat = (dlat * 180.0) / ((kA * (1 - kEe)) / (magic * sqrtmagic) * kPi);
    dlng = (dlng * 180.0) / (kA / sqrtmagic * cos(radlat) * kPi);
    double mglat = lat + dlat;
    double mglng = lng + dlng;
    *out_lng = lng * 2 - mglng;
    *out_lat = lat * 2 - mglat;
}

static void bd09_to_wgs84_inner(double bd_lon, double bd_lat, double *out_lng, double *out_lat) {
    double lng = 0.0;
    double lat = 0.0;
    bd09_to_gcj02_inner(bd_lon, bd_lat, &lng, &lat);
    gcj02_to_wgs84_inner(lng, lat, out_lng, out_lat);
}

static void wgs84_to_bd09_inner(double lng, double lat, double *out_lng, double *out_lat) {
    double gcj_lng = 0.0;
    double gcj_lat = 0.0;
    wgs84_to_gcj02_inner(lng, lat, &gcj_lng, &gcj_lat);
    gcj02_to_bd09_inner(gcj_lng, gcj_lat, out_lng, out_lat);
}

#define DEFINE_BATCH_FUNCS(name, func) \
    static PyObject *py_##name##_batch_xy(PyObject *self, PyObject *args) { \
        PyObject *lngs = NULL; \
        PyObject *lats = NULL; \
        if (!PyArg_ParseTuple(args, "OO", &lngs, &lats)) { \
            return NULL; \
        } \
        return batch_xy(lngs, lats, func); \
    } \
    static PyObject *py_##name##_batch_pairs(PyObject *self, PyObject *args) { \
        PyObject *points = NULL; \
        if (!PyArg_ParseTuple(args, "O", &points)) { \
            return NULL; \
        } \
        return batch_pairs(points, func); \
    }

DEFINE_BATCH_FUNCS(gcj02_to_bd09, gcj02_to_bd09_inner)
DEFINE_BATCH_FUNCS(bd09_to_gcj02, bd09_to_gcj02_inner)
DEFINE_BATCH_FUNCS(wgs84_to_gcj02, wgs84_to_gcj02_inner)
DEFINE_BATCH_FUNCS(gcj02_to_wgs84, gcj02_to_wgs84_inner)
DEFINE_BATCH_FUNCS(bd09_to_wgs84, bd09_to_wgs84_inner)
DEFINE_BATCH_FUNCS(wgs84_to_bd09, wgs84_to_bd09_inner)

static PyObject *py_out_of_china(PyObject *self, PyObject *args) {
    double lng = 0.0;
    double lat = 0.0;
    if (!PyArg_ParseTuple(args, "dd", &lng, &lat)) {
        return NULL;
    }
    return PyBool_FromLong(out_of_china(lng, lat));
}

static PyObject *py_transformlat(PyObject *self, PyObject *args) {
    double lng = 0.0;
    double lat = 0.0;
    if (!PyArg_ParseTuple(args, "dd", &lng, &lat)) {
        return NULL;
    }
    double result = 0.0;
    Py_BEGIN_ALLOW_THREADS
    result = transform_lat(lng, lat);
    Py_END_ALLOW_THREADS
    return PyFloat_FromDouble(result);
}

static PyObject *py_transformlng(PyObject *self, PyObject *args) {
    double lng = 0.0;
    double lat = 0.0;
    if (!PyArg_ParseTuple(args, "dd", &lng, &lat)) {
        return NULL;
    }
    double result = 0.0;
    Py_BEGIN_ALLOW_THREADS
    result = transform_lng(lng, lat);
    Py_END_ALLOW_THREADS
    return PyFloat_FromDouble(result);
}

static PyMethodDef kMethods[] = {
    {"gcj02_to_bd09_batch_xy", py_gcj02_to_bd09_batch_xy, METH_VARARGS, NULL},
    {"gcj02_to_bd09_batch_pairs", py_gcj02_to_bd09_batch_pairs, METH_VARARGS, NULL},
    {"bd09_to_gcj02_batch_xy", py_bd09_to_gcj02_batch_xy, METH_VARARGS, NULL},
    {"bd09_to_gcj02_batch_pairs", py_bd09_to_gcj02_batch_pairs, METH_VARARGS, NULL},
    {"wgs84_to_gcj02_batch_xy", py_wgs84_to_gcj02_batch_xy, METH_VARARGS, NULL},
    {"wgs84_to_gcj02_batch_pairs", py_wgs84_to_gcj02_batch_pairs, METH_VARARGS, NULL},
    {"gcj02_to_wgs84_batch_xy", py_gcj02_to_wgs84_batch_xy, METH_VARARGS, NULL},
    {"gcj02_to_wgs84_batch_pairs", py_gcj02_to_wgs84_batch_pairs, METH_VARARGS, NULL},
    {"bd09_to_wgs84_batch_xy", py_bd09_to_wgs84_batch_xy, METH_VARARGS, NULL},
    {"bd09_to_wgs84_batch_pairs", py_bd09_to_wgs84_batch_pairs, METH_VARARGS, NULL},
    {"wgs84_to_bd09_batch_xy", py_wgs84_to_bd09_batch_xy, METH_VARARGS, NULL},
    {"wgs84_to_bd09_batch_pairs", py_wgs84_to_bd09_batch_pairs, METH_VARARGS, NULL},
    {"out_of_china", py_out_of_china, METH_VARARGS, NULL},
    {"_transformlat", py_transformlat, METH_VARARGS, NULL},
    {"_transformlng", py_transformlng, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef kModule = {
    PyModuleDef_HEAD_INIT,
    "_coordTransform",
    NULL,
    -1,
    kMethods,
};

PyMODINIT_FUNC PyInit__coordTransform(void) {
    PyObject *module = PyModule_Create(&kModule);
    if (!module) {
        return NULL;
    }
    PyObject *value = PyFloat_FromDouble(kXPi);
    if (!value || PyModule_AddObject(module, "x_pi", value) < 0) {
        Py_XDECREF(value);
        Py_DECREF(module);
        return NULL;
    }
    value = PyFloat_FromDouble(kPi);
    if (!value || PyModule_AddObject(module, "pi", value) < 0) {
        Py_XDECREF(value);
        Py_DECREF(module);
        return NULL;
    }
    value = PyFloat_FromDouble(kA);
    if (!value || PyModule_AddObject(module, "a", value) < 0) {
        Py_XDECREF(value);
        Py_DECREF(module);
        return NULL;
    }
    value = PyFloat_FromDouble(kEe);
    if (!value || PyModule_AddObject(module, "ee", value) < 0) {
        Py_XDECREF(value);
        Py_DECREF(module);
        return NULL;
    }
    return module;
}
