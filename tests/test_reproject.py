import numpy as np
import pytest
import xarray as xr
from src.reproject import to_wgs84_region


def _make_info(dlat, dlon, crs="WGS84", proj_name="latitude_longitude", is_regular=True):
    lat = np.arange(20.0, 42.0, dlat)
    lon = np.arange(110.0, 140.0, dlon)
    return {"dlat": dlat, "dlon": dlon, "crs": crs,
            "proj_name": proj_name, "is_regular": is_regular,
            "lat": lat, "lon": lon}


def _make_da(dlat=0.25, dlon=0.25):
    lat = np.arange(20.0, 42.0, dlat)
    lon = np.arange(110.0, 140.0, dlon)
    rng = np.random.default_rng(0)
    data = rng.uniform(30.0, 35.0, (len(lat), len(lon))).astype(np.float32)
    return xr.DataArray(data, dims=["lat", "lon"],
                        coords={"lat": lat, "lon": lon})


def test_output_dims_are_lat_lon():
    da = _make_da()
    info = _make_info(0.25, 0.25)
    result = to_wgs84_region(da, info)
    assert "lat" in result.dims and "lon" in result.dims


def test_output_within_analysis_region():
    da = _make_da()
    info = _make_info(0.25, 0.25)
    result = to_wgs84_region(da, info)
    assert float(result.lat.min()) >= 24.0 - 0.25
    assert float(result.lat.max()) <= 38.0 + 0.25
    assert float(result.lon.min()) >= 117.0 - 0.25
    assert float(result.lon.max()) <= 131.0 + 0.25


def test_irregular_grid_raises():
    lat = np.arange(20.0, 42.0, 0.25)
    lon = np.arange(110.0, 140.0, 0.25)
    rng = np.random.default_rng(0)
    data = rng.uniform(30.0, 35.0, (len(lat), len(lon))).astype(np.float32)
    da = xr.DataArray(data, dims=["lat", "lon"],
                      coords={"lat": lat, "lon": lon})
    info = _make_info(0.25, 0.25, is_regular=False)
    with pytest.raises(NotImplementedError, match="비정규격자"):
        to_wgs84_region(da, info)


def test_lon_normalization():
    lat = np.arange(20.0, 42.0, 0.25)
    lon_0_360 = np.arange(200.0, 240.0, 0.25)  # 200~240° → -160~-120°
    rng = np.random.default_rng(0)
    data = rng.uniform(30.0, 35.0, (len(lat), len(lon_0_360))).astype(np.float32)
    da = xr.DataArray(data, dims=["lat", "lon"],
                      coords={"lat": lat, "lon": lon_0_360})
    info = _make_info(0.25, 0.25)
    info["lon"] = lon_0_360
    result = to_wgs84_region(da, info)
    assert float(result.lon.max()) <= 180.0
