# 범용 검증 파이프라인 설계 (PIPELINE)

> 어떤 nc 자료가 와도 **동일한 절차**로 검증한다.
> 모든 자료를 **WGS84 정규격자**로 표준화한 뒤, **저해상도를 기준**으로 리샘플 → 검증.

## 0. 설계 원칙
- **해커톤 프로젝트 목표**: 현재 보유한 2개의 NC 파일(`dataset-sss-ssd-nrt-daily_20260101T1200Z_P20260122T0000Z.nc`, `SMAP_L3_SSS_20260101_8DAYS_V5.0.nc`) 검증.
- **해커톤 범위 제한**: 두 파일 모두 **정규격자(rectilinear)**만 다룬다. 비정규격자(곡선격자·스와스·모델 ESMF) 처리는 해커톤 범위 외.
- **분석 영역**: 양자강 하구·동중국해·남해안·서해안 일대
  ```
  lat : 24°N ~ 38°N
  lon : 117°E ~ 131°E
  ```
  (서해/황해 전체 + 동중국해 + 양자강 하구 + 한반도 남·서해안 포함)
- 입력은 **무조건 NetCDF(.nc) 파일만**. 그 외 형식은 즉시 거부.
- 자료 종류(위성 L3 격자 / 위성 L2 스와스 / 모델)를 자동 판별하고, 종류에 맞는
  방법으로 **공통 좌표계(WGS84, EPSG:4326) 정규격자**로 변환한다.
- **검증 직전에는 두 자료가 무조건 WGS84**여야 한다.
- 두 자료의 공간해상도는 **저해상도(coarser)**에 맞춘다.
- **분석 영역 적용**: crop 대신 분석 영역(위 lat/lon)을 **목표 격자로 삼아 [3] 리샘플** 시 반영한다.

## 전체 흐름

```
  nc 입력 ──▶ [1] 입력 검증 (nc 전용)
            ──▶ [2] NC 파악 + QC
                     NC 파악: 자료 유형·격자·해상도·투영 보고 (분기는 [3]에서)
                     QC: FillValue·valid_range·QC flag → 참값 마스킹
            ──▶ [3] WGS84 표준화 + 분석 영역 리샘플
                     ├─ 정규격자(WGS84) : 경도 정규화·정렬 → 분석 영역 목표 격자로 리샘플
                     └─ 정규격자(투영)  : WGS84 재투영 → 분석 영역 목표 격자로 리샘플
                     └─ (해커톤 범위 외) 비정규격자: 스와스 바인딩 / 모델 ESMF
                     📊 시각화: step3_wgs84_A.png, step3_wgs84_B.png
            ──▶ [4] 해상도 정합 (저해상도 기준 리샘플)
                     📊 시각화: step4_resampled_A.png, step4_resampled_B.png
            ──▶ [5] 검증
                     ├─ 고→저 (권장): 통계량 6개
                     └─ 저→고 (비교): 통계량 6개
                     → 비교 테이블 + 저해상도 기준 타당성 확인
                     📊 시각화: step5_hilo.png, step5_lohi.png, step5_compare.png
            ──▶ 결과: results/tables(CSV), results/figures(PNG)
```

---

## [1] 입력 검증
- NetCDF(NetCDF3·4)인지 확인 후 `xarray.open_dataset`으로 개방.
- nc가 아니면 명확한 에러로 중단.

## [2] NC 파악 + QC

### 2-1. NC 파악 (보고 전용 — 분기 처리는 [3]에서)
NC를 열면 아래 항목을 자동으로 파악하고 결과를 출력·기록한다. 여기서는 **보고만** 하고, 실제 분기 처리는 [3]에서 수행한다.

| 항목 | 판별 방법 |
|---|---|
| **자료 유형** | 전역 속성 `processing_level`(`L2`/`L3`/`L4`), `cdm_data_type`(`Grid`/`Swath`/`Point`), `source`/`institution` 키워드 → **위성 L3 격자 / 위성 L2 스와스 / 모델 / 합성장** 중 하나로 분류 |
| **정규/비정규격자** | `is_regular_grid(lat, lon)` — lat·lon 1D이고 간격 일정하면 정규, 그 외 비정규 |
| **공간해상도** | `dlat = lat[1]-lat[0]`, `dlon = lon[1]-lon[0]` (도 단위로 표기) |
| **시간해상도** | `time` 차원 값 또는 전역 속성 `time_coverage_duration`/`temporal_resolution` |
| **투영 정보** | `grid_mapping` 변수의 `grid_mapping_name` 확인 → 없거나 `latitude_longitude`면 WGS84(지리좌표), 그 외(`polar_stereographic` 등)면 투영명·EPSG 기록 |

