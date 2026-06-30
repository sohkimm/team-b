import os
import numpy as np
import xarray as xr
import pytest
from src.visualize import save_map, save_scatter, save_compare_table


def _small_da():
    lat = np.arange(24.0, 38.0, 0.25)
    lon = np.arange(117.0, 131.0, 0.25)
    rng = np.random.default_rng(0)
    data = rng.uniform(30.0, 35.0, (len(lat), len(lon))).astype(np.float32)
    return xr.DataArray(data, dims=["lat", "lon"],
                        coords={"lat": lat, "lon": lon})


def test_save_map_creates_file(tmp_path):
    da = _small_da()
    path = str(tmp_path / "test_map.png")
    save_map(da, path, "테스트 지도")
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0


def test_save_scatter_creates_file(tmp_path):
    da = _small_da()
    stats = {"N": 100, "Bias": 0.1, "RMSE": 0.5, "MAE": 0.3, "R": 0.9, "R2": 0.81}
    path = str(tmp_path / "scatter.png")
    save_scatter(da, da, stats, path, "산점도")
    assert os.path.exists(path)


def test_save_compare_table_creates_file(tmp_path):
    stats_hilo = {"N": 100, "Bias": 0.1, "RMSE": 0.5, "MAE": 0.3, "R": 0.9, "R2": 0.81}
    stats_lohi = {"N": 200, "Bias": 0.3, "RMSE": 0.8, "MAE": 0.5, "R": 0.7, "R2": 0.49}
    path = str(tmp_path / "compare.png")
    save_compare_table(stats_hilo, stats_lohi, path)
    assert os.path.exists(path)
