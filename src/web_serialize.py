"""웹용 JSON 직렬화 — 2D 염분 격자(lee: dims=lat/lon) / 산점 점배열 → JSON-safe.

lee의 compute_stats(ref, eval)를 그대로 써서 산점 통계를 낸다.
"""
import math

import numpy as np

from src.metrics import compute_stats


def safe_num(x):
    """NaN/Inf → None (JSON엔 NaN이 없다)."""
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return x
    return None if (math.isnan(f) or math.isinf(f)) else f


def field_to_json(da):
    """dims=(lat,lon) 1D 오름차순 좌표 2D DataArray → {z, extent, vmin, vmax}.

    z[i][j]는 (lat[i], lon[j]) 값. NaN은 None.
    """
    lat = np.asarray(da["lat"].values, dtype="float64")
    lon = np.asarray(da["lon"].values, dtype="float64")
    vals = np.asarray(da.values, dtype="float64")
    z = [[safe_num(v) for v in row] for row in vals]
    finite = vals[np.isfinite(vals)]
    vmin = safe_num(float(finite.min())) if finite.size else None
    vmax = safe_num(float(finite.max())) if finite.size else None
    return {
        "z": z,
        "lat0": float(lat.min()), "lat1": float(lat.max()),
        "lon0": float(lon.min()), "lon1": float(lon.max()),
        "ny": int(lat.size), "nx": int(lon.size),
        "vmin": vmin, "vmax": vmax,
    }


def scatter_to_json(ref_da, eval_da, max_points=1400, seed=1337):
    """(ref, eval) 점배열 + lee compute_stats. 통계는 전체, 점은 ≤max_points 서브샘플."""
    r = np.asarray(ref_da.values, dtype="float64").ravel()
    e = np.asarray(eval_da.values, dtype="float64").ravel()
    mask = np.isfinite(r) & np.isfinite(e)
    r, e = r[mask], e[mask]
    s = compute_stats(ref_da, eval_da)
    n = int(r.size)
    if n > max_points:
        rng = np.random.default_rng(seed)
        idx = rng.choice(n, size=max_points, replace=False)
        idx.sort()
        rp, ep = r[idx], e[idx]
    else:
        rp, ep = r, e
    points = [[float(rv), float(ev)] for rv, ev in zip(rp, ep)]
    return {
        "points": points,
        "stats": {"N": int(s["N"]), "Bias": safe_num(s["Bias"]),
                  "RMSE": safe_num(s["RMSE"]), "R": safe_num(s["R"])},
    }
