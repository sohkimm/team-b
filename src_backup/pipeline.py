import datetime
import os

import numpy as np
import pandas as pd
import xarray as xr

from src.io_nc import open_nc
<<<<<<< HEAD
from src.inspect_nc import describe
from src.reproject import to_wgs84
from src.resample import to_grid, _dx
from src.metrics import stats
from src.visualize import make_scatter, plot_map
=======
from src.inspect_nc import inspect
from src.qc import apply_qc
from src.reproject import to_wgs84_region
from src.resample import match_resolution
from src.metrics import compute_stats
from src.visualize import save_map, save_scatter, save_compare_table
>>>>>>> 06158a89bbdf60908735d65e5ca34f0996554218


def run(cfg: dict) -> dict:
    outdir = cfg["outdir"]
    fig_dir = os.path.join(outdir, "figures")
    tbl_dir = os.path.join(outdir, "tables")
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(tbl_dir, exist_ok=True)

    # [1] 입력 검증
    ds_a = open_nc(cfg["file_a"])
    ds_b = open_nc(cfg["file_b"])
    print("[1] 입력 검증 완료")

    # [2] NC 파악 + QC
    info_a = inspect(ds_a)
    info_b = inspect(ds_b)
    print(f"[2] NC 파악: A={info_a['data_type']}/{info_a['dlat']:.3f}°,"
          f" B={info_b['data_type']}/{info_b['dlat']:.3f}°")

    da_a = apply_qc(ds_a, cfg["var_a"])
    da_b = apply_qc(ds_b, cfg["var_b"])
    valid_a = int((~np.isnan(da_a.values)).sum())
    valid_b = int((~np.isnan(da_b.values)).sum())
    print(f"[2] QC 완료: A 유효셀 {valid_a} / B 유효셀 {valid_b}")

    # [3] WGS84 + 분석 영역
    da_a = to_wgs84_region(da_a, info_a)
    da_b = to_wgs84_region(da_b, info_b)
    save_map(da_a, os.path.join(fig_dir, "step3_wgs84_A.png"),
             f"파일 A — WGS84 분석영역 ({cfg['var_a']})")
    save_map(da_b, os.path.join(fig_dir, "step3_wgs84_B.png"),
             f"파일 B — WGS84 분석영역 ({cfg['var_b']})")
    print("[3] WGS84+분석영역 리샘플 완료 → step3_wgs84_A.png, step3_wgs84_B.png 저장")

    # [4] 해상도 정합
    da_coarse, da_fine_resampled, coarse_label = match_resolution(da_a, da_b)
    fine_label = "B" if coarse_label == "A" else "A"
    coarse_res = info_a["dlat"] if coarse_label == "A" else info_b["dlat"]
    save_map(da_coarse,
             os.path.join(fig_dir, "step4_resampled_A.png"),
             f"파일 {coarse_label} — 저해상도 기준 ({coarse_res:.3f}°)")
    save_map(da_fine_resampled,
             os.path.join(fig_dir, "step4_resampled_B.png"),
             f"파일 {fine_label} — 리샘플 후 ({coarse_res:.3f}°)")
    print(f"[4] 해상도 정합 완료(기준: {coarse_label} {coarse_res:.3f}°)"
          f" → step4_resampled_A.png, step4_resampled_B.png 저장")

    # [5] 검증
    # 고→저 (권장): coarse=기준, fine_resampled=평가
    stats_hilo = compute_stats(ref=da_coarse, eval_da=da_fine_resampled)

    # 저→고 (비교): bilinear로 coarse → fine 격자 보간
    da_fine_orig = da_b if coarse_label == "A" else da_a
    da_coarse_up = da_coarse.interp_like(da_fine_orig, method="linear")
    stats_lohi = compute_stats(ref=da_fine_orig, eval_da=da_coarse_up)

    save_scatter(da_coarse, da_fine_resampled, stats_hilo,
                 os.path.join(fig_dir, "step5_hilo.png"), "검증 고→저 (권장)")
    save_scatter(da_fine_orig, da_coarse_up, stats_lohi,
                 os.path.join(fig_dir, "step5_lohi.png"), "검증 저→고 (비교)")
    save_compare_table(stats_hilo, stats_lohi,
                       os.path.join(fig_dir, "step5_compare.png"))

    # CSV 저장
    csv_path = os.path.join(tbl_dir, "stats.csv")
    df = pd.DataFrame([
        {"방향": "고→저(권장)", **stats_hilo},
        {"방향": "저→고(비교)", **stats_lohi},
    ])
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # report.md 생성
    report_path = os.path.join(outdir, "report.md")
    _write_report(report_path, cfg, info_a, info_b,
                  coarse_label, coarse_res, stats_hilo, stats_lohi)
    print(f"[5] 검증 완료 → {report_path} 생성")

    return {"report": report_path, "csv": csv_path, "figures": fig_dir}


def _write_report(path, cfg, info_a, info_b,
                  coarse_label, coarse_res, stats_hilo, stats_lohi):
    now = datetime.datetime.now().isoformat(timespec="seconds")

    def fmt(v, k):
        if k == "N":
            return str(int(v)) if not (isinstance(v, float) and np.isnan(v)) else "NaN"
        return f"{v:.4f}" if isinstance(v, float) and not np.isnan(v) else "NaN"

    keys = ["N", "Bias", "RMSE", "MAE", "R", "R2"]
    hilo_row = " | ".join(fmt(stats_hilo[k], k) for k in keys)
    lohi_row = " | ".join(fmt(stats_lohi[k], k) for k in keys)

    content = f"""# NC 검증 결과 보고서

생성: {now}

<<<<<<< HEAD
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
=======
## 입력 파일 정보
>>>>>>> 06158a89bbdf60908735d65e5ca34f0996554218

| | 파일 A | 파일 B |
|---|---|---|
| 경로 | `{cfg['file_a']}` | `{cfg['file_b']}` |
| 변수 | `{cfg['var_a']}` | `{cfg['var_b']}` |
| 자료유형 | {info_a['data_type']} | {info_b['data_type']} |
| 격자유형 | {info_a['grid_type']} | {info_b['grid_type']} |
| 공간해상도 | {info_a['dlat']:.3f}° × {info_a['dlon']:.3f}° | {info_b['dlat']:.3f}° × {info_b['dlon']:.3f}° |
| 투영 | {info_a['crs']} | {info_b['crs']} |

## 파이프라인 설정

<<<<<<< HEAD
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
=======
- 분석 영역: lat 24~38°N, lon 117~131°E
- 기준 해상도: 파일 {coarse_label} ({coarse_res:.3f}°, 저해상도)

## 검증 통계

| 방향 | N | Bias | RMSE | MAE | R | R² |
|---|---|---|---|---|---|---|
| 고→저 (권장) | {hilo_row} |
| 저→고 (비교) | {lohi_row} |

> Bias = Eval − Ref (양수: 평가 자료가 더 높음)

## 시각화

### [3] WGS84 표준화
![A WGS84](figures/step3_wgs84_A.png)
![B WGS84](figures/step3_wgs84_B.png)

### [4] 해상도 정합 후
![A 정합](figures/step4_resampled_A.png)
![B 정합](figures/step4_resampled_B.png)

### [5] 검증 결과
![고→저 산점도](figures/step5_hilo.png)
![저→고 산점도](figures/step5_lohi.png)
![통계 비교](figures/step5_compare.png)
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
>>>>>>> 06158a89bbdf60908735d65e5ca34f0996554218
