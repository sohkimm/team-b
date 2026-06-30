import numpy as np
import xarray as xr
from src.web_serialize import safe_num, field_to_json, scatter_to_json


def _da(vals, lat, lon):
    return xr.DataArray(np.asarray(vals, dtype=float),
                        coords={"lat": np.asarray(lat, float), "lon": np.asarray(lon, float)},
                        dims=("lat", "lon"))


def test_safe_num():
    assert safe_num(1.5) == 1.5
    assert safe_num(float("nan")) is None
    assert safe_num(float("inf")) is None
    assert safe_num(None) is None


def test_field_to_json_latlon():
    da = _da([[35.0, float("nan")], [34.0, 33.0], [32.0, 31.0]],
             [24.0, 24.25, 24.5], [117.0, 117.25])
    out = field_to_json(da)
    assert out["ny"] == 3 and out["nx"] == 2
    assert out["lat0"] == 24.0 and out["lat1"] == 24.5
    assert out["lon0"] == 117.0 and out["lon1"] == 117.25
    assert out["z"][0][1] is None and out["z"][0][0] == 35.0
    assert out["vmin"] == 31.0 and out["vmax"] == 35.0


def test_scatter_to_json():
    lat = list(np.arange(24, 30, 0.25)); lon = list(np.arange(117, 123, 0.25))
    ny, nx = len(lat), len(lon)
    ref = _da(np.full((ny, nx), 33.0), lat, lon)
    ev = _da(np.full((ny, nx), 34.0), lat, lon)
    out = scatter_to_json(ref, ev, max_points=10)
    assert out["stats"]["N"] == ny * nx
    assert abs(out["stats"]["Bias"] - 1.0) < 1e-9
    assert len(out["points"]) <= 10
    assert out["points"][0] == [33.0, 34.0]
