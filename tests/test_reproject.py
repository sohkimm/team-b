import numpy as np
import pytest
from src.reproject import to_wgs84
from src.inspect_nc import InspectReport
from tests.conftest import make_grid_da


def _report(grid_kind="GEOGRAPHIC"):
    return InspectReport(grid_kind, 0.5, 0.5, "latitude", "longitude",
                         "sea_surface_salinity", "1e-3", 1)


def test_to_wgs84_renames_and_sorts():
    # lat 내림차순 + lon 0~360
    da = make_grid_da(np.arange(12).reshape(3, 4),
                      lat=[2.0, 1.0, 0.0], lon=[10.0, 200.0, 350.0, 5.0])
    out = to_wgs84(da, _report())
    assert "x" in out.dims and "y" in out.dims
    assert np.all(np.diff(out["y"].values) > 0)   # lat 오름차순
    assert np.all(np.diff(out["x"].values) > 0)   # lon 오름차순
    assert out["x"].values.min() >= -180 and out["x"].values.max() <= 180


def test_to_wgs84_rejects_irregular():
    da = make_grid_da(np.zeros((2, 2)), lat=[0.0, 1.0], lon=[0.0, 1.0])
    with pytest.raises(ValueError, match="범위 외"):
        to_wgs84(da, _report(grid_kind="IRREGULAR"))
