import os
from dataclasses import dataclass, field

from src.io_nc import open_nc
from src.inspect_nc import describe
from src.reproject import to_wgs84
from src.resample import to_ref_grid
from src.metrics import stats
from src.visualize import make_scatter


@dataclass
class Config:
    aoi: tuple = (24.0, 38.0, 117.0, 131.0)   # lat0, lat1, lon0, lon1
    ref: str = "auto"                          # "auto"/"a"/"b"
    var_a: str = None
    var_b: str = None
    time_index: int = 0
    method: str = "coarsen"
    outdir: str = "results"


def _prep(path, var_override, time_index):
    ds = open_nc(path)
    rep = describe(ds, var_override=var_override)
    da = ds[rep.var_name]
    if "time" in da.dims:
        da = da.isel(time=time_index)
    # CMEMS sos는 (time, depth, lat, lon) — depth 등 잔여 싱글톤 차원 제거 → 2D(lat,lon)
    da = da.squeeze(drop=True)
    return to_wgs84(da, rep), rep


def _crop_aoi(da, aoi):
    lat0, lat1, lon0, lon1 = aoi
    return da.sel(y=slice(lat0, lat1), x=slice(lon0, lon1))


def run(path_a, path_b, cfg):
    da_a, rep_a = _prep(path_a, cfg.var_a, cfg.time_index)
    da_b, rep_b = _prep(path_b, cfg.var_b, cfg.time_index)

    if cfg.ref == "a":
        ref_is_a = True
    elif cfg.ref == "b":
        ref_is_a = False
    else:  # auto: coarser(큰 dlon)가 ref. 동률(<5%)이면 a를 ref.
        ref_is_a = rep_a.dlon >= rep_b.dlon * 0.95 and rep_a.dlon >= rep_b.dlon

    if ref_is_a:
        ref_da, eval_da = da_a, da_b
        ref_name = os.path.basename(path_a); eval_name = os.path.basename(path_b)
    else:
        ref_da, eval_da = da_b, da_a
        ref_name = os.path.basename(path_b); eval_name = os.path.basename(path_a)

    ref_aoi = _crop_aoi(ref_da, cfg.aoi)
    eval_on_ref = to_ref_grid(eval_da, ref_aoi, method=cfg.method)
    s = stats(eval_on_ref, ref_aoi)
    fig = make_scatter(eval_on_ref, ref_aoi, s)
    return {"stats": s, "figure": fig, "ref_name": ref_name, "eval_name": eval_name}
