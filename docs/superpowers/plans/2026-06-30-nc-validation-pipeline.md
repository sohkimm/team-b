# NC 검증 파이프라인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CMEMS L4 SSS(0.125°)와 SMAP L3 8일합성 SSS(0.25°) 두 NetCDF를 동일 절차로 표준화·정합·통계검증하는 파이프라인을 만든다.

**Architecture:** 순수 함수 변환 모듈(`io_nc`/`inspect_nc`/`reproject`/`resample`/`metrics`) + IO 어댑터(`visualize`/`io_out`)를 `pipeline.run`이 오케스트레이션한다. 기준 격자는 저해상도(SMAP) native 격자를 AOI로 크롭한 것이며 ref는 재보간하지 않는다. 고해상도(CMEMS)는 정수 2배라 `coarsen(2,2).mean()` 블록평균으로 ref 격자에 정합(MVP, rasterio 비의존).

**Tech Stack:** Python 3.10, xarray, netCDF4, numpy, scipy, pandas, matplotlib. (강화 단계에서만 rioxarray/rasterio, cartopy)

## Global Constraints

- 좌표계: WGS84(EPSG:4326), 차원명은 표준화 후 `x`(경도)/`y`(위도), lat 오름차순, lon −180~180.
- 기준 격자: 저해상도 자료의 native 격자를 AOI로 크롭(합성 격자 만들지 않음). **ref는 절대 재보간하지 않는다.**
- AOI 기본값: lat 24~38°N, lon 117~131°E.
- 비교 변수 차단 기준은 **standard_name='sea_surface_salinity'** 만. units 문자열 불일치는 경고만(중단 금지).
- 헤드라인 통계: 대칭지표 `N, Bias(=eval−ref), RMSE, MAE, R(Pearson)`. `R2_nse=1−SSE/SST`는 부차지표(음수 허용).
- NaN은 채우지 않고 전파. 통계는 두 격자 모두 유효한 셀만.
- 투영/비정규격자 입력은 `to_wgs84`에서 명시적 중단(범위 외).
- MVP(Task 0~8)는 `xarray netCDF4 numpy scipy pandas matplotlib`만 사용. rasterio/cartopy는 강화(Task 9~11) 전용.
- 모든 소스는 `src/`, 테스트는 `tests/`. 각 task 끝에 commit.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `src/metrics.py` | 통계량 계산 (대칭지표 + NSE) |
| `src/io_nc.py` | NetCDF 입력 검증·개방 |
| `src/inspect_nc.py` | `InspectReport`, `is_regular_grid`, 염분 변수 탐지 |
| `src/reproject.py` | WGS84 표준화(무보간), 투영/비정규 중단 |
| `src/resample.py` | 저해상도 ref 격자로 정합(coarsen) |
| `src/visualize.py` | `make_scatter`(MVP), `make_map`(강화) → Figure 반환 |
| `src/io_out.py` | CSV/PNG 디스크 저장 |
| `src/pipeline.py` | `Config`, `run` 오케스트레이션 |
| `run_validation.py` | CLI 진입점 |
| `tests/conftest.py` | 합성 NetCDF/DataArray 픽스처 헬퍼 |
| `tests/test_*.py` | 모듈별 단위 테스트 + 통합 스모크 |

---

## Task 0: 프로젝트 스캐폴드 + 환경

**Files:**
- Create: `src/__init__.py`, `tests/__init__.py`, `pytest.ini`
- Create: `tests/conftest.py`
- Modify: `environment.yml` (이미 경량화됨 — 확인만)

**Interfaces:**
- Produces: `tests/conftest.py`의 `make_grid_da(values, lat, lon, name, attrs)` 픽스처 헬퍼 — 이후 모든 테스트가 합성 DataArray 생성에 사용.

- [ ] **Step 1: 디렉터리/패키지 파일 생성**

```bash
mkdir -p src tests
touch src/__init__.py tests/__init__.py
```

- [ ] **Step 2: pytest 설정 작성**

`pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v
```

- [ ] **Step 3: conftest 픽스처 헬퍼 작성**

`tests/conftest.py`:
```python
import numpy as np
import xarray as xr


def make_grid_da(values, lat, lon, name="sea_surface_salinity", attrs=None):
    """위/경도 1D 좌표를 가진 합성 DataArray. values shape = (len(lat), len(lon))."""
    da = xr.DataArray(
        np.asarray(values, dtype="float64"),
        coords={"latitude": np.asarray(lat, dtype="float64"),
                "longitude": np.asarray(lon, dtype="float64")},
        dims=("latitude", "longitude"),
        name=name,
        attrs=attrs or {"standard_name": "sea_surface_salinity", "units": "1e-3"},
    )
    return da
```

- [ ] **Step 4: 환경 생성 검증 (30분 타임박스)**

