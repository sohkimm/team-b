import numpy as np
import pytest
import xarray as xr
from src.metrics import compute_stats


def _make_pair(ref_vals, eval_vals, lat=None, lon=None):
    lat = lat or [24.0, 25.0]
    lon = lon or [117.0, 118.0]
    dims = ["lat", "lon"]
    r = xr.DataArray(np.array(ref_vals, dtype=float).reshape(len(lat), len(lon)),
                     dims=dims, coords={"lat": lat, "lon": lon})
    e = xr.DataArray(np.array(eval_vals, dtype=float).reshape(len(lat), len(lon)),
                     dims=dims, coords={"lat": lat, "lon": lon})
    return r, e


def test_perfect_correlation():
    ref, ev = _make_pair([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0])
    s = compute_stats(ref, ev)
    assert s["N"] == 4
    assert abs(s["Bias"]) < 1e-9
    assert abs(s["RMSE"]) < 1e-9
    assert abs(s["R"] - 1.0) < 1e-6
    assert abs(s["R2"] - 1.0) < 1e-6


def test_bias_direction():
    ref, ev = _make_pair([1.0, 2.0, 3.0, 4.0], [2.0, 3.0, 4.0, 5.0])
    s = compute_stats(ref, ev)
    assert abs(s["Bias"] - 1.0) < 1e-9  # eval - ref = +1


def test_nan_cells_excluded():
    ref, ev = _make_pair([1.0, float("nan"), 3.0, 4.0],
                          [1.0, 2.0,          3.0, 4.0])
    s = compute_stats(ref, ev)
    assert s["N"] == 3


def test_all_nan_returns_nan():
    ref, ev = _make_pair([float("nan")] * 4, [float("nan")] * 4)
    s = compute_stats(ref, ev)
    assert s["N"] == 0
    assert np.isnan(s["Bias"])


def test_rmse_value():
    ref, ev = _make_pair([0.0, 0.0, 0.0, 0.0], [1.0, 1.0, 1.0, 1.0])
    s = compute_stats(ref, ev)
    assert abs(s["RMSE"] - 1.0) < 1e-9
    assert abs(s["MAE"] - 1.0) < 1e-9
