import numpy as np
import pytest
import xarray as xr
from src.resample import match_resolution


def _make_region_da(res: float, seed: int = 0) -> xr.DataArray:
    lat = np.arange(24.0, 38.0, res)
    lon = np.arange(117.0, 131.0, res)
    rng = np.random.default_rng(seed)
    data = rng.uniform(30.0, 35.0, (len(lat), len(lon))).astype(np.float32)
    return xr.DataArray(data, dims=["lat", "lon"],
                        coords={"lat": lat, "lon": lon})


def test_coarse_label_b_when_b_is_coarser():
    da_a = _make_region_da(0.05)
    da_b = _make_region_da(0.25, seed=1)
    coarse, fine_resampled, label = match_resolution(da_a, da_b)
    assert label == "B"


def test_coarse_label_a_when_a_is_coarser():
    da_a = _make_region_da(0.25)
    da_b = _make_region_da(0.05, seed=1)
    coarse, fine_resampled, label = match_resolution(da_a, da_b)
    assert label == "A"


def test_output_grid_matches_coarse():
    da_a = _make_region_da(0.05)
    da_b = _make_region_da(0.25, seed=1)
    coarse, fine_resampled, label = match_resolution(da_a, da_b)
    assert fine_resampled.lat.shape == coarse.lat.shape
    assert fine_resampled.lon.shape == coarse.lon.shape


def test_output_has_lat_lon_dims():
    da_a = _make_region_da(0.05)
    da_b = _make_region_da(0.25, seed=1)
    coarse, fine_resampled, label = match_resolution(da_a, da_b)
    assert "lat" in fine_resampled.dims
    assert "lon" in fine_resampled.dims
