import os
from dataclasses import dataclass

from src.io_nc import open_nc
from src.inspect_nc import describe
from src.reproject import to_wgs84
from src.resample import to_grid, _dx
from src.metrics import stats
from src.visualize import make_scatter, plot_map


@dataclass
class Config:
    aoi: tuple = (24.0, 38.0, 117.0, 131.0)   # lat0, lat1, lon0, lon1
    ref: str = "auto"                          # "auto"/"a"/"b" — Bias=eval−ref 방향
    var_a: str = None
    var_b: str = None
    time_index: int = 0
    grid: str = "fine"   # "fine"=고해상도 격자 비교(저해상도 업샘플) / "coarse"=저해상도 격자 비교(고해상도 다운샘플)
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

    # Step 1 이미지: AOI 클립 후 원본 해상도
    fig_dir = os.path.join(cfg.outdir, "figures")
    a_crop = _crop_aoi(da_a, cfg.aoi)
    b_crop = _crop_aoi(da_b, cfg.aoi)
    plot_map(a_crop, title=f"[Step1] {rep_a.var_name} ({rep_a.dlon}°)",
             save_path=os.path.join(fig_dir, f"step1_{rep_a.var_name}.png"))
    plot_map(b_crop, title=f"[Step1] {rep_b.var_name} ({rep_b.dlon}°)",
             save_path=os.path.join(fig_dir, f"step1_{rep_b.var_name}.png"))

    # ref/eval 역할 (Bias = eval − ref). auto: 저해상도(큰 dlon)=ref.
    if cfg.ref == "a":
        ref_is_a = True
    elif cfg.ref == "b":
        ref_is_a = False
    else:
        ref_is_a = rep_a.dlon >= rep_b.dlon
    if ref_is_a:
        ref_da, ref_rep, ref_name = da_a, rep_a, os.path.basename(path_a)
        eval_da, eval_rep, eval_name = da_b, rep_b, os.path.basename(path_b)
    else:
        ref_da, ref_rep, ref_name = da_b, rep_b, os.path.basename(path_b)
        eval_da, eval_rep, eval_name = da_a, rep_a, os.path.basename(path_a)

    # 비교 격자 선택. "fine"=더 촘촘한 자료 격자(거친 쪽 업샘플) / "coarse"=더 거친 자료 격자(촘촘한 쪽 다운샘플)
    if cfg.grid == "fine":
        target_da = ref_da if ref_rep.dlon < eval_rep.dlon else eval_da
        resamp = "linear"      # 거친 쪽을 bilinear 업샘플
    elif cfg.grid == "coarse":
        target_da = ref_da if ref_rep.dlon > eval_rep.dlon else eval_da
        resamp = "coarsen"     # 촘촘한 쪽을 블록평균 다운샘플
    else:
        raise ValueError(f"cfg.grid는 'fine'/'coarse'만: {cfg.grid}")
    target = _crop_aoi(target_da, cfg.aoi)

    # 목표인 자료는 그대로(native, 재보간 없음), 다른 하나만 목표 격자로 정합
    ref_on = target if ref_da is target_da else to_grid(ref_da, target, resamp)
    eval_on = target if eval_da is target_da else to_grid(eval_da, target, resamp)

    s = stats(eval_on, ref_on)
    grid_res = round(_dx(target, "x"), 6)
    title = f"grid={cfg.grid} ({grid_res} deg), resamp={resamp}"

    # Step 2 이미지: 격자 정합 후
    plot_map(ref_on,  title=f"[Step2-ref]  {ref_name}  → {grid_res}°",
             save_path=os.path.join(fig_dir, f"step2_ref_{cfg.grid}.png"))
    plot_map(eval_on, title=f"[Step2-eval] {eval_name} → {grid_res}°",
             save_path=os.path.join(fig_dir, f"step2_eval_{cfg.grid}.png"))

    fig = make_scatter(eval_on, ref_on, s, title=title)
    return {"stats": s, "figure": fig, "ref_name": ref_name,
            "eval_name": eval_name, "grid": cfg.grid, "grid_res": grid_res,
            "eval_on": eval_on, "ref_on": ref_on, "title": title}