판별 결과 예시:
```
자료 유형  : 위성 L3 격자 (합성장)
격자 유형  : 정규격자 (rectilinear)
공간해상도 : 0.25° × 0.25°
시간해상도 : 8일 합성
투영 정보  : WGS84 (지리좌표, grid_mapping 없음)
```

### 2-2. QC — 속성 기반
변수 **어트리뷰트**만 보고 참값을 가린다.

| 검사 | 사용하는 속성 | 처리 |
|---|---|---|
| 결측 | `_FillValue`, `missing_value` | 해당 값 → NaN |
| 유효범위(참값) | `valid_min`/`valid_max`, `valid_range` | 범위 밖 → 제거 |
| QC flag | `flag_values`/`flag_masks` + `flag_meanings` 동반 변수 | good 비트만 통과 |

- `scale_factor`/`add_offset`은 xarray가 디코딩.
- QC flag는 **비트마스크 해석**까지 지원(`flag_masks` & `flag_values`로 good 판정).

## [3] WGS84 표준화 + 분석 영역 리샘플  ⭐

### 3-1. 격자 판별 — lat/lon 간격 일정성 검사 (분기 처리)
[2]의 NC 파악 결과를 바탕으로 실제 분기를 결정한다.

```python
def is_regular_grid(lat, lon, rtol=1e-4):
    """lat/lon 간격이 일정하면 정규격자(True)."""
    if lat.ndim != 1 or lon.ndim != 1:
        return False                       # 2D 좌표 = 곡선격자(비정규)
    dlat, dlon = np.diff(lat), np.diff(lon)
    return (np.allclose(dlat, dlat[0], rtol=rtol) and
            np.allclose(dlon, dlon[0], rtol=rtol))
```

- 1D lat/lon이고 간격이 **일정** → **정규격자** → 아래 3-2 처리
- 그 외 → **비정규격자** → 해커톤 범위 외, 중단 또는 경고

### 3-2. 정규격자 표준화 → WGS84 + 분석 영역 목표 격자로 리샘플

| 자료 유형 | 좌표 | 방법 | 라이브러리 |
|---|---|---|---|
| 정규격자(지리, WGS84) | 1D lat/lon(도) | 경도 −180~180 정규화·정렬 → 분석 영역 목표 격자로 리샘플 | xarray / rioxarray |
| 정규격자(투영) | 1D x/y + `grid_mapping` | WGS84로 재투영 → 분석 영역 목표 격자로 리샘플 | GDAL / rioxarray / rasterio |
| ~~곡선격자(모델)~~ | — | *(해커톤 범위 외)* | — |
| ~~비구조/스와스(L2)~~ | — | *(해커톤 범위 외)* | — |

- **CRS 탐지**: `grid_mapping` 변수의 `grid_mapping_name`(예: `latitude_longitude`, `polar_stereographic`), 또는 `crs`/`spatial_ref`/proj4 속성. 없고 lat/lon이 도 단위면 WGS84 지리좌표로 간주.
- **목표 격자**: rectilinear, lat 오름차순, lon −180~180, 분석 영역(lat 24~38°N, lon 117~131°E) 적용.
- **시각화 (matplotlib)**: 표준화 완료 직후 두 자료 각각 지도 이미지 저장 (`results/figures/step3_wgs84_A.png`, `step3_wgs84_B.png`).

## [4] 해상도 정합 (리샘플)
WGS84 표준화가 끝난 두 격자를 **저해상도 기준**으로 리샘플해 공간해상도를 맞춘다.

- **기준 = 저해상도(coarser)**. 고해상도를 저해상도 격자로 **면적집계(conservative)**.
- 저해상도 격자가 곧 [5] 검증의 기준 격자가 된다.
- 리샘플 라이브러리: **rioxarray / rasterio** (`reproject_match`).
- 전제: **이 단계 진입 시 두 자료 모두 WGS84**.
- **시각화 (matplotlib)**: 리샘플 완료 직후 두 자료를 동일 격자에서 나란히 이미지 저장 (`results/figures/step4_resampled_A.png`, `step4_resampled_B.png`).

