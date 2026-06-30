import numpy as np
import xarray as xr
from src.visualize import make_scatter


def test_make_scatter_returns_figure():
    a = xr.DataArray(np.array([[1.0, 2.0], [3.0, 4.0]]), dims=("y", "x"))
    b = xr.DataArray(np.array([[1.1, 2.1], [2.9, 4.2]]), dims=("y", "x"))
    stat = {"N": 4, "Bias": 0.075, "RMSE": 0.13, "R": 0.99, "R2_nse": 0.98, "MAE": 0.12}
    fig = make_scatter(a, b, stat)
    assert fig is not None
    assert len(fig.axes) >= 1
