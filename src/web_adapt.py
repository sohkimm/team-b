"""웹 입력 정규화 어댑터 — lee 파이프라인에 넣기 전 전처리만 담당.

lee의 모듈(inspect/apply_qc/to_wgs84_region/...)은 변수명을 받고(자동탐지 X),
time/depth 싱글톤을 안 줄이며, 좌표명 lat/lon을 가정한다. 업로드 파일은 그렇지
않을 수 있으므로 여기서 (1) 염분 변수 자동탐지 (2) time/depth squeeze
(3) latitude/longitude → lat/lon rename 만 한다. lee 알고리즘은 건드리지 않는다.
"""
SAL_NAMES = ("sos", "smap_sss", "sss", "salinity", "so")


def detect_var(ds):
    """염분 변수 자동탐지: standard_name → 알려진 이름 → 2D+ float 첫 변수."""
    for v in ds.data_vars:
        sn = str(ds[v].attrs.get("standard_name", "")).lower()
        if "salinity" in sn:
            return v
    for name in SAL_NAMES:
        if name in ds.data_vars:
            return name
    for v in ds.data_vars:
        if ds[v].ndim >= 2:
            return v
    raise ValueError(f"염분 변수 자동탐지 실패. 후보: {list(ds.data_vars)}")


def prep(ds, var, time_index=0):
    """lee의 apply_qc 결과를 2D(lat,lon)로 정규화해 반환."""
    from src.qc import apply_qc
    da = apply_qc(ds, var)
    if "time" in da.dims:
        da = da.isel(time=time_index)
    da = da.squeeze(drop=True)
    ren = {}
    if "latitude" in da.dims:
        ren["latitude"] = "lat"
    if "longitude" in da.dims:
        ren["longitude"] = "lon"
    return da.rename(ren) if ren else da