Run:
```bash
micromamba env create -f environment.yml -y || conda env create -f environment.yml
micromamba run -n ncval python -c "import xarray, netCDF4, numpy, scipy, pandas, matplotlib; print('MVP deps OK')"
```
Expected: `MVP deps OK`. 30분 초과 시 폴백: `python3 -m venv .venv && .venv/bin/pip install xarray netCDF4 numpy scipy pandas matplotlib pytest` (전부 순수 휠).

- [ ] **Step 5: PROCESS_LOG 필수 로그 (step0)**

`submit/teamB_ksh_PROCESS_LOG.md`에 환경 구축·실파일 introspection 결과 1항목 추가(인용형).

- [ ] **Step 6: Commit**

```bash
git add src tests pytest.ini
git commit -m "chore: project scaffold + test fixture helper"
```

---

## Task 1: metrics.py — 통계량 (가장 쉬움, 0 의존성, 최우선)

**Files:**
- Create: `src/metrics.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Produces: `stats(eval, ref) -> dict` — 키: `N`(int), `Bias`(float), `RMSE`(float), `MAE`(float), `R`(float), `R2_nse`(float). 입력은 array-like(np.ndarray 또는 xr.DataArray); 둘 다 유효(non-NaN)한 셀만 사용. `Bias = mean(eval - ref)`.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_metrics.py`:
```python
import numpy as np
from src.metrics import stats


def test_stats_handcalc():
    ref = np.array([1.0, 2.0, 3.0, 4.0])
    evalv = np.array([1.1, 2.1, 2.9, 4.2])
    s = stats(evalv, ref)
    assert s["N"] == 4
    # diffs = [0.1, 0.1, -0.1, 0.2]; bias = 0.075
    assert np.isclose(s["Bias"], 0.075)
    assert np.isclose(s["RMSE"], np.sqrt(np.mean([0.01, 0.01, 0.01, 0.04])))
    assert np.isclose(s["MAE"], np.mean([0.1, 0.1, 0.1, 0.2]))
    assert s["R"] > 0.98


def test_stats_masks_nan_both():
    ref = np.array([1.0, np.nan, 3.0])
    evalv = np.array([1.0, 2.0, np.nan])
    s = stats(evalv, ref)
    assert s["N"] == 1  # only index 0 valid in both


def test_nse_can_be_negative():
    ref = np.array([1.0, 2.0, 3.0])
    evalv = np.array([3.0, 2.0, 1.0])  # worse than mean
    s = stats(evalv, ref)
    assert s["R2_nse"] < 0
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.metrics'`

- [ ] **Step 3: 최소 구현**

`src/metrics.py`:
```python
import numpy as np


def _to_1d(a):
    return np.asarray(getattr(a, "values", a), dtype="float64").ravel()


def stats(eval, ref):
    e = _to_1d(eval)
    r = _to_1d(ref)
    mask = ~np.isnan(e) & ~np.isnan(r)
    e, r = e[mask], r[mask]
    n = int(e.size)
    if n == 0:
        return {"N": 0, "Bias": np.nan, "RMSE": np.nan,
                "MAE": np.nan, "R": np.nan, "R2_nse": np.nan}
    diff = e - r
    bias = float(np.mean(diff))
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    mae = float(np.mean(np.abs(diff)))
    r_pearson = float(np.corrcoef(e, r)[0, 1]) if n > 1 else np.nan
    sse = float(np.sum(diff ** 2))
    sst = float(np.sum((r - np.mean(r)) ** 2))
    r2 = 1.0 - sse / sst if sst > 0 else np.nan
    return {"N": n, "Bias": bias, "RMSE": rmse, "MAE": mae,
            "R": r_pearson, "R2_nse": r2}
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_metrics.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/metrics.py tests/test_metrics.py
git commit -m "feat: metrics with symmetric stats + NSE"
```

---

## Task 2: io_nc.py — NetCDF 입력 검증

**Files:**
- Create: `src/io_nc.py`
- Test: `tests/test_io_nc.py`

**Interfaces:**
- Consumes: 없음.
- Produces: `open_nc(path) -> xr.Dataset` — magic(`CDF`/`HDF`) 검사 후 `xr.open_dataset(path, decode_cf=True)`. NetCDF 아니면 `ValueError("nc 파일만 지원: ...")`.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_io_nc.py`:
```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_io_nc.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현**

`src/io_nc.py`:
```python
import xarray as xr


def open_nc(path):
    with open(path, "rb") as f:
        magic = f.read(4)
    if not (magic[:3] == b"CDF" or magic == b"\x89HDF"):
        raise ValueError(f"nc 파일만 지원: {path} (magic={magic!r})")
    return xr.open_dataset(path, decode_cf=True)
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_io_nc.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/io_nc.py tests/test_io_nc.py
git commit -m "feat: io_nc with NetCDF magic-byte validation"
```