## [5] 검증
두 격자에서 **둘 다 유효한 셀**만 1:1 매칭하여 통계량을 계산한다.
통계량(6개): `N`, `Bias`, `RMSE`, `MAE`, `R`, `R²` (편차 = 평가 − 기준).

### 5-1. 두 방향 리샘플 비교 (저↔고 기준)
**저해상도 기준이 올바른 선택임을 수치로 검증하기 위해 두 방향을 모두 수행하고 결과를 비교한다.**

| 방법 | 설명 | 기준 격자 |
|---|---|---|
| **고→저 (권장)** | 고해상도를 저해상도 격자로 면적집계(conservative) | 저해상도 |
| **저→고 (비교)** | 저해상도를 고해상도 격자로 보간(bilinear) | 고해상도 |

- 두 방법 각각 통계량 6개 산출 → **비교 테이블** 1장으로 정리.
- 예상 결과: 고→저 방향이 Bias·RMSE 안정적, 저→고 방향은 보간 아티팩트로 통계 왜곡 → **저해상도 기준의 타당성 확인**.
- **시각화 (matplotlib)**: 두 방향 결과를 나란히 산점도·지도로 출력 (`results/figures/step5_hilo.png`, `step5_lohi.png`, `step5_compare.png`).

---

## 표준 규약 (요약)
| 항목 | 표준 |
|---|---|
| 좌표계 | **WGS84 (EPSG:4326)**, lat/lon 도 단위 |
| 격자 | rectilinear, lat 오름차순, lon −180~180 |
| 분석 영역 | lat 24~38°N, lon 117~131°E (목표 격자로 리샘플 시 반영) |
| 격자 판별 | **lat/lon 간격 일정성** (`is_regular_grid`) — [2]에서 보고, [3]에서 분기 |
| 기준 해상도 | 두 입력 중 **저해상도** |
| 입력 | **nc 전용** |
| 비정규격자 | **해커톤 범위 외** |

## 환경 & 라이브러리
conda 환경 **`ncval`** (Python 3.10) — `environment.yml` 참조.

| 용도 | 라이브러리 | 해커톤 사용 여부 |
|---|---|---|
| 입출력·연산 | xarray, netCDF4, numpy, scipy, pandas | ✅ |
| 재투영·리샘플 | rioxarray, rasterio, pyproj | ✅ |
| 시각화·지리정보 | matplotlib, cartopy | ✅ |
| 스와스 바인딩 | pyresample | ❌ 범위 외 |
| 모델 ESMF 보간 | xesmf, esmpy | ❌ 범위 외 |

```bash
conda env create -f environment.yml   # 환경 ncval 생성
conda activate ncval
```

## 제안 모듈 구조
```
src/
├── io_nc.py       # nc 전용 입력, 변수·좌표·속성 파싱
├── inspect_nc.py  # NC 파악: 자료 유형·격자·해상도·투영 보고 ([2]-1)
├── qc.py          # QC: FillValue + valid_range + flag 비트 → 참값 ([2]-2)
├── reproject.py   # WGS84 표준화 + 분석 영역 리샘플 ([3])
├── resample.py    # 저해상도 기준 해상도 정합 ([4])
├── metrics.py     # 통계량 (N, Bias, RMSE, MAE, R, R²)
├── visualize.py   # matplotlib 단계별 지도·산점도 출력
└── pipeline.py    # 단계 오케스트레이션 [1]→[2]→[3]→[4]→[5]
run_validation.py  # CLI 진입점
```

## 테스트 데이터
| 파일 | 설명 |
|---|---|
| `dataset-sss-ssd-nrt-daily_20260101T1200Z_P20260122T0000Z.nc` | SSS/SSD NRT 일별 격자 |
| `SMAP_L3_SSS_20260101_8DAYS_V5.0.nc` | SMAP L3 SSS 8일 합성 |

---

## 결정 사항 (확정)
- **격자 판별**: [2]에서 `is_regular_grid`로 보고, [3]에서 분기 처리.
- **비정규격자**: 해커톤 범위 외 — 진입 시 경고 후 중단.
- **분석 영역**: lat 24~38°N / lon 117~131°E — crop 대신 [3] 리샘플의 목표 격자로 적용.
- **해상도 기준**: 두 입력 중 저해상도.
- **검증 방향**: 고→저(권장) + 저→고(비교) 두 방향 모두 수행 후 비교 테이블 출력.
- **환경**: conda `ncval`, 재투영/리샘플은 rioxarray·rasterio.
