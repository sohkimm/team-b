import pytest
import numpy as np
import xarray as xr

LAT_A = np.arange(24.0, 38.0, 0.05)
LON_A = np.arange(117.0, 131.0, 0.05)
LAT_B = np.arange(24.0, 38.0, 0.25)
LON_B = np.arange(117.0, 131.0, 0.25)

@pytest.fixture
def nc_high_res(tmp_path):
    """합성 고해상도(0.05°) WGS84 NC 파일."""
    rng = np.random.default_rng(42)
    data = rng.uniform(30.0, 35.0, (len(LAT_A), len(LON_A))).astype(np.float32)
    ds = xr.Dataset(
        {"sss": (["lat", "lon"], data,
                 {"_FillValue": -9999.0, "valid_min": 0.0, "valid_max": 45.0,
                  "units": "psu", "long_name": "Sea Surface Salinity"})},
        coords={"lat": LAT_A, "lon": LON_A},
        attrs={"processing_level": "L3", "cdm_data_type": "Grid",
               "Conventions": "CF-1.6"},
    )
    path = tmp_path / "high_res.nc"
    ds.to_netcdf(str(path))
    return str(path), ds

@pytest.fixture
def nc_low_res(tmp_path):
    """합성 저해상도(0.25°) WGS84 NC 파일."""
    rng = np.random.default_rng(7)
    data = rng.uniform(30.0, 35.0, (len(LAT_B), len(LON_B))).astype(np.float32)
    ds = xr.Dataset(
        {"sss_smap": (["lat", "lon"], data,
                      {"_FillValue": -9999.0, "valid_min": 0.0, "valid_max": 45.0,
                       "units": "psu", "long_name": "SMAP Sea Surface Salinity"})},
        coords={"lat": LAT_B, "lon": LON_B},
        attrs={"processing_level": "L3", "cdm_data_type": "Grid",
               "Conventions": "CF-1.6"},
    )
    path = tmp_path / "low_res.nc"
    ds.to_netcdf(str(path))
    return str(path), ds

@pytest.fixture
def nc_with_fillvalue(tmp_path):
    """일부 셀이 FillValue(-9999)인 NC."""
    rng = np.random.default_rng(1)
    data = rng.uniform(30.0, 35.0, (4, 5)).astype(np.float32)
    data[0, 0] = -9999.0
    data[1, 2] = -9999.0
    ds = xr.Dataset(
        {"sss": (["lat", "lon"], data, {"_FillValue": -9999.0,
                                         "valid_min": 0.0, "valid_max": 45.0})},
        coords={"lat": np.array([24.0, 25.0, 26.0, 27.0]),
                "lon": np.array([117.0, 118.0, 119.0, 120.0, 121.0])},
        attrs={"processing_level": "L3"},
    )
    path = tmp_path / "fill.nc"
    ds.to_netcdf(str(path))
    return str(path), ds
