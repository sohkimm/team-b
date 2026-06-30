import xarray as xr


def open_nc(path):
    with open(path, "rb") as f:
        magic = f.read(4)
    if not (magic[:3] == b"CDF" or magic == b"\x89HDF"):
        raise ValueError(f"nc 파일만 지원: {path} (magic={magic!r})")
    return xr.open_dataset(path, decode_cf=True)