---

## Task 3: inspect_nc.py — 격자 판별 + InspectReport + 변수 탐지

**Files:**
- Create: `src/inspect_nc.py`
- Test: `tests/test_inspect_nc.py`

**Interfaces:**
- Consumes: `tests/conftest.py:make_grid_da`.
- Produces:
  - `is_regular_grid(lat, lon, rtol=1e-4) -> bool`
  - `detect_salinity_var(ds, override=None) -> str` — `standard_name=='sea_surface_salinity'`인 변수명. override 우선. 없으면 `ValueError`(후보 변수 목록 포함).
  - `InspectReport` dataclass: `grid_kind`(str: "GEOGRAPHIC"/"PROJECTED"/"IRREGULAR"), `dlat`(float), `dlon`(float), `lat_name`(str), `lon_name`(str), `var_name`(str), `units`(str), `time_len`(int).
  - `describe(ds, var_override=None) -> InspectReport`.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_inspect_nc.py`:
```python
import numpy as np
import pytest
import xarray as xr
from src.inspect_nc import is_regular_grid, detect_salinity_var, describe


def test_is_regular_grid_true():
    lat = np.arange(0, 5, 0.5)
    lon = np.arange(100, 110, 0.5)
    assert is_regular_grid(lat, lon) is True


def test_is_regular_grid_false_2d():
    lat = np.zeros((3, 3))
    lon = np.zeros((3, 3))
    assert is_regular_grid(lat, lon) is False


def test_detect_salinity_picks_sss_not_density():
    ds = xr.Dataset({
        "sss": ("x", np.arange(3.0), {"standard_name": "sea_surface_salinity"}),
        "ssd": ("x", np.arange(3.0), {"standard_name": "sea_surface_density"}),
    })
    assert detect_salinity_var(ds) == "sss"


def test_detect_salinity_override():
    ds = xr.Dataset({"foo": ("x", np.arange(3.0))})
    assert detect_salinity_var(ds, override="foo") == "foo"


def test_describe_geographic(make_sss_ds):
    rep = describe(make_sss_ds)
    assert rep.grid_kind == "GEOGRAPHIC"
    assert np.isclose(rep.dlat, 0.25)
    assert rep.var_name == "sea_surface_salinity"
    assert rep.time_len == 1
```

`tests/conftest.py`에 픽스처 추가:
```python
import pytest


@pytest.fixture
def make_sss_ds():
    lat = np.arange(24.0, 38.0, 0.25)
    lon = np.arange(117.0, 131.0, 0.25)
    data = np.ones((1, lat.size, lon.size))
    return xr.Dataset(
        {"sea_surface_salinity": (("time", "latitude", "longitude"), data,
                                  {"standard_name": "sea_surface_salinity", "units": "1e-3"})},
        coords={"time": [np.datetime64("2026-01-01")], "latitude": lat, "longitude": lon},
    )
```
(conftest 상단에 `import numpy as np`, `import xarray as xr` 이미 있음 — 없으면 추가)

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_inspect_nc.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현**

`src/inspect_nc.py`:
```python
from dataclasses import dataclass
import numpy as np

_LAT_NAMES = ("latitude", "lat", "nav_lat", "y")
_LON_NAMES = ("longitude", "lon", "nav_lon", "x")


@dataclass
class InspectReport:
    grid_kind: str
    dlat: float
    dlon: float
    lat_name: str
    lon_name: str
    var_name: str
    units: str
    time_len: int


def is_regular_grid(lat, lon, rtol=1e-4):
    lat = np.asarray(lat)
    lon = np.asarray(lon)
    if lat.ndim != 1 or lon.ndim != 1:
        return False
    dlat, dlon = np.diff(lat), np.diff(lon)
    if dlat.size == 0 or dlon.size == 0:
        return False
    return bool(np.allclose(dlat, dlat[0], rtol=rtol)
                and np.allclose(dlon, dlon[0], rtol=rtol))


def detect_salinity_var(ds, override=None):
    if override is not None:
        return override
    for name, var in ds.data_vars.items():
        if var.attrs.get("standard_name") == "sea_surface_salinity":
            return name
    raise ValueError(
        f"sea_surface_salinity 변수 자동탐지 실패. 후보: {list(ds.data_vars)} "
        f"— --var-a/--var-b 로 지정하세요.")


def _find_coord(ds, names):
    for n in names:
        if n in ds.coords or n in ds.variables:
            return n
    raise ValueError(f"좌표 미발견: {names} 중 없음 (있는 좌표: {list(ds.coords)})")


