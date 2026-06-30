import numpy as np
import xarray as xr


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
