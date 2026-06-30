import numpy as np
import pytest
import xarray as xr
from src.inspect_nc import inspect, is_regular_grid


def test_is_regular_grid_true():
    lat = np.arange(24.0, 38.0, 0.25)
    lon = np.arange(117.0, 131.0, 0.25)
    assert is_regular_grid(lat, lon) is True


def test_is_regular_grid_false_2d():
    lat = np.array([[24.0, 24.0], [25.0, 25.0]])
    lon = np.array([[117.0, 118.0], [117.0, 118.0]])
    assert is_regular_grid(lat, lon) is False


def test_is_regular_grid_irregular():
    lat = np.array([24.0, 25.0, 27.0, 31.0])
    lon = np.arange(117.0, 131.0, 0.25)
    assert is_regular_grid(lat, lon) is False


def test_inspect_returns_dict(nc_low_res):
    _, ds = nc_low_res
    result = inspect(ds)
    assert isinstance(result, dict)
    for key in ["data_type", "grid_type", "is_regular", "dlat", "dlon", "crs"]:
        assert key in result, f"누락 키: {key}"


def test_inspect_l3_grid(nc_low_res):
    _, ds = nc_low_res
    result = inspect(ds)
    assert result["data_type"] == "위성 L3 격자"
    assert result["is_regular"] is True
    assert abs(result["dlat"] - 0.25) < 1e-4
    assert result["crs"] == "WGS84"
