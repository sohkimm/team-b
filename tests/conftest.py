import numpy as np
import pytest
import xarray as xr


@pytest.fixture
def make_sss_ds():
    lat = np.arange(24.0, 38.0, 0.25)
    lon = np.arange(117.0, 131.0, 0.25)
    data = np.ones((1, lat.size, lon.size))
    return xr.Dataset(
        {"sea_surface_salinity": (("time", "latitude", "longitude"), data,
                                  {"standard_name": "sea_surface_salinity", "units": "1e-3"})},
        coords={"time": [np.datetime64("2026-01-01")], "latitude": lat, "longitude": lon},
    )


def make_grid_da(values, lat, lon, name="sea_surface_salinity", attrs=None):
    """위/경도 1D 좌표를 가진 합성 DataArray. values shape = (len(lat), len(lon))."""
    da = xr.DataArray(
        np.asarray(values, dtype="float64"),
        coords={"latitude": np.asarray(lat, dtype="float64"),
                "longitude": np.asarray(lon, dtype="float64")},
        dims=("latitude", "longitude"),
        name=name,
        attrs=attrs or {"standard_name": "sea_surface_salinity", "units": "1e-3"},
    )
    return da
