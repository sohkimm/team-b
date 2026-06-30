import numpy as np
import xarray as xr
from src.resample import to_ref_grid, to_grid


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


def test_to_grid_upsample_linear():
    # 거친 노드 → 촘촘 격자로 bilinear 업샘플. fine 노드가 coarse 노드를 포함하도록 구성.
    coarse = _da([[10.0, 20.0], [30.0, 40.0]], x=[0.0, 1.0], y=[0.0, 1.0])
    target = _da(np.zeros((3, 3)), x=[0.0, 0.5, 1.0], y=[0.0, 0.5, 1.0])
    out = to_grid(coarse, target, method="linear")
    assert out.shape == (3, 3)
    # 원본 노드와 겹치는 지점은 원본값 그대로
    assert np.isclose(out.sel(x=0.0, y=0.0).item(), 10.0)
    assert np.isclose(out.sel(x=1.0, y=1.0).item(), 40.0)
    # x 중점(y=0): (10+20)/2 = 15
    assert np.isclose(out.sel(x=0.5, y=0.0).item(), 15.0)
    # 정중앙 bilinear: (10+20+30+40)/4 = 25
    assert np.isclose(out.sel(x=0.5, y=0.5).item(), 25.0)
    # target은 변형되지 않음
    assert np.all(target.values == 0.0)


def test_to_grid_auto_directions():
    cx = np.array([117.125, 117.375]); cy = np.array([24.125, 24.375])
    coarse = _da(np.ones((2, 2)), cx, cy)
    fx = np.array([117.0625, 117.1875, 117.3125, 117.4375])
    fy = np.array([24.0625, 24.1875, 24.3125, 24.4375])
    fine = _da(np.arange(16.0).reshape(4, 4), fx, fy)
    # target이 더 촘촘(fine) → 업샘플 → (4,4)
    assert to_grid(coarse, fine, method="auto").shape == (4, 4)
    # target이 더 거침(coarse) → 다운샘플 → (2,2)
    assert to_grid(fine, coarse, method="auto").shape == (2, 2)
