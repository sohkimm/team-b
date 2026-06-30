import numpy as np
import xarray as xr
from scipy import stats


def compute_stats(ref: xr.DataArray, eval_da: xr.DataArray) -> dict:
    """
    Compute statistical metrics between reference and evaluation DataArrays.

    Parameters
    ----------
    ref : xr.DataArray
        Reference (ground truth) data
    eval_da : xr.DataArray
        Evaluation (predicted/simulated) data

    Returns
    -------
    dict
        Dictionary with keys: N, Bias, RMSE, MAE, R, R2
        - N (int): Number of valid (non-NaN) pairs
        - Bias (float): Mean difference (eval - ref)
        - RMSE (float): Root Mean Square Error
        - MAE (float): Mean Absolute Error
        - R (float): Pearson correlation coefficient
        - R2 (float): R-squared (coefficient of determination)

    Notes
    -----
    - NaN values in either array exclude that cell from computation
    - When N==0, all float stats are returned as NaN
    - Bias is computed as eval - ref (positive means eval is higher)
    """
    r = ref.values.flatten().astype(float)
    e = eval_da.values.flatten().astype(float)
    mask = ~(np.isnan(r) | np.isnan(e))

    if mask.sum() == 0:
        return {"N": 0, "Bias": np.nan, "RMSE": np.nan,
                "MAE": np.nan, "R": np.nan, "R2": np.nan}

    r_valid, e_valid = r[mask], e[mask]
    diff = e_valid - r_valid
    bias = float(np.mean(diff))
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    mae = float(np.mean(np.abs(diff)))

    if len(r_valid) < 2 or np.std(r_valid) < 1e-12:
        corr = np.nan
    else:
        result = stats.linregress(r_valid, e_valid)
        corr = float(result.rvalue)

    return {
        "N": int(mask.sum()),
        "Bias": bias,
        "RMSE": rmse,
        "MAE": mae,
        "R": corr,
        "R2": float(corr ** 2) if not np.isnan(corr) else np.nan,
    }
