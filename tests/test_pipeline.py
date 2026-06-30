import numpy as np
import xarray as xr
from src.pipeline import Config, run


def _write(path, lat, lon, val):
    data = np.full((1, lat.size, lon.size), val, dtype="float64")
    ds = xr.Dataset(
        {"sea_surface_salinity": (("time", "latitude", "longitude"), data,
            {"standard_name": "sea_surface_salinity", "units": "1e-3"})},
        coords={"time": [np.datetime64("2026-01-01")],
                "latitude": lat, "longitude": lon})
    ds.to_netcdf(path)


def test_run_end_to_end(tmp_path):
    # A: 0.125° (고해상도/eval), B: 0.25° (저해상도/ref)
    a = tmp_path / "a.nc"; b = tmp_path / "b.nc"
    _write(a, np.arange(24.0, 38.0, 0.125), np.arange(117.0, 131.0, 0.125), 35.0)
    _write(b, np.arange(24.125, 38.0, 0.25), np.arange(117.125, 131.0, 0.25), 35.0)
    res = run(str(a), str(b), Config())
    assert res["ref_name"] == "b.nc"      # 저해상도가 ref
    assert res["stats"]["N"] > 0
    assert np.isclose(res["stats"]["Bias"], 0.0, atol=1e-6)  # 동일값 → bias 0
    assert res["figure"] is not None


def test_grid_fine_vs_coarse(tmp_path):
    # 두 방식을 별도로 산출: fine(SMAP 업샘플, 0.125°) vs coarse(CMEMS 다운샘플, 0.25°)
    a = tmp_path / "a.nc"; b = tmp_path / "b.nc"
    _write(a, np.arange(24.0, 38.0, 0.125), np.arange(117.0, 131.0, 0.125), 35.0)
    _write(b, np.arange(24.125, 38.0, 0.25), np.arange(117.125, 131.0, 0.25), 35.0)
    fine = run(str(a), str(b), Config(grid="fine"))
    coarse = run(str(a), str(b), Config(grid="coarse"))
    assert fine["grid_res"] == 0.125 and coarse["grid_res"] == 0.25
    assert fine["grid_res"] < coarse["grid_res"]
    assert fine["stats"]["N"] > coarse["stats"]["N"]   # 고해상도 격자가 셀 더 많음
    # ref 역할(저해상도 b)·Bias 방향은 두 방식에서 일관
    assert fine["ref_name"] == "b.nc" and coarse["ref_name"] == "b.nc"
    assert np.isclose(fine["stats"]["Bias"], 0.0, atol=1e-6)
    assert np.isclose(coarse["stats"]["Bias"], 0.0, atol=1e-6)