def describe(ds, var_override=None):
    lat_name = _find_coord(ds, _LAT_NAMES)
    lon_name = _find_coord(ds, _LON_NAMES)
    lat = np.asarray(ds[lat_name].values)
    lon = np.asarray(ds[lon_name].values)
    regular = is_regular_grid(lat, lon)
    grid_kind = "GEOGRAPHIC" if regular else "IRREGULAR"
    dlat = float(abs(lat[1] - lat[0])) if lat.ndim == 1 and lat.size > 1 else float("nan")
    dlon = float(abs(lon[1] - lon[0])) if lon.ndim == 1 and lon.size > 1 else float("nan")
    var_name = detect_salinity_var(ds, override=var_override)
    units = ds[var_name].attrs.get("units", "")
    time_len = int(ds.sizes.get("time", 1))
    return InspectReport(grid_kind, dlat, dlon, lat_name, lon_name,
                         var_name, units, time_len)
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_inspect_nc.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/inspect_nc.py tests/test_inspect_nc.py tests/conftest.py
git commit -m "feat: inspect_nc grid classification + salinity var detection"
```

---

## Task 4: reproject.py — WGS84 표준화(무보간)

**Files:**
- Create: `src/reproject.py`
- Test: `tests/test_reproject.py`

**Interfaces:**
- Consumes: `src/inspect_nc.py:InspectReport`, `tests/conftest.py:make_grid_da`.
- Produces: `to_wgs84(da, report) -> xr.DataArray` — 차원명 `x`/`y`로 rename, 경도 −180~180 정규화 후 `sortby("x")`, `sortby("y")`. `report.grid_kind != "GEOGRAPHIC"`면 `ValueError`(범위 외). 결과는 1D `x`,`y` 좌표 오름차순.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_reproject.py`:
```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_reproject.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현**

`src/reproject.py`:
```python
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
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_reproject.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/reproject.py tests/test_reproject.py
git commit -m "feat: reproject WGS84 standardization (no interpolation)"
```

---

## Task 5: resample.py — 저해상도 ref 격자로 정합 (coarsen)

**Files:**
- Create: `src/resample.py`
- Test: `tests/test_resample.py`

**Interfaces:**
- Consumes: `to_wgs84` 출력 형식(`x`/`y` 1D 오름차순 DataArray).
- Produces: `to_ref_grid(eval_da, ref_da, method="coarsen") -> xr.DataArray` — eval을 ref 격자에 정합. `method="coarsen"`: factor=round(ref dx / eval dx)로 `coarsen(x=f,y=f,boundary="trim").mean()` 후 `reindex_like(ref_da, method="nearest", tolerance=ref_dy/2)`. **ref_da는 변형하지 않음.**

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_resample.py`:
```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_resample.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현**

`src/resample.py`:
```python
import numpy as np


def _dx(da, dim):
    v = da[dim].values
    return float(abs(v[1] - v[0]))


def to_ref_grid(eval_da, ref_da, method="coarsen"):
    if method != "coarsen":
        raise NotImplementedError(f"method={method}는 강화 단계(Task 11)에서 추가")
    fx = int(round(_dx(ref_da, "x") / _dx(eval_da, "x")))
    fy = int(round(_dx(ref_da, "y") / _dx(eval_da, "y")))
    fx, fy = max(fx, 1), max(fy, 1)
    coarse = eval_da.coarsen(x=fx, y=fy, boundary="trim").mean()
    tol = _dx(ref_da, "y") / 2.0
    return coarse.reindex_like(ref_da, method="nearest", tolerance=tol)
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_resample.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/resample.py tests/test_resample.py
git commit -m "feat: resample high-res to coarse ref grid via coarsen block-mean"
```

---

## Task 6: visualize.py + io_out.py — 산점도 Figure + 저장

**Files:**
- Create: `src/visualize.py`, `src/io_out.py`
- Test: `tests/test_visualize.py`, `tests/test_io_out.py`

**Interfaces:**
- Consumes: `metrics.stats` 출력 dict.
- Produces:
  - `make_scatter(eval_da, ref_da, stat) -> matplotlib.figure.Figure` — 1:1 산점도 + 통계박스(N/Bias/RMSE/R). Agg 백엔드.
  - `io_out.save_fig(fig, path) -> None`, `io_out.save_csv(rows, path) -> None` (rows=list[dict]).

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_visualize.py`:
```python
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
```

