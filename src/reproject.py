import numpy as np


def to_wgs84(da, report):
    if report.grid_kind != "GEOGRAPHIC":
        raise ValueError(
            f"범위 외 격자({report.grid_kind}) — 정규격자 WGS84만 지원합니다.")
    out = da.rename({report.lat_name: "y", report.lon_name: "x"})
    # 경도 −180~180 정규화
    new_x = ((out["x"].values + 180.0) % 360.0) - 180.0
    out = out.assign_coords(x=new_x)
    out = out.sortby("x").sortby("y")
    assert np.all(np.diff(out["x"].values) > 0), "x 비단조 — 정규화/정렬 실패"
    assert np.all(np.diff(out["y"].values) > 0), "y 비단조 — 정렬 실패"
    return out
