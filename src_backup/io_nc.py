import os
import xarray as xr


def open_nc(path: str) -> xr.Dataset:
    if not path.endswith(".nc"):
        raise ValueError(f"NetCDF(.nc) 파일만 지원합니다: {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"파일 없음: {path}")
    try:
        return xr.open_dataset(path, mask_and_scale=True)
    except Exception as e:
        raise ValueError(f"NC 파일 열기 실패: {path}\n{e}") from e
