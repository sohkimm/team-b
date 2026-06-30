import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 24.0, 38.0
LON_MIN, LON_MAX = 117.0, 131.0


def to_wgs84_region(da: xr.DataArray, info: dict) -> xr.DataArray:
    """
    Convert DataArray to WGS84 and resample to analysis region.

    Parameters:
    -----------
    da : xr.DataArray
        Input DataArray with dims ["lat", "lon"]
    info : dict
        Metadata dict from inspect() with keys:
        - is_regular: bool
        - dlat, dlon: float (resolution)
        - crs, proj_name: str
        - lat, lon: np.ndarray (coordinate arrays)

    Returns:
    --------
    xr.DataArray
        Resampled to analysis region (lat 24~38N, lon 117~131E) in WGS84

    Raises:
    -------
    NotImplementedError
        If grid is not regular (curved, swath, model grid)
    RuntimeError
        If reprojection fails
    """
    if not info["is_regular"]:
        raise NotImplementedError(
            "비정규격자(곡선격자·스와스·모델)는 해커톤 범위 외입니다."
        )

    if info["proj_name"] not in ("latitude_longitude", "WGS84"):
        try:
            import rioxarray  # noqa: F401
            da = (da.rio.set_spatial_dims(x_dim="lon", y_dim="lat")
                     .rio.write_crs(f"EPSG:{_proj_to_epsg(info['proj_name'])}")
                     .rio.reproject("EPSG:4326"))
            # 재투영 후 dim 이름 통일
            if "x" in da.dims:
                da = da.rename({"x": "lon", "y": "lat"})
        except Exception as e:
            raise RuntimeError(f"재투영 실패: {e}") from e

    # 경도 -180~180 정규화
    lon = da.lon.values.copy()
    if lon.max() > 180.0:
        lon = np.where(lon > 180.0, lon - 360.0, lon)
        idx = np.argsort(lon)
        da = da.assign_coords(lon=lon).isel(lon=idx)

    # lat 오름차순 정렬
    if da.lat.values[0] > da.lat.values[-1]:
        da = da.isel(lat=slice(None, None, -1))

    # 분석 영역 목표 격자로 interp
    res = info["dlat"]
    target_lat = np.arange(LAT_MIN, LAT_MAX + res * 0.5, res)
    target_lon = np.arange(LON_MIN, LON_MAX + res * 0.5, res)

    # 목표 격자가 원본 범위 안에 있는지 클립
    target_lat = target_lat[(target_lat >= da.lat.min()) &
                             (target_lat <= da.lat.max())]
    target_lon = target_lon[(target_lon >= da.lon.min()) &
                             (target_lon <= da.lon.max())]

    result = da.interp(lat=target_lat, lon=target_lon, method="linear")
    return result


def _proj_to_epsg(proj_name: str) -> int:
    """Map projection name to EPSG code."""
    mapping = {
        "polar_stereographic": 3413,
        "lambert_conformal_conic": 4326,
    }
    return mapping.get(proj_name, 4326)
