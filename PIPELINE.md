# 범용 검증 파이프라인 설계 (PIPELINE)

> 어떤 nc 자료가 와도 **동일한 절차**로 검증한다.
> 모든 자료를 **WGS84 정규격자**로 표준화한 뒤, **저해상도를 기준**으로 리샘플 → 검증.

## 0. 설계 원칙
- 입력은 **무조건 NetCDF(.nc) 파일만**. 그 외 형식은 즉시 거부.
- 자료 종류(위성 L3 격자 / 위성 L2 스와스 / 모델)를 자동 판별하고, 종류에 맞는
  방법으로 **공통 좌표계(WGS84, EPSG:4326) 정규격자**로 변환한다.
- **검증 직전에는 두 자료가 무조건 WGS84**여야 한다.
- 두 자료의 공간해상도는 **저해상도(coarser)**에 맞춘다. (crop은 두지 않음 — 아래 [4] 참조)

## 전체 흐름

```
  nc 입력 ──▶ [0] 입력 검증 (nc 전용)
            ──▶ [1] QC (속성 기반: 참값 flag + FillValue)
            ──▶ [2] 격자 판별 & WGS84 표준화  ◀── 파이프라인의 핵심
                     ├─ 정규격자  : CRS 확인 → (투영이면) WGS84 재투영
                     └─ 비정규격자: L2 스와스 → 바인딩(binning)
                                    모델      → ESMF 보간(conservative)
            ──▶ [3] 해상도 정합 (저해상도 기준 리샘플; crop 없음)
            ──▶ [4] 검증 (매칭 → 통계량 → 지리정보 지도)
            ──▶ 결과: results/tables(CSV), results/figures(PNG, 지리정보 포함)
```

---

## 1. 입력 검증
- NetCDF(NetCDF3·4)인지 확인 후 `xarray.open_dataset`으로 개방.
- nc가 아니면 명확한 에러로 중단.

## 2. QC — 속성 기반, 기본만
변수 **어트리뷰트**만 보고 참값을 가린다. (육지·해빙 등 변수별 부가 마스킹은
코어에서 제외하고 옵션으로만 둔다.)

| 검사 | 사용하는 속성 | 처리 |
|---|---|---|
| 결측 | `_FillValue`, `missing_value` | 해당 값 → NaN |
| 유효범위(참값) | `valid_min`/`valid_max`, `valid_range` | 범위 밖 → 제거 |
| QC flag | `flag_values`/`flag_masks` + `flag_meanings` 동반 변수 | good 비트만 통과 |

- `scale_factor`/`add_offset`은 xarray가 디코딩.
- QC flag는 **비트마스크 해석**까지 지원(`flag_masks` & `flag_values`로 good 판정).

## 3. 격자 판별 & WGS84 표준화  ⭐

### 3-1. 판별 — lat/lon 간격 일정성 검사
**핵심 판별자는 "lat/lon 간격이 일정한가?"** 이다. 전용 함수로 검사한다.

```python
def is_regular_grid(lat, lon, rtol=1e-4):
    """lat/lon 간격이 일정하면 정규격자(True)."""
    if lat.ndim != 1 or lon.ndim != 1:
        return False                       # 2D 좌표 = 곡선격자(비정규)
    dlat, dlon = np.diff(lat), np.diff(lon)
    return (np.allclose(dlat, dlat[0], rtol=rtol) and
            np.allclose(dlon, dlon[0], rtol=rtol))
```

- 1D lat/lon 이고 간격이 **일정** → **정규격자(rectilinear)**
- 간격이 **불규칙**하거나 lat/lon 이 **2D**(곡선격자) 또는 **점군/단일 관측차원**(스와스)
  → **비정규격자**
- 비정규 안에서 스와스 vs 모델: **2D 좌표(곡선격자)면 모델→ESMF**, **점군/관측차원이면
  위성 L2 스와스→바인딩**. 모호하면 전역 속성(`cdm_data_type`, `processing_level`) 또는
  `--grid-type {regular|model|swath}` 수동 지정.

### 3-2. 종류별 표준화 → 모두 WGS84 정규격자

| 자료 유형 | 좌표 | 방법 | 라이브러리 |
|---|---|---|---|
| 정규격자(지리, WGS84) | 1D lat/lon(도) | 경도 −180~180 정규화·정렬만 | xarray |
| 정규격자(투영) | 1D x/y + `grid_mapping` | **WGS84로 재투영** | **GDAL / rioxarray / rasterio** |
| 곡선격자(모델) | 2D lat/lon | **ESMF 보간(conservative)** — 면적·평균 보존(가장 변화 적음) | xesmf(+esmpy) |
| 비구조/스와스(L2) | 점군 lat/lon | **바인딩**(목표 셀 평균/카운트) | pyresample(bucket) |

- **CRS 탐지**: `grid_mapping` 변수의 `grid_mapping_name`(예: `latitude_longitude`,
  `polar_stereographic`), 또는 `crs`/`spatial_ref`/proj4 속성. 없고 lat/lon이 도 단위면
  WGS84 지리좌표로 간주.
- **ESMF는 conservative** 고정(면적가중 평균으로 원본 적분량 보존 → 변화 최소).
- **목표 격자**: rectilinear, lat 오름차순, lon −180~180.

