#!/usr/bin/env python
import argparse
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
if str(PARENT) not in sys.path:
    # Ensure the package import resolves to the repo directory, not coordTransform.py.
    sys.path.insert(0, str(PARENT))

try:
    import coordTransform.coordTransform as py_impl
except Exception:
    import importlib.util

    py_path = ROOT / "coordTransform.py"
    spec = importlib.util.spec_from_file_location("coordTransform_py", py_path)
    if spec is None or spec.loader is None:
        raise SystemExit("Failed to load pure-Python coordTransform.py.")
    py_impl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(py_impl)

try:
    import coordTransform._coordTransform as c_impl
except ImportError as exc:
    raise SystemExit(
        "C extension not available. Build it with 'pip install -e .' or 'python -m build'."
    ) from exc

try:
    import numpy as np
except Exception:
    np = None

FUNC_NAMES = [
    "gcj02_to_bd09",
    "bd09_to_gcj02",
    "wgs84_to_gcj02",
    "gcj02_to_wgs84",
    "bd09_to_wgs84",
    "wgs84_to_bd09",
]


def get_funcs(impl, names):
    return [getattr(impl, name) for name in names]


def get_c_funcs(names, input_mode):
    suffix = "_batch_pairs" if input_mode == "pairs" else "_batch_xy"
    return [getattr(c_impl, f"{name}{suffix}") for name in names]


def generate_points(count, seed, lng_min, lng_max, lat_min, lat_max, use_numpy):
    if use_numpy:
        if np is None:
            raise SystemExit("numpy is required for --use-numpy")
        rng = np.random.default_rng(seed)
        lngs = rng.uniform(lng_min, lng_max, size=count).astype("float64", copy=False)
        lats = rng.uniform(lat_min, lat_max, size=count).astype("float64", copy=False)
        return lngs, lats
    rng = random.Random(seed)
    lngs = [rng.uniform(lng_min, lng_max) for _ in range(count)]
    lats = [rng.uniform(lat_min, lat_max) for _ in range(count)]
    return lngs, lats


def run_range_arrays(lngs, lats, start, end, funcs):
    for i in range(start, end):
        lng = lngs[i]
        lat = lats[i]
        for fn in funcs:
            fn(lng, lat)


def run_range_pairs(points, start, end, funcs):
    for i in range(start, end):
        lng, lat = points[i]
        for fn in funcs:
            fn(lng, lat)


def run_batch_arrays(lngs, lats, funcs):
    for fn in funcs:
        fn(lngs, lats)


def run_batch_pairs(points, funcs):
    for fn in funcs:
        fn(points)


def benchmark_scalar_arrays(lngs, lats, funcs, threads):
    start = time.perf_counter()
    count = len(lngs)
    chunk = (count + threads - 1) // threads
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for idx in range(0, count, chunk):
            futures.append(
                executor.submit(run_range_arrays, lngs, lats, idx, min(idx + chunk, count), funcs)
            )
        for future in futures:
            future.result()
    return time.perf_counter() - start


def benchmark_scalar_pairs(points, funcs, threads):
    start = time.perf_counter()
    count = len(points)
    chunk = (count + threads - 1) // threads
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for idx in range(0, count, chunk):
            futures.append(
                executor.submit(run_range_pairs, points, idx, min(idx + chunk, count), funcs)
            )
        for future in futures:
            future.result()
    return time.perf_counter() - start


def benchmark_batch_arrays(lngs, lats, funcs, threads):
    start = time.perf_counter()
    count = len(lngs)
    chunk = (count + threads - 1) // threads
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for idx in range(0, count, chunk):
            sub_lngs = lngs[idx : min(idx + chunk, count)]
            sub_lats = lats[idx : min(idx + chunk, count)]
            futures.append(executor.submit(run_batch_arrays, sub_lngs, sub_lats, funcs))
        for future in futures:
            future.result()
    return time.perf_counter() - start


def benchmark_batch_pairs(points, funcs, threads):
    start = time.perf_counter()
    count = len(points)
    chunk = (count + threads - 1) // threads
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for idx in range(0, count, chunk):
            sub_points = points[idx : min(idx + chunk, count)]
            futures.append(executor.submit(run_batch_pairs, sub_points, funcs))
        for future in futures:
            future.result()
    return time.perf_counter() - start


