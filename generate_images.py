"""이미지 8장 생성 스크립트 — 기존 코드 건드리지 않음.

사용법:
    python generate_images.py <CMEMS.nc> <SMAP.nc>
"""
import sys
import os
import numpy as np

from src.io_nc import open_nc
from src.inspect_nc import inspect
from src.web_adapt import detect_var, prep as web_prep
from src.reproject import to_wgs84_region
from src.resample import match_resolution
from src.metrics import compute_stats
from src.visualize import save_map, save_scatter

OUT = os.path.join("results", "figures")
os.makedirs(OUT, exist_ok=True)

path_a, path_b = sys.argv[1], sys.argv[2]

ds_a, ds_b = open_nc(path_a), open_nc(path_b)
var_a, var_b = detect_var(ds_a), detect_var(ds_b)
info_a, info_b = inspect(ds_a), inspect(ds_b)

da_a = to_wgs84_region(web_prep(ds_a, var_a), info_a)
da_b = to_wgs84_region(web_prep(ds_b, var_b), info_b)

# Step1 — 원본 해상도 2장
save_map(da_a, f"{OUT}/step1_{var_a}.png", f"[Step1] {var_a} ({info_a['dlon']:.3f}°)")
save_map(da_b, f"{OUT}/step1_{var_b}.png", f"[Step1] {var_b} ({info_b['dlon']:.3f}°)")

# Step2 Coarse — 다운샘플 2장 + 산점도 1장
ref_c, eval_c, _ = match_resolution(da_a, da_b)
save_map(ref_c,  f"{OUT}/step2_ref_coarse.png",  "[Step2-Coarse] 기준 (저해상도)")
save_map(eval_c, f"{OUT}/step2_eval_coarse.png", "[Step2-Coarse] 평가 (다운샘플)")
save_scatter(ref_c, eval_c, compute_stats(ref_c, eval_c),
             f"{OUT}/scatter_coarse.png", "Scatter — Coarse")

# Step2 Fine — bilinear 업샘플 2장 + 산점도 1장
res_a = float(abs(np.diff(da_a.lat.values).mean()))
res_b = float(abs(np.diff(da_b.lat.values).mean()))
fine_ref, coarse_eval = (da_a, da_b) if res_a <= res_b else (da_b, da_a)
eval_f = coarse_eval.interp_like(fine_ref, method="linear")
save_map(fine_ref, f"{OUT}/step2_ref_fine.png",  "[Step2-Fine] 기준 (고해상도)")
save_map(eval_f,   f"{OUT}/step2_eval_fine.png", "[Step2-Fine] 평가 (업샘플)")
save_scatter(fine_ref, eval_f, compute_stats(fine_ref, eval_f),
             f"{OUT}/scatter_fine.png", "Scatter — Fine")

print(f"완료 — {OUT}/ 에 이미지 8장 저장됨")
