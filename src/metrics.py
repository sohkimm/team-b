import numpy as np


def _to_1d(a):
    return np.asarray(getattr(a, "values", a), dtype="float64").ravel()


def stats(eval, ref):
    e = _to_1d(eval)
    r = _to_1d(ref)
    mask = ~np.isnan(e) & ~np.isnan(r)
    e, r = e[mask], r[mask]
    n = int(e.size)
    if n == 0:
        return {"N": 0, "Bias": np.nan, "RMSE": np.nan,
                "MAE": np.nan, "R": np.nan, "R2_nse": np.nan}
    diff = e - r
    bias = float(np.mean(diff))
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    mae = float(np.mean(np.abs(diff)))
    r_pearson = float(np.corrcoef(e, r)[0, 1]) if n > 1 else np.nan
    sse = float(np.sum(diff ** 2))
    sst = float(np.sum((r - np.mean(r)) ** 2))
    r2 = 1.0 - sse / sst if sst > 0 else np.nan
    return {"N": n, "Bias": bias, "RMSE": rmse, "MAE": mae,
            "R": r_pearson, "R2_nse": r2}