def verify_arrays(lngs, lats, funcs_py, funcs_c, tol, sample, seed):
    rng = random.Random(seed + 1)
    total = len(lngs)
    if sample <= 0:
        return 0, 0.0
    if sample >= total:
        indices = list(range(total))
    else:
        indices = rng.sample(range(total), sample)

    sample_lngs = [lngs[i] for i in indices]
    sample_lats = [lats[i] for i in indices]

    mismatches = 0
    max_err = 0.0
    for fn_py, fn_c in zip(funcs_py, funcs_c):
        c_lngs, c_lats = fn_c(sample_lngs, sample_lats)
        for i, (lng, lat) in enumerate(zip(sample_lngs, sample_lats)):
            py_lng, py_lat = fn_py(lng, lat)
            err = max(abs(py_lng - c_lngs[i]), abs(py_lat - c_lats[i]))
            if err > max_err:
                max_err = err
            if err > tol:
                mismatches += 1
                if mismatches <= 5:
                    print(
                        "Mismatch",
                        indices[i],
                        fn_py.__name__,
                        "py=",
                        (py_lng, py_lat),
                        "c=",
                        (c_lngs[i], c_lats[i]),
                        "err=",
                        err,
                    )
    return mismatches, max_err


def verify_pairs(points, funcs_py, funcs_c, tol, sample, seed):
    rng = random.Random(seed + 1)
    total = len(points)
    if sample <= 0:
        return 0, 0.0
    if sample >= total:
        indices = list(range(total))
    else:
        indices = rng.sample(range(total), sample)

    sample_points = [points[i] for i in indices]
    mismatches = 0
    max_err = 0.0
    for fn_py, fn_c in zip(funcs_py, funcs_c):
        c_points = fn_c(sample_points)
        for i, (lng, lat) in enumerate(sample_points):
            py_lng, py_lat = fn_py(lng, lat)
            c_lng, c_lat = c_points[i]
            err = max(abs(py_lng - c_lng), abs(py_lat - c_lat))
            if err > max_err:
                max_err = err
            if err > tol:
                mismatches += 1
                if mismatches <= 5:
                    print(
                        "Mismatch",
                        indices[i],
                        fn_py.__name__,
                        "py=",
                        (py_lng, py_lat),
                        "c=",
                        (c_lng, c_lat),
                        "err=",
                        err,
                    )
    return mismatches, max_err


def parse_args():
    parser = argparse.ArgumentParser(
        description="Benchmark Python vs C coordTransform with multithreading."
    )
    parser.add_argument("--points", type=int, default=1_000_000)
    parser.add_argument("--threads", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verify-samples", type=int, default=10_000)
    parser.add_argument("--tol", type=float, default=1e-9)
    parser.add_argument("--function", default="all", choices=["all"] + FUNC_NAMES)
    parser.add_argument("--input", default="arrays", choices=["arrays", "pairs"])
    parser.add_argument("--use-numpy", action="store_true")
    parser.add_argument("--lng-min", type=float, default=70.0)
    parser.add_argument("--lng-max", type=float, default=140.0)
    parser.add_argument("--lat-min", type=float, default=3.0)
    parser.add_argument("--lat-max", type=float, default=54.0)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.function == "all":
        names = FUNC_NAMES
    else:
        names = [args.function]

    lngs, lats = generate_points(
        args.points,
        args.seed,
        args.lng_min,
        args.lng_max,
        args.lat_min,
        args.lat_max,
        args.use_numpy,
    )

    points = list(zip(lngs, lats)) if args.input == "pairs" else None

    funcs_py = get_funcs(py_impl, names)
    funcs_c = get_c_funcs(names, args.input)

    warm = min(1000, len(lngs))
    if warm:
        if args.input == "pairs":
            run_range_pairs(points, 0, warm, funcs_py)
            run_batch_pairs(points[:warm], funcs_c)
        else:
            run_range_arrays(lngs, lats, 0, warm, funcs_py)
            run_batch_arrays(lngs[:warm], lats[:warm], funcs_c)

    if args.input == "pairs":
        py_time = benchmark_scalar_pairs(points, funcs_py, args.threads)
        c_time = benchmark_batch_pairs(points, funcs_c, args.threads)
    else:
        py_time = benchmark_scalar_arrays(lngs, lats, funcs_py, args.threads)
        c_time = benchmark_batch_arrays(lngs, lats, funcs_c, args.threads)

    speedup = py_time / c_time if c_time > 0 else float("inf")

    print("Points:", len(points) if points is not None else len(lngs))
    print("Threads:", args.threads)
    print("Functions:", ", ".join(names))
    print("Python time (s):", round(py_time, 4))
    print("C time (s):", round(c_time, 4))
    print("Speedup:", round(speedup, 2), "x")

    if args.input == "pairs":
        mismatches, max_err = verify_pairs(
            points,
            funcs_py,
            funcs_c,
            args.tol,
            args.verify_samples,
            args.seed,
        )
    else:
        mismatches, max_err = verify_arrays(
            lngs,
            lats,
            funcs_py,
            funcs_c,
            args.tol,
            args.verify_samples,
            args.seed,
        )
    if args.verify_samples > 0:
        print("Verify samples:", min(args.verify_samples, len(points) if points is not None else len(lngs)))
        print("Mismatches:", mismatches)
        print("Max error:", max_err)


if __name__ == "__main__":
    main()