## 4. 해상도 정합 (리샘플)
표준화(WGS84)가 끝난 두 격자를 **리샘플**로 공간해상도를 맞춘다.
**crop은 두지 않는다** — 어차피 해상도가 바뀌므로, 원하는 영역이 있으면 **그 영역의
격자로 리샘플**하면 된다.

- **기준 = 저해상도(coarser)**. 고해상도를 저해상도 격자로 **면적집계**(conservative).
- 저해상도 격자(또는 사용자가 지정한 목표 영역·격자)가 곧 검증 격자가 된다.
- 리샘플/재투영 라이브러리: **GDAL / rioxarray / rasterio**(`reproject` / `reproject_match`).
- 전제: **검증 직전에는 두 자료가 무조건 WGS84**.

## 5. 검증
- 두 격자에서 **둘 다 유효한 셀**만 1:1 매칭.
- 통계량(현재 6개, 확장 가능): `N`, `Bias`, `RMSE`, `MAE`, `R`, `R²` (편차 = 평가 − 기준).
- 결과: 통계 CSV + 산점도 + 지도(해안선·°E/°N 위경도축 등 **지리정보 포함**).

---

## 표준 규약 (요약)
| 항목 | 표준 |
|---|---|
| 좌표계 | **WGS84 (EPSG:4326)**, lat/lon 도 단위 |
| 격자 | rectilinear, lat 오름차순, lon −180~180 |
| 격자 판별 | **lat/lon 간격 일정성**(`is_regular_grid`) |
| 모델 보간 | **ESMF conservative** |
| 기준 해상도 | 두 입력 중 **저해상도** |
| 입력 | **nc 전용** |
| crop | 없음(원하는 영역은 그 격자로 리샘플) |

## 환경 & 라이브러리
conda 환경 **`ncval`** (Python 3.10) — 생성 완료. `environment.yml` 참조.

| 용도 | 라이브러리 |
|---|---|
| 입출력·연산 | xarray, netCDF4, numpy, scipy, pandas, dask |
| 재투영·리샘플 | **GDAL, rioxarray, rasterio**, pyproj |
| 스와스 바인딩 | pyresample |
| 모델 ESMF 보간 | xesmf, esmpy |
| 시각화·지리정보 | matplotlib, cartopy |

```bash
conda env create -f environment.yml   # 환경 ncval 생성
conda activate ncval
```

## 현재 코드 대비 (gap 분석)
현재 [run_validation.py](../run_validation.py)는 **정규격자 + 같은 지리좌표** 가정의 SSS 검증.

| 단계 | 현재 | 일반화 필요 |
|---|---|---|
| 입력 nc 전용 | ✅ | — |
| QC: valid_range/FillValue | ✅ | — |
| QC: flag 비트마스크 해석 | ❌ | 추가 |
| QC: 육지·해빙 | SSS 특화로 내장 | **옵션화**(코어에서 분리) |
| 격자 판별(간격 일정성) | ❌ | `is_regular_grid` 추가 |
| CRS 탐지 → WGS84 재투영 | ❌ | GDAL/rioxarray/rasterio |
| 곡선격자 ESMF(conservative) | ❌ | xesmf 추가 |
| 스와스 바인딩 | △(block-mean만) | pyresample bucket로 일반화 |
| 저해상도 기준 리샘플 | ✅(block-mean) | conservative로 일반화 |
| 통계량 6 + 지리정보 지도 | ✅ | 확장 가능 |

## 제안 모듈 구조 (일반화 후)
```
src/
├── io_nc.py       # nc 전용 입력, 변수·좌표·속성 파싱
├── qc.py          # 속성 기반 QC: FillValue + valid_range + flag 비트 → 참값
├── grid.py        # is_regular_grid 판별 + CRS 탐지 + 유형 분류
├── reproject.py   # WGS84 표준화: 재투영(GDAL/rio) / ESMF(conservative) / 바인딩
├── resample.py    # 저해상도 기준 리샘플(목표 격자로 정합)
├── metrics.py     # 통계량
└── pipeline.py    # 단계 오케스트레이션
run_validation.py  # CLI 진입점
```

## 테스트 데이터 (현재 작업 파일)
| 파일 | 설명 |
|---|---|
| `dataset-sss-ssd-nrt-daily_20260101T1200Z_P20260122T0000Z.nc` | SSS/SSD NRT 일별 격자 |
| `SMAP_L3_SSS_20260101_8DAYS_V5.0.nc` | SMAP L3 SSS 8일 합성 |

---

## 결정 사항 (확정)
- **격자 판별**: `is_regular_grid`(lat/lon 간격 일정성)로 정규/비정규 구분.
- **ESMF 보간**: **conservative**(면적·평균 보존 — 가장 변화 적음).
- **crop 없음**: 영역이 필요하면 그 영역 격자로 리샘플. **검증 전 무조건 WGS84**.
- **환경**: 신규 conda 환경 `ncval`, 재투영/리샘플은 **GDAL·rioxarray·rasterio**.
- (남은 판단) 스와스 vs 모델 모호 시: 좌표 차원/전역속성 자동 + `--grid-type` 수동 override.
