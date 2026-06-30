from dataclasses import dataclass
import numpy as np

_LAT_NAMES = ("latitude", "lat", "nav_lat", "y")
_LON_NAMES = ("longitude", "lon", "nav_lon", "x")


@dataclass
class InspectReport:
    grid_kind: str
    dlat: float
    dlon: float
    lat_name: str
    lon_name: str
    var_name: str
    units: str
    time_len: int


def is_regular_grid(lat, lon, rtol=1e-4):
    lat = np.asarray(lat)
    lon = np.asarray(lon)
    if lat.ndim != 1 or lon.ndim != 1:
        return False
    dlat, dlon = np.diff(lat), np.diff(lon)
    if dlat.size == 0 or dlon.size == 0:
        return False
    return bool(np.allclose(dlat, dlat[0], rtol=rtol)
                and np.allclose(dlon, dlon[0], rtol=rtol))


def detect_salinity_var(ds, override=None):
    if override is not None:
        return override
    for name, var in ds.data_vars.items():
        if var.attrs.get("standard_name") == "sea_surface_salinity":
            return name
    raise ValueError(
        f"sea_surface_salinity 변수 자동탐지 실패. 후보: {list(ds.data_vars)} "
        f"— --var-a/--var-b 로 지정하세요.")


def _find_coord(ds, names):
    for n in names:
        if n in ds.coords or n in ds.variables:
            return n
    raise ValueError(f"좌표 미발견: {names} 중 없음 (있는 좌표: {list(ds.coords)})")


def describe(ds, var_override=None):
    lat_name = _find_coord(ds, _LAT_NAMES)
    lon_name = _find_coord(ds, _LON_NAMES)
    lat = np.asarray(ds[lat_name].values)
    lon = np.asarray(ds[lon_name].values)
    regular = is_regular_grid(lat, lon)
    grid_kind = "GEOGRAPHIC" if regular else "IRREGULAR"
    dlat = float(abs(lat[1] - lat[0])) if lat.ndim == 1 and lat.size > 1 else float("nan")
    dlon = float(abs(lon[1] - lon[0])) if lon.ndim == 1 and lon.size > 1 else float("nan")
    var_name = detect_salinity_var(ds, override=var_override)
    units = ds[var_name].attrs.get("units", "")
    time_len = int(ds.sizes.get("time", 1))
    return InspectReport(grid_kind, dlat, dlon, lat_name, lon_name,
                         var_name, units, time_len)
