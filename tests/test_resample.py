import numpy as np
import xarray as xr
from src.resample import to_ref_grid


def _da(values, x, y):
    return xr.DataArray(np.asarray(values, dtype="float64"),
                        coords={"y": np.asarray(y, dtype="float64"),
                                "x": np.asarray(x, dtype="float64")},
                        dims=("y", "x"), name="v")


def test_coarsen_block_mean_2x():
    # eval 0.125° 4x4, ref 0.25° 2x2 정렬
    ex = np.array([117.0625, 117.1875, 117.3125, 117.4375])
    ey = np.array([24.0625, 24.1875, 24.3125, 24.4375])
    evals = np.arange(16.0).reshape(4, 4)
    rx = np.array([117.125, 117.375])
    ry = np.array([24.125, 24.375])
    ref = _da(np.zeros((2, 2)), rx, ry)
    out = to_ref_grid(_da(evals, ex, ey), ref)
    # 좌상 블록 평균 = mean([0,1,4,5]) = 2.5
    assert np.isclose(out.sel(x=117.125, y=24.125).item(), 2.5)
    assert out.shape == (2, 2)


def test_ref_unchanged():
    rx = np.array([117.125, 117.375]); ry = np.array([24.125, 24.375])
    ref = _da(np.ones((2, 2)), rx, ry)
    ref_copy = ref.copy(deep=True)
    ex = np.array([117.0625, 117.1875, 117.3125, 117.4375])
    ey = np.array([24.0625, 24.1875, 24.3125, 24.4375])
    to_ref_grid(_da(np.arange(16.0).reshape(4, 4), ex, ey), ref)
    assert ref.equals(ref_copy)