`tests/test_io_out.py`:
```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.io_out import save_fig, save_csv


def test_save_fig_writes_png(tmp_path):
    fig = plt.figure()
    p = tmp_path / "out.png"
    save_fig(fig, str(p))
    assert p.exists() and p.stat().st_size > 0


def test_save_csv_writes(tmp_path):
    p = tmp_path / "out.csv"
    save_csv([{"N": 4, "RMSE": 0.13}], str(p))
    assert p.exists()
    assert "RMSE" in p.read_text()
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_visualize.py tests/test_io_out.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현**

`src/visualize.py`:
```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def make_scatter(eval_da, ref_da, stat):
    e = np.asarray(getattr(eval_da, "values", eval_da)).ravel()
    r = np.asarray(getattr(ref_da, "values", ref_da)).ravel()
    mask = ~np.isnan(e) & ~np.isnan(r)
    e, r = e[mask], r[mask]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(r, e, s=6, alpha=0.4)
    lo = float(min(r.min(), e.min())) if e.size else 0.0
    hi = float(max(r.max(), e.max())) if e.size else 1.0
    ax.plot([lo, hi], [lo, hi], "k--", lw=1)
    ax.set_xlabel("기준(ref)")
    ax.set_ylabel("평가(eval)")
    txt = (f"N={stat['N']}\nBias={stat['Bias']:.3f}\n"
           f"RMSE={stat['RMSE']:.3f}\nR={stat['R']:.3f}")
    ax.text(0.05, 0.95, txt, transform=ax.transAxes,
            va="top", ha="left", bbox=dict(boxstyle="round", fc="w"))
    fig.tight_layout()
    return fig
```

`src/io_out.py`:
```python
import csv
import os


def save_fig(fig, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, dpi=120)


