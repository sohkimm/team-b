import numpy as np
import pytest
import xarray as xr
from src.qc import apply_qc


def test_fillvalue_replaced_with_nan(nc_with_fillvalue):
    _, ds = nc_with_fillvalue
    da = apply_qc(ds, "sss")
    assert np.isnan(da.values[0, 0])
    assert np.isnan(da.values[1, 2])


def test_valid_cells_preserved(nc_with_fillvalue):
    _, ds = nc_with_fillvalue
    da = apply_qc(ds, "sss")
    valid_count = int((~np.isnan(da.values)).sum())
    assert valid_count == 18  # 4*5=20, 2개 FillValue


def test_valid_range_applied():
    data = np.array([[1.0, 50.0], [-1.0, 35.0]], dtype=np.float32)
    ds = xr.Dataset(
        {"sss": (["lat", "lon"], data,
                 {"_FillValue": -9999.0, "valid_min": 0.0, "valid_max": 45.0})},
        coords={"lat": [24.0, 25.0], "lon": [117.0, 118.0]},
    )
    da = apply_qc(ds, "sss")
    assert np.isnan(da.values[0, 1])  # 50.0 > valid_max → NaN
    assert np.isnan(da.values[1, 0])  # -1.0 < valid_min → NaN
    assert da.values[0, 0] == pytest.approx(1.0)
    assert da.values[1, 1] == pytest.approx(35.0)


def test_missing_var_raises():
    ds = xr.Dataset({"sss": (["lat", "lon"], np.ones((2, 2)))},
                    coords={"lat": [24.0, 25.0], "lon": [117.0, 118.0]})
    with pytest.raises(KeyError, match="sss_none"):
        apply_qc(ds, "sss_none")
