import numpy as np
import pytest
import xarray as xr
from src.io_nc import open_nc


def test_open_nc_rejects_non_netcdf(tmp_path):
    p = tmp_path / "notnc.txt"
    p.write_text("hello")
    with pytest.raises(ValueError, match="nc 파일만 지원"):
        open_nc(str(p))


def test_open_nc_opens_real_netcdf(tmp_path):
    p = tmp_path / "sample.nc"
    xr.Dataset({"v": ("x", np.arange(3.0))}).to_netcdf(p)
    ds = open_nc(str(p))
    assert "v" in ds
    ds.close()
