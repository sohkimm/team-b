import numpy as np
import xarray as xr
from rasterio.enums import Resampling
import rioxarray  # noqa: F401 — registers .rio accessor


def match_resolution(
    da_a: xr.DataArray, da_b: xr.DataArray
) -> tuple[xr.DataArray, xr.DataArray, str]:
    """
    Resample the higher-resolution DataArray to match the coarser one.

    Args:
        da_a: First DataArray (dims=["lat", "lon"], WGS84)
        da_b: Second DataArray (dims=["lat", "lon"], WGS84)

    Returns:
        Tuple of (coarse, fine_resampled_to_coarse, coarse_label)
        where coarse_label indicates which input was coarser ("A" or "B")
    """
    res_a = float(abs(np.diff(da_a.lat.values).mean()))
    res_b = float(abs(np.diff(da_b.lat.values).mean()))

    if res_a >= res_b:
        coarse, fine, label = da_a, da_b, "A"
    else:
        coarse, fine, label = da_b, da_a, "B"

    coarse_rio = (coarse.rio
                        .set_spatial_dims(x_dim="lon", y_dim="lat")
                        .rio.write_crs("EPSG:4326"))
    fine_rio = (fine.rio
                    .set_spatial_dims(x_dim="lon", y_dim="lat")
                    .rio.write_crs("EPSG:4326"))

    fine_resampled = fine_rio.rio.reproject_match(
        coarse_rio, resampling=Resampling.average
    )

    # rioxarray가 dim을 x/y로 바꾸면 복원
    if "x" in fine_resampled.dims:
        fine_resampled = fine_resampled.rename({"x": "lon", "y": "lat"})

    # coarse의 정확한 lat/lon 좌표로 강제 정렬 (부동소수점 오차 제거)
    fine_resampled = fine_resampled.assign_coords(
        lat=coarse.lat.values[:fine_resampled.sizes["lat"]],
        lon=coarse.lon.values[:fine_resampled.sizes["lon"]],
    )

    return coarse, fine_resampled, label