def save_csv(rows, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not rows:
        open(path, "w").close()
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_visualize.py tests/test_io_out.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/visualize.py src/io_out.py tests/test_visualize.py tests/test_io_out.py
git commit -m "feat: scatter figure + csv/png io adapters"
```

---

## Task 7: pipeline.py — Config + run 오케스트레이션 (MVP 결승선)

**Files:**
- Create: `src/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `open_nc`, `describe`, `to_wgs84`, `to_ref_grid`, `stats`, `make_scatter`.
- Produces:
  - `Config` dataclass: `aoi=(24.0,38.0,117.0,131.0)`, `ref="auto"`, `var_a=None`, `var_b=None`, `time_index=0`, `method="coarsen"`, `outdir="results"`.
  - `run(path_a, path_b, cfg) -> dict` — 키: `stats`(dict), `figure`(Figure), `ref_name`(str), `eval_name`(str). **디스크 쓰기 안 함.**

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_pipeline.py`:
```python
import numpy as np
import xarray as xr
from src.pipeline import Config, run


def _write(path, lat, lon, val):
    data = np.full((1, lat.size, lon.size), val, dtype="float64")
    ds = xr.Dataset(
        {"sea_surface_salinity": (("time", "latitude", "longitude"), data,
            {"standard_name": "sea_surface_salinity", "units": "1e-3"})},
        coords={"time": [np.datetime64("2026-01-01")],
                "latitude": lat, "longitude": lon})
    ds.to_netcdf(path)


def test_run_end_to_end(tmp_path):
    # A: 0.125° (고해상도/eval), B: 0.25° (저해상도/ref)
    a = tmp_path / "a.nc"; b = tmp_path / "b.nc"
    _write(a, np.arange(24.0, 38.0, 0.125), np.arange(117.0, 131.0, 0.125), 35.0)
    _write(b, np.arange(24.125, 38.0, 0.25), np.arange(117.125, 131.0, 0.25), 35.0)
    res = run(str(a), str(b), Config())
    assert res["ref_name"] == "b.nc"      # 저해상도가 ref
    assert res["stats"]["N"] > 0
    assert np.isclose(res["stats"]["Bias"], 0.0, atol=1e-6)  # 동일값 → bias 0
    assert res["figure"] is not None
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현**

`src/pipeline.py`:
```python
import os
from dataclasses import dataclass, field

from src.io_nc import open_nc
from src.inspect_nc import describe
from src.reproject import to_wgs84
from src.resample import to_ref_grid
from src.metrics import stats
from src.visualize import make_scatter


@dataclass
class Config:
    aoi: tuple = (24.0, 38.0, 117.0, 131.0)   # lat0, lat1, lon0, lon1
    ref: str = "auto"                          # "auto"/"a"/"b"
    var_a: str = None
    var_b: str = None
    time_index: int = 0
    method: str = "coarsen"
    outdir: str = "results"


def _prep(path, var_override, time_index):
    ds = open_nc(path)
    rep = describe(ds, var_override=var_override)
    da = ds[rep.var_name]
    if "time" in da.dims:
        da = da.isel(time=time_index)
    # CMEMS sos는 (time, depth, lat, lon) — depth 등 잔여 싱글톤 차원 제거 → 2D(lat,lon)
    da = da.squeeze(drop=True)
    return to_wgs84(da, rep), rep


def _crop_aoi(da, aoi):
    lat0, lat1, lon0, lon1 = aoi
    return da.sel(y=slice(lat0, lat1), x=slice(lon0, lon1))


def run(path_a, path_b, cfg):
    da_a, rep_a = _prep(path_a, cfg.var_a, cfg.time_index)
    da_b, rep_b = _prep(path_b, cfg.var_b, cfg.time_index)

    if cfg.ref == "a":
        ref_is_a = True
    elif cfg.ref == "b":
        ref_is_a = False
    else:  # auto: coarser(큰 dlon)가 ref. 동률(<5%)이면 a를 ref.
        ref_is_a = rep_a.dlon >= rep_b.dlon * 0.95 and rep_a.dlon >= rep_b.dlon

    if ref_is_a:
        ref_da, eval_da = da_a, da_b
        ref_name = os.path.basename(path_a); eval_name = os.path.basename(path_b)
    else:
        ref_da, eval_da = da_b, da_a
        ref_name = os.path.basename(path_b); eval_name = os.path.basename(path_a)

    ref_aoi = _crop_aoi(ref_da, cfg.aoi)
    eval_on_ref = to_ref_grid(eval_da, ref_aoi, method=cfg.method)
    s = stats(eval_on_ref, ref_aoi)
    fig = make_scatter(eval_on_ref, ref_aoi, s)
    return {"stats": s, "figure": fig, "ref_name": ref_name, "eval_name": eval_name}
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_pipeline.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 전체 테스트 + PROCESS_LOG 필수 로그(첫 결과)**

Run: `pytest -v` → 전부 PASS 확인. `submit/teamB_ksh_PROCESS_LOG.md`에 "MVP 파이프라인 end-to-end 통과" 1항목 추가(인용형).

- [ ] **Step 6: Commit**

```bash
git add src/pipeline.py tests/test_pipeline.py
git commit -m "feat: pipeline.run orchestration (MVP end-to-end)"
```

---

## Task 8: run_validation.py — CLI + 실파일 통합 스모크

**Files:**
- Create: `run_validation.py`
- Test: `tests/test_integration.py`

**Interfaces:**
- Consumes: `Config`, `run`, `io_out.save_fig`, `io_out.save_csv`.
- Produces: CLI `python run_validation.py A.nc B.nc [--var-a] [--var-b] [--ref auto|a|b] [--outdir]`. `results/tables/stats.csv`, `results/figures/step5_scatter.png` 생성.

- [ ] **Step 1: 실패 테스트 작성 (실파일 스모크)**

`tests/test_integration.py`:
```python
import os
import subprocess
import sys
import pytest

A = "dataset-sss-ssd-nrt-daily_20260101T1200Z_P20260122T0000Z.nc"
B = "SMAP_L3_SSS_20260101_8DAYS_V5.0.nc"


@pytest.mark.skipif(not (os.path.exists(A) and os.path.exists(B)),
                    reason="실파일 없음")
def test_cli_smoke(tmp_path):
    out = tmp_path / "results"
    r = subprocess.run(
        [sys.executable, "run_validation.py", A, B, "--outdir", str(out)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (out / "tables" / "stats.csv").exists()
    assert (out / "figures" / "step5_scatter.png").exists()
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_integration.py -v`
Expected: FAIL — `run_validation.py` 없음 (returncode≠0)

- [ ] **Step 3: 최소 구현**

`run_validation.py`:
```python
import argparse
import os

from src.pipeline import Config, run
from src.io_out import save_fig, save_csv


def main():
    ap = argparse.ArgumentParser(description="NC SSS 검증 파이프라인")
    ap.add_argument("path_a")
    ap.add_argument("path_b")
    ap.add_argument("--var-a", default=None)
    ap.add_argument("--var-b", default=None)
    ap.add_argument("--ref", default="auto", choices=["auto", "a", "b"])
    ap.add_argument("--outdir", default="results")
    args = ap.parse_args()

    cfg = Config(ref=args.ref, var_a=args.var_a, var_b=args.var_b,
                 outdir=args.outdir)
    res = run(args.path_a, args.path_b, cfg)

    save_csv([res["stats"]],
             os.path.join(args.outdir, "tables", "stats.csv"))
    save_fig(res["figure"],
             os.path.join(args.outdir, "figures", "step5_scatter.png"))
    s = res["stats"]
    print(f"[ref={res['ref_name']} vs eval={res['eval_name']}] "
          f"N={s['N']} Bias={s['Bias']:.3f} RMSE={s['RMSE']:.3f} R={s['R']:.3f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인 (실파일 있으면)**

Run: `pytest tests/test_integration.py -v`
Expected: PASS (실파일 있을 때) 또는 SKIP. 이어서 수동 실행:
```bash
python run_validation.py "dataset-sss-ssd-nrt-daily_20260101T1200Z_P20260122T0000Z.nc" "SMAP_L3_SSS_20260101_8DAYS_V5.0.nc"
ls results/tables/stats.csv results/figures/step5_scatter.png
```
Expected: 통계 한 줄 출력 + 두 파일 생성. **이 시점이 MVP 완성(도는 결과).**

- [ ] **Step 5: Commit**

```bash
git add run_validation.py tests/test_integration.py
git commit -m "feat: CLI entrypoint + real-file integration smoke (MVP complete)"
```

---

> **여기까지가 MVP.** 아래 Task 9~11은 강화(시간 남는 만큼). NON-GOAL(저→고 진단·오차귀속 코드·open-water 마스킹)은 구현하지 않는다.

---

## Task 9: qc.py — 속성 기반 QC

**Files:**
- Create: `src/qc.py`
- Test: `tests/test_qc.py`
- Modify: `src/pipeline.py:_prep` (QC 적용 추가)

**Interfaces:**
- Consumes: 변수 DataArray.
- Produces: `apply_qc(da) -> da` — `valid_min`/`valid_max`/`valid_range` 밖 → NaN, `_FillValue`/`missing_value` → NaN. (decode_cf가 처리 못 한 잔여 대비)

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_qc.py`:
```python
import numpy as np
import xarray as xr
from src.qc import apply_qc


def test_apply_qc_valid_range():
    da = xr.DataArray(np.array([5.0, 100.0, 35.0]), dims="x",
                      attrs={"valid_min": 0.0, "valid_max": 45.0})
    out = apply_qc(da)
    assert np.isnan(out.values[1])           # 100 > valid_max
    assert out.values[0] == 5.0


def test_apply_qc_fillvalue():
    da = xr.DataArray(np.array([35.0, -999.0]), dims="x",
                      attrs={"_FillValue": -999.0})
    out = apply_qc(da)
    assert np.isnan(out.values[1])
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_qc.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현**

`src/qc.py`:
```python
import numpy as np


def apply_qc(da):
    out = da
    a = da.attrs
    if "valid_range" in a:
        vmin, vmax = a["valid_range"][0], a["valid_range"][1]
    else:
        vmin, vmax = a.get("valid_min"), a.get("valid_max")
    if vmin is not None:
        out = out.where(out >= vmin)
    if vmax is not None:
        out = out.where(out <= vmax)
    for key in ("_FillValue", "missing_value"):
        if key in a:
            out = out.where(out != a[key])
    return out
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_qc.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: pipeline에 연결**

`src/pipeline.py` 상단 import에 `from src.qc import apply_qc` 추가, `_prep`에서 `da = ds[rep.var_name]` 다음 줄에 `da = apply_qc(da)` 삽입. Run: `pytest tests/test_pipeline.py -v` → PASS 확인.

- [ ] **Step 6: Commit**

```bash
git add src/qc.py tests/test_qc.py src/pipeline.py
git commit -m "feat: attribute-based QC masking"
```

---

## Task 10: visualize.make_map — AOI 지도 (cartopy 폴백 포함)

**Files:**
- Modify: `src/visualize.py` (add `make_map`)
- Test: `tests/test_visualize.py` (add)
- Modify: `src/pipeline.py` (figures dict로 확장), `run_validation.py` (지도 저장)

**Interfaces:**
- Produces: `make_map(da, title) -> Figure` — `pcolormesh(shading="nearest")`로 2D 장 표시. cartopy 있으면 해안선, 없으면 plain.

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_visualize.py`에 추가:
```python
def test_make_map_returns_figure():
    import xarray as xr, numpy as np
    from src.visualize import make_map
    da = xr.DataArray(np.random.rand(5, 5),
                      coords={"y": np.linspace(24, 38, 5), "x": np.linspace(117, 131, 5)},
                      dims=("y", "x"))
    fig = make_map(da, "test")
    assert fig is not None
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_visualize.py::test_make_map_returns_figure -v`
Expected: FAIL — `make_map` 없음

- [ ] **Step 3: 최소 구현**

`src/visualize.py`에 추가:
```python
def make_map(da, title=""):
    try:
        import cartopy.crs as ccrs
        proj = ccrs.PlateCarree()
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"projection": proj})
        ax.coastlines(resolution="50m")
        mesh = ax.pcolormesh(da["x"], da["y"], da.values,
                             shading="nearest", transform=proj)
    except Exception:
        fig, ax = plt.subplots(figsize=(6, 6))
        mesh = ax.pcolormesh(da["x"], da["y"], da.values, shading="nearest")
    fig.colorbar(mesh, ax=ax, shrink=0.7)
    ax.set_title(title)
    fig.tight_layout()
    return fig
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_visualize.py -v`
Expected: PASS

- [ ] **Step 5: pipeline/CLI 연결**

`pipeline.run` 반환에 `"map_ref": make_map(ref_aoi, "ref"), "map_eval": make_map(eval_on_ref, "eval")` 추가(import 갱신). `run_validation.py`에서 두 지도를 `results/figures/step4_resampled_A.png`, `..._B.png`로 저장. Run: `pytest -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add src/visualize.py src/pipeline.py run_validation.py tests/test_visualize.py
git commit -m "feat: AOI map rendering with cartopy fallback"
```

---

## Task 11: 가드 강화 + reproject_match(average) 경로

**Files:**
- Modify: `src/pipeline.py` (units 경고, N<10 경고)
- Modify: `src/resample.py` (method="average")
- Test: `tests/test_resample.py` (add, rasterio 있을 때만)

**Interfaces:**
- Produces: `to_ref_grid(..., method="average")` — rioxarray `reproject_match(ref, Resampling.average)`. `src_nodata=np.nan` 명시.

- [ ] **Step 1: 실패 테스트 작성 (rasterio 가드)**

`tests/test_resample.py`에 추가:
```python
import pytest

rioxarray = pytest.importorskip("rioxarray")


def test_average_method_runs():
    import numpy as np, xarray as xr
    from src.resample import to_ref_grid
    ex = np.arange(117.0625, 117.5, 0.125); ey = np.arange(24.0625, 24.5, 0.125)
    ev = xr.DataArray(np.arange(16.0).reshape(4, 4), coords={"y": ey, "x": ex},
                      dims=("y", "x"))
    rx = np.array([117.125, 117.375]); ry = np.array([24.125, 24.375])
    ref = xr.DataArray(np.zeros((2, 2)), coords={"y": ry, "x": rx}, dims=("y", "x"))
    out = to_ref_grid(ev, ref, method="average")
    assert out.shape == (2, 2)
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_resample.py -k average -v`
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: 최소 구현**

`src/resample.py`의 `to_ref_grid`에서 `if method != "coarsen"` 블록을 교체:
```python
    if method == "coarsen":
        fx = int(round(_dx(ref_da, "x") / _dx(eval_da, "x")))
        fy = int(round(_dx(ref_da, "y") / _dx(eval_da, "y")))
        fx, fy = max(fx, 1), max(fy, 1)
        coarse = eval_da.coarsen(x=fx, y=fy, boundary="trim").mean()
        tol = _dx(ref_da, "y") / 2.0
        return coarse.reindex_like(ref_da, method="nearest", tolerance=tol)
    if method in ("average", "bilinear"):
        import rioxarray  # noqa
        from rasterio.enums import Resampling
        rs = Resampling.average if method == "average" else Resampling.bilinear
        src = eval_da.rio.write_crs("EPSG:4326").rio.write_nodata(np.nan, encoded=False)
        ref = ref_da.rio.write_crs("EPSG:4326")
        return src.rio.reproject_match(ref, resampling=rs)
    raise ValueError(f"알 수 없는 method={method}")
```
(상단 `import numpy as np` 이미 있음. `to_ref_grid` 시그니처는 그대로.)

- [ ] **Step 4: pipeline 경고 추가**

`src/pipeline.py`의 `run`에서 `s = stats(...)` 다음에:
```python
    if rep_a.units and rep_b.units and rep_a.units != rep_b.units:
        print(f"[경고] units 표기 불일치(정상일 수 있음): {rep_a.units} vs {rep_b.units}")
    if s["N"] < 10:
        print(f"[경고] 공통 유효 셀 N={s['N']} < 10 — 통계 신뢰 불가")
```

- [ ] **Step 5: 통과 확인**

Run: `pytest -v`
Expected: PASS (rasterio 없으면 average 테스트 SKIP)

- [ ] **Step 6: Commit**

```bash
git add src/resample.py src/pipeline.py tests/test_resample.py
git commit -m "feat: reproject_match average path + units/N guards"
```

---

## Self-Review 결과

- **스펙 커버리지:** [1]입력검증=T2, [2-1]파악=T3, [2-2]QC=T9, [3]WGS84무보간=T4, [4]정합=T5/T11, [5]통계=T1, 시각화=T6/T10, 오케스트레이션=T7, CLI=T8. 헤드라인 대칭지표·NSE=T1. ref 무변형=T5. NON-GOAL(저→고·오차귀속·마스킹)은 의도적 제외. ✅
- **플레이스홀더:** 모든 step에 실제 코드/명령 포함. ✅
- **타입 일관성:** `InspectReport` 필드, `stats` 키(`N/Bias/RMSE/MAE/R/R2_nse`), `to_ref_grid(eval, ref, method)`, `Config` 필드, `run` 반환 키가 task 간 일치. ✅
- **주의:** Task 7 `test_pipeline`는 `from conftest import`가 아니라 픽스처/직접생성을 쓰므로 import 경로 문제 없음. `from conftest import make_grid_da`(Task 4 테스트)는 pytest rootdir에 tests가 있어 동작하나, 실패 시 `from tests.conftest import` 또는 conftest를 `tests/`에 두고 `tests`를 패키지로 인식시킬 것.
