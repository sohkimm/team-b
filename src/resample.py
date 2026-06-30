import numpy as np


def _dx(da, dim):
    v = da[dim].values
    return float(abs(v[1] - v[0]))


def to_grid(src_da, target_da, method="auto"):
    """src_da를 target_da 격자에 정합한다. target_da는 변형하지 않는다.

    method:
      "auto"    배율로 자동 — target이 더 거칠면 coarsen(블록평균),
                더 촘촘하면 linear(bilinear 업샘플), 비슷하면 nearest
      "coarsen" 정수배 블록평균 (다운샘플 전용)
      "linear"  bilinear 보간 (업샘플/일반)
      "nearest" 최근접 스냅
    """
    tdx, tdy = _dx(target_da, "x"), _dx(target_da, "y")
    sdx, sdy = _dx(src_da, "x"), _dx(src_da, "y")
    if method == "auto":
        if tdx > sdx * 1.5:
            method = "coarsen"
        elif tdx < sdx / 1.5:
            method = "linear"
        else:
            method = "nearest"
    if method == "coarsen":
        fx = max(int(round(tdx / sdx)), 1)
        fy = max(int(round(tdy / sdy)), 1)
        coarse = src_da.coarsen(x=fx, y=fy, boundary="trim").mean()
        return coarse.reindex_like(target_da, method="nearest", tolerance=tdy / 2.0)
    if method in ("linear", "bilinear"):
        # 저해상도 → 고해상도 업샘플(bilinear). scipy 사용, rasterio 불필요.
        return src_da.interp_like(target_da, method="linear")
    if method == "nearest":
        return src_da.reindex_like(target_da, method="nearest", tolerance=tdy / 2.0)
    raise ValueError(f"알 수 없는 method={method}")


def to_ref_grid(eval_da, ref_da, method="coarsen"):
    """하위호환 별칭: eval_da를 ref_da 격자로 정합 (기본 coarsen 다운샘플)."""
    return to_grid(eval_da, ref_da, method=method)
