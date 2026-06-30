import pytest
from src.io_nc import open_nc
import xarray as xr

def test_open_valid_nc(nc_high_res):
    path, _ = nc_high_res
    ds = open_nc(path)
    assert isinstance(ds, xr.Dataset)

def test_open_invalid_extension(tmp_path):
    p = tmp_path / "data.txt"
    p.write_text("not netcdf")
    with pytest.raises(ValueError, match="NetCDF"):
        open_nc(str(p))

def test_open_nonexistent_file():
    with pytest.raises((ValueError, FileNotFoundError)):
        open_nc("/nonexistent/path/file.nc")
