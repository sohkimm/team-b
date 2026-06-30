import numpy as np
import xarray as xr


def is_regular_grid(lat: np.ndarray, lon: np.ndarray, rtol: float = 1e-4) -> bool:
    if lat.ndim != 1 or lon.ndim != 1:
        return False
    if len(lat) < 2 or len(lon) < 2:
        return True
    dlat = np.diff(lat)
    dlon = np.diff(lon)
    return (np.allclose(dlat, dlat[0], rtol=rtol) and
            np.allclose(dlon, dlon[0], rtol=rtol))


def _find_coord(ds: xr.Dataset, names: list) -> np.ndarray:
    for name in names:
        if name in ds.coords:
            return ds.coords[name].values
    raise KeyError(f"좌표 변수를 찾을 수 없음. 시도한 이름: {names}")


def _detect_crs(ds: xr.Dataset) -> tuple:
    for var in ds.data_vars:
        gm_name = ds[var].attrs.get("grid_mapping")
        if gm_name and gm_name in ds:
            proj = ds[gm_name].attrs.get("grid_mapping_name", "latitude_longitude")
            if proj == "latitude_longitude":
                return "WGS84", proj
            return proj, proj
    for attr in ("crs_wkt", "proj4", "spatial_ref"):
        if attr in ds.attrs:
            return ds.attrs[attr], ds.attrs[attr]
    return "WGS84", "latitude_longitude"


def inspect(ds: xr.Dataset) -> dict:
    lat = _find_coord(ds, ["lat", "latitude", "y"])
    lon = _find_coord(ds, ["lon", "longitude", "x"])

    proc = ds.attrs.get("processing_level", "")
    cdm = ds.attrs.get("cdm_data_type", "")
    if "L2" in proc or cdm == "Swath":
        data_type = "위성 L2 스와스"
    elif "L3" in proc or cdm == "Grid":
        data_type = "위성 L3 격자"
    elif "L4" in proc:
        data_type = "위성 L4 합성장"
    elif "model" in ds.attrs.get("source", "").lower():
        data_type = "모델"
    else:
        data_type = "미분류"

    regular = is_regular_grid(lat, lon)
    grid_type = "정규격자" if regular else "비정규격자"

    dlat = float(abs(np.diff(lat).mean())) if len(lat) > 1 else None
    dlon = float(abs(np.diff(lon).mean())) if len(lon) > 1 else None

    crs, proj_name = _detect_crs(ds)
    time_res = ds.attrs.get("time_coverage_duration",
               ds.attrs.get("temporal_resolution", "미확인"))

    return {
        "data_type": data_type,
        "grid_type": grid_type,
        "is_regular": regular,
        "dlat": dlat,
        "dlon": dlon,
        "lat": lat,
        "lon": lon,
        "crs": crs,
        "proj_name": proj_name,
        "time_res": time_res,
    }
