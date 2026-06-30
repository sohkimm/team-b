"""단계별(SSE) 오케스트레이터 — lee 파이프라인 위에서 동작.

lee의 inspect / apply_qc / to_wgs84_region / match_resolution / compute_stats 를
호출하고(입력 정규화는 web_adapt 담당), 프론트가 먹을 SSE 이벤트로 변환한다.
lee 알고리즘은 건드리지 않는다.
"""
from src.io_nc import open_nc
from src.inspect_nc import inspect
from src.reproject import to_wgs84_region
from src.resample import match_resolution
from src.metrics import compute_stats
from src.web_adapt import detect_var, prep
from src.web_serialize import field_to_json, scatter_to_json, safe_num


def _inspect_row(info, var):
    return {
        "TYPE": info.get("data_type") or "n/a",
        "VAR": var,
        "GRID": info.get("grid_type") or "n/a",
        "RES": (f"{info['dlon']:g}°" if info.get("dlon") else "n/a"),
        "TIME": str(info.get("time_res") or "n/a"),
        "CRS": str(info.get("crs") or "n/a"),
    }


def _metrics_rows(s_hi, s_lo):
    defs = [("N", "표본수"), ("Bias", "편차"), ("RMSE", "평균제곱근"),
            ("MAE", "평균절대"), ("R", "상관계수"), ("R²", "결정계수")]
    keys = ["N", "Bias", "RMSE", "MAE", "R", "R2"]
    rows = []
    for (label, kr), key in zip(defs, keys):
        rows.append({"label": label, "kr": kr,
                     "hilo": safe_num(s_hi[key]) if key != "N" else int(s_hi[key]),
                     "lohi": safe_num(s_lo[key]) if key != "N" else int(s_lo[key])})
    return rows


def analyze_stream(path_a, path_b, *, time_index=0, var_a=None, var_b=None):
    step = 0
    try:
        # ── 1. 입력 검증 ──
        step = 1
        yield {"event": "step", "data": {"n": 1, "status": "active"}}
        ds_a = open_nc(path_a)
        ds_b = open_nc(path_b)
        yield {"event": "step", "data": {"n": 1, "status": "done"}}

        # ── 2. Inspect + QC ──
        step = 2
        yield {"event": "step", "data": {"n": 2, "status": "active"}}
        info_a = inspect(ds_a)
        info_b = inspect(ds_b)
        va = var_a or detect_var(ds_a)
        vb = var_b or detect_var(ds_b)
        inspect_payload = {"a": _inspect_row(info_a, va), "b": _inspect_row(info_b, vb)}
        qc = [{"k": "_FillValue→NaN"}, {"k": "valid_range clip"}, {"k": "flag mask"}]
        da_a = prep(ds_a, va, time_index)   # apply_qc + squeeze + lat/lon
        da_b = prep(ds_b, vb, time_index)
        yield {"event": "step",
               "data": {"n": 2, "status": "done", "inspect": inspect_payload, "qc": qc}}

        # ── 3. WGS84 + AOI(24–38N/117–131E) → native 맵 2종 ──
        step = 3
        yield {"event": "step", "data": {"n": 3, "status": "active"}}
        a_aoi = to_wgs84_region(da_a, info_a)   # CMEMS, dims lat/lon
        b_aoi = to_wgs84_region(da_b, info_b)   # SMAP
        maps3 = {"cmems": field_to_json(a_aoi), "smap": field_to_json(b_aoi)}
        yield {"event": "step", "data": {"n": 3, "status": "done", "maps": maps3}}

        # ── 4. 해상도 정합 (lee match_resolution: 고해상도를 저해상도로 average 다운샘플) ──
        step = 4
        yield {"event": "step", "data": {"n": 4, "status": "active"}}
        coarse, fine_res, label = match_resolution(a_aoi, b_aoi)  # label: 'A'(=CMEMS) | 'B'(=SMAP)
        coarse_name = "CMEMS" if label == "A" else "SMAP"
        fine_name = "SMAP" if label == "A" else "CMEMS"
        fine_orig = b_aoi if label == "A" else a_aoi
        yield {"event": "step", "data": {"n": 4, "status": "done"}}

        # ── 5. 검증 (양방향) ──
        step = 5
        yield {"event": "step", "data": {"n": 5, "status": "active"}}
        coarse_up = coarse.interp_like(fine_orig, method="linear")
        s_hi = compute_stats(ref=coarse, eval_da=fine_res)       # 고→저 (권장)
        s_lo = compute_stats(ref=fine_orig, eval_da=coarse_up)   # 저→고 (비교)
        metrics = _metrics_rows(s_hi, s_lo)
        scatter = {
            "hilo": {**scatter_to_json(coarse, fine_res),
                     "refLabel": coarse_name, "evalLabel": fine_name},
            "lohi": {**scatter_to_json(fine_orig, coarse_up),
                     "refLabel": fine_name, "evalLabel": coarse_name},
        }
        bias = safe_num(s_hi["Bias"]) or 0.0
        r = safe_num(s_hi["R"]) or 0.0
        verdict = {
            "recommended": "hilo",
            "headline": "HI→LO (고→저) — recommended",
            "bullets": [
                "면적평균(average) 다운샘플 → 안정적 Bias / RMSE.",
                f"R≈{r:.2f}, Bias {bias:+.2f} PSU (기준 {coarse_name}).",
            ],
        }
        yield {"event": "step",
               "data": {"n": 5, "status": "done", "metrics": metrics,
                        "scatter": scatter, "verdict": verdict}}

        yield {"event": "done", "data": {"ok": True}}
    except Exception as e:
        yield {"event": "error", "data": {"detail": str(e), "n": step}}
