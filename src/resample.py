import numpy as np


def _dx(da, dim):
    v = da[dim].values
    return float(abs(v[1] - v[0]))


def to_ref_grid(eval_da, ref_da, method="coarsen"):
    if method != "coarsen":
        raise NotImplementedError(f"method={method}는 강화 단계(Task 11)에서 추가")
    fx = int(round(_dx(ref_da, "x") / _dx(eval_da, "x")))
    fy = int(round(_dx(ref_da, "y") / _dx(eval_da, "y")))
    fx, fy = max(fx, 1), max(fy, 1)
    coarse = eval_da.coarsen(x=fx, y=fy, boundary="trim").mean()
    tol = _dx(ref_da, "y") / 2.0
    return coarse.reindex_like(ref_da, method="nearest", tolerance=tol)
