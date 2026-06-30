import numpy as np
import pytest
import xarray as xr
from src.inspect_nc import is_regular_grid, detect_salinity_var, describe


def test_is_regular_grid_true():
    lat = np.arange(0, 5, 0.5)
    lon = np.arange(100, 110, 0.5)
    assert is_regular_grid(lat, lon) is True


def test_is_regular_grid_false_2d():
    lat = np.zeros((3, 3))
    lon = np.zeros((3, 3))
    assert is_regular_grid(lat, lon) is False


def test_detect_salinity_picks_sss_not_density():
    ds = xr.Dataset({
        "sss": ("x", np.arange(3.0), {"standard_name": "sea_surface_salinity"}),
        "ssd": ("x", np.arange(3.0), {"standard_name": "sea_surface_density"}),
    })
    assert detect_salinity_var(ds) == "sss"


def test_detect_salinity_override():
    ds = xr.Dataset({"foo": ("x", np.arange(3.0))})
    assert detect_salinity_var(ds, override="foo") == "foo"


def test_describe_geographic(make_sss_ds):
    rep = describe(make_sss_ds)
    assert rep.grid_kind == "GEOGRAPHIC"
    assert np.isclose(rep.dlat, 0.25)
    assert rep.var_name == "sea_surface_salinity"
    assert rep.time_len == 1
