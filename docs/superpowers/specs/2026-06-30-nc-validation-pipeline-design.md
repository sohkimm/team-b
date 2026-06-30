# NC 검증 파이프라인 — 설계 문서

> 작성일: 2026-06-30 · 팀B (teamB) · 작성자: 김소희(ksh)
> 상태: 승인됨 (브레인스토밍 완료) → 구현 계획 작성 단계로 진행

## 1. 목적 & 범위

두 개의 NetCDF 해양 표층염분(SSS) 자료를 **동일한 절차**로 비교·검증하는 파이프라인을 만든다.
모든 자료를 **WGS84 정규격자**로 표준화한 뒤, **저해상도를 기준**으로 리샘플하여 통계 검증한다.

**대상 파일 (해커톤 범위):**

| 파일 | 설명 |
|---|---|
| `dataset-sss-ssd-nrt-daily_20260101T1200Z_P20260122T0000Z.nc` | CMEMS SSS/SSD NRT 일별 격자 (25 MB, NetCDF4/HDF5) |
| `SMAP_L3_SSS_20260101_8DAYS_V5.0.nc` | SMAP L3 SSS 8일 합성 (11 MB, NetCDF4/HDF5) |

**범위 제한:** 두 파일 모두 **정규격자(rectilinear)**만 다룬다. 비정규격자(곡선격자·스와스·모델 ESMF)는 **해커톤 범위 외** — 진입 시 경고 후 중단.

**분석 영역(AOI):** 양자강 하구·동중국해·남해안·서해안 일대
```
lat : 24°N ~ 38°N
lon : 117°E ~ 131°E
```

## 2. 확정 결정 사항

브레인스토밍에서 확정한 핵심 결정:

| 항목 | 결정 | 근거 |
|---|---|---|
| **리샘플 라이브러리** | rioxarray `reproject_match` + `Resampling.average` (근사 conservative) | 3단계 후 두 격자가 WGS84 축정렬이므로 average가 충분히 타당. xesmf(엄밀 conservative)는 esmpy 의존성 리스크로 제외 |
| **비교 변수 선택** | SSS **자동 탐지** (`standard_name='sea_surface_salinity'` 또는 이름 키워드) | 범용성. 실패 시 후보 출력 + `--var-a/--var-b` 안내 |
| **시간 차원** | 각 파일의 **첫(유일) 타임스텝** | 두 파일 모두 사실상 단일 시점 |
| **실행 환경** | 이 맥에 **micromamba** 설치 → `ncval` 환경 생성 | conda 미설치, 관리자 권한 불필요·스크립트화 용이 |
| **격자 판별** | [2]에서 `is_regular_grid` 보고, [3]에서 분기 | 결정 위치를 한 곳에 집중 |
| **비정규격자** | 해커톤 범위 외 — 명시적 중단 | 조용한 처리 금지 |
| **해상도 기준** | 두 입력 중 **저해상도(coarser)** | |
| **검증 방향** | 고→저(권장) + 저→고(비교) 두 방향 모두 수행 후 비교 테이블 | 저해상도 기준의 타당성을 수치로 확인 |

## 3. 아키텍처 — 얇은 오케스트레이터 + 순수 함수 모듈

각 모듈은 독립 테스트 가능하고, `xarray` 객체를 입출력으로 받으며, 한 가지 일만 한다.
`pipeline.py`가 연결하고, 모듈끼리는 전달받은 데이터 외에 서로 import하지 않는다.

```
run_validation.py        # CLI: 경로, --var-a/--var-b 오버라이드, --outdir; pipeline.run() 호출
src/
├── io_nc.py        [1]  open_nc(path) → xr.Dataset  (NetCDF 아니면 거부, decode_cf=True)
├── inspect_nc.py   [2-1] describe(ds) → InspectReport (유형/격자/해상도/투영) — 보고만
├── qc.py           [2-2] apply_qc(da, ds) → da  (_FillValue/valid_range/flag 비트 → NaN)
├── reproject.py    [3]  to_wgs84(da) → da (WGS84 표준화: 경도 정규화·정렬, 필요시 재투영)
├── resample.py     [4]  build_target_grid / match_resolution(...) via reproject_match
├── metrics.py      [5]  stats(eval, ref) → dict{N,Bias,RMSE,MAE,R,R2}
├── visualize.py         map_field / scatter → PNG (matplotlib + cartopy)
└── pipeline.py          run(path_a, path_b, cfg) → results  ([1]→[5] 오케스트레이션)
```

**핵심 경계 결정:** `inspect_nc`는 **보고만** 하고 절대 분기하지 않는다. 정규/투영/비정규 분기는 `reproject`(및 pipeline)가 단독으로 소유한다. 격자 유형 결정이 정확히 한 곳에만 존재.

## 4. 데이터 흐름

```
A.nc ─[1]open─[2-1]describe─[2-2]QC─┐
                                     ├─▶ [3] 경도 정규화·정렬, (투영이면) WGS84 재투영
B.nc ─[1]open─[2-1]describe─[2-2]QC─┘         → 두 자료 모두 "WGS84 원본 해상도" 상태
                                                  📊 step3_wgs84_A/B.png
                                     │
        해상도 비교: dlat·dlon로 저해상도(coarser) 판정  (재투영 직후, AOI 자르기 전)
                                     │
        목표 격자 1개 생성 = AOI(24~38°N,117~131°E) ∩ 저해상도 간격
                                     │
                  ┌──────────────────┴──────────────────┐
            [4] 고→저 (권장)                       [4'] 저→고 (비교)
            목표=AOI+저해상도 간격                 목표=AOI+고해상도 간격
            고→저: reproject_match(average)        저→고: reproject_match(bilinear)
            📊 step4_resampled_A/B.png
                  │                                      │
            [5] stats(고_on_저, 저)              [5] stats(저_on_고, 고)
                  └──────────────┬───────────────────────┘
                          비교 테이블 + step5_hilo/lohi/compare.png
                                 ▼
                  results/tables/*.csv, results/figures/*.png
```

**이중 리샘플 방지 (핵심):**

1. **목표 격자는 단 한 번 생성** — AOI 경계 + 저해상도 격자 간격으로 정의된 rectilinear 격자(lat 오름차순, lon −180~180). 3단계는 "WGS84화"까지만, AOI 정합은 4단계 `reproject_match`가 목표 격자를 받아 한 번에 처리. 보간은 자료당 **1회**.
2. **저해상도 판정은 WGS84화 직후·AOI 자르기 전** dlat·dlon으로 한다 (재투영 후 간격이 바뀔 수 있어 순서가 중요). 두 자료 해상도가 같으면 A를 기준.
3. **`reproject_match`가 reproject + AOI 격자 정합 + 해상도 정합을 한 함수로 처리** — 이게 이중 보간을 막는 메커니즘.

## 5. 단계별 명세

### [1] 입력 검증 — `io_nc.py`
- 파일 magic(`CDF`=NetCDF3, `HDF`=NetCDF4) 확인 후 `xarray.open_dataset(decode_cf=True)`로 개방.
- NetCDF 아니거나 개방 실패 → 명확한 에러로 중단.

### [2-1] NC 파악 (보고 전용) — `inspect_nc.py`

| 항목 | 판별 방법 |
|---|---|
| 자료 유형 | 전역 속성 `processing_level`, `cdm_data_type`, `source`/`institution` 키워드 → 위성 L3 격자 / L2 스와스 / 모델 / 합성장 분류 |
| 정규/비정규 | `is_regular_grid(lat, lon)` |
| 공간해상도 | `dlat=lat[1]-lat[0]`, `dlon=lon[1]-lon[0]` (도) |
| 시간해상도 | `time` 차원 또는 `time_coverage_duration`/`temporal_resolution` |
| 투영 정보 | `grid_mapping` 변수의 `grid_mapping_name`; 없거나 `latitude_longitude`면 WGS84 |

```python
def is_regular_grid(lat, lon, rtol=1e-4):
    if lat.ndim != 1 or lon.ndim != 1:
        return False                       # 2D 좌표 = 곡선격자(비정규)
    dlat, dlon = np.diff(lat), np.diff(lon)
    return (np.allclose(dlat, dlat[0], rtol=rtol) and
            np.allclose(dlon, dlon[0], rtol=rtol))
```

### [2-2] QC — 속성 기반 — `qc.py`

| 검사 | 사용 속성 | 처리 |
|---|---|---|
| 결측 | `_FillValue`, `missing_value` | 해당 값 → NaN |
| 유효범위 | `valid_min`/`valid_max`, `valid_range` | 범위 밖 → NaN |
| QC flag | `flag_values`/`flag_masks` + `flag_meanings` 동반 변수 | good 비트만 통과 (비트마스크 해석) |

- `scale_factor`/`add_offset`은 xarray가 디코딩(decode_cf).
- 동반 QC 변수가 없으면 flag 검사는 건너뜀(자동 탐지).

### [3] WGS84 표준화 — `reproject.py`
- **분기:** `is_regular_grid==False` → 비정규격자 → **해커톤 범위 외, 중단**.
- 정규격자(지리, WGS84): 경도 −180~180 정규화·정렬, lat 오름차순 정렬.
- 정규격자(투영): `grid_mapping`/CRS 탐지 후 WGS84 재투영. CRS 탐지 실패 시 중단(오재투영 방지).
- 시각화: `results/figures/step3_wgs84_A.png`, `step3_wgs84_B.png`.

### [4] 해상도 정합 — `resample.py`
- 저해상도 판정 → AOI + 저해상도 간격으로 **목표 격자** 생성.
- 고→저: `reproject_match`(`Resampling.average`)로 고해상도를 목표 격자에 정합.
- 저↔고 비교를 위해 저→고(`Resampling.bilinear`) 목표 격자도 별도 생성.
- 시각화: `results/figures/step4_resampled_A.png`, `step4_resampled_B.png`.

### [5] 검증 — `metrics.py`
- 두 격자에서 **둘 다 유효한 셀**만 1:1 매칭.
- 통계량 6개: `N`, `Bias`, `RMSE`, `MAE`, `R`, `R²` (편차 = 평가 − 기준).
- 고→저 / 저→고 각각 산출 → **비교 테이블** 1장.
- 시각화: `results/figures/step5_hilo.png`, `step5_lohi.png`, `step5_compare.png`.
- 결과 CSV: `results/tables/`.

## 6. 에러 처리 & 범위 가드

| 단계 | 가드 조건 | 동작 |
|---|---|---|
| [1] | NetCDF 아님 / open 실패 | `nc 파일만 지원` 즉시 중단 |
| [2-1] | 좌표 후보(lat/lon, latitude/longitude, x/y) 미발견 | 못 찾은 좌표 명시 후 중단 |
| [2-2] | SSS 자동탐지 실패 | 후보 변수 목록 + `--var-a/--var-b 지정` 안내 |
| [3] | `is_regular_grid==False` | 해커톤 범위 외 — 경고 후 중단 |
| [3] | 투영 자료인데 CRS 탐지 실패 | CRS 불명 — 중단 |
| [4] | AOI ∩ 자료 = 빈 영역 | `분석 영역에 유효 데이터 없음` 중단 |
| [5] | 공통 유효 셀 N < 임계값(10) | 통계는 내되 **신뢰 불가 경고** 표기 |

**원칙:**
1. 범위 외(비정규격자)는 **명시적 중단** — 조용히 처리 안 함.
2. NaN은 전 단계 **전파** — 0/FillValue로 채우지 않음. 5단계 "둘 다 유효한 셀만" 마스킹으로 자연 제거.
3. **부분 산출물 보존** — 후속 단계 실패해도 이전 figure/로그는 디스크에 남김.

## 7. 테스트 & 검증 전략

순수 함수 모듈이라 작은 **합성 NC 픽스처**로 단위 테스트. 실파일(25/11MB)은 통합 스모크 1개에서만.

| 모듈 | 테스트 |
|---|---|
| `qc` | FillValue/valid_range/flag 합성 DataArray → NaN 위치 검증 |
| `inspect_nc` | 정규/투영/2D좌표 합성 ds → 보고 필드 정확성 |
| `reproject` | 0~360→−180~180 정규화, lat 내림차순→오름차순 |
| `resample` | 알려진 2×2 블록 → average 평균값, reproject_match 격자 일치 |
| `metrics` | 손계산 벡터(ref=[1,2,3], eval=[1.1,2.1,2.9]) → 수치 일치 |
| 통합 | 실제 2개 nc → 전체 무중단 완주 + CSV/PNG 생성 확인 |

**완료 검증(필수):** "완료" 주장 전 (a) `pytest` 통과 출력, (b) `run_validation.py` 실행 → `results/tables/*.csv` + `results/figures/*.png` 존재 확인. 증거 없이 완료 선언 금지.

## 8. 빌드 순서 (위상 정렬)

```
0. micromamba 설치 + ncval 환경 생성 + 실파일 introspection
   └ 실제 좌표명·QC속성·해상도·투영 확인 (설계 가정 검증) ★결정적
1. io_nc + inspect_nc        ← 실파일 열고 구조 보고 (현실 확인 먼저)
2. metrics                   ← 의존성 0, 손계산 검증 (빠른 성공)
3. qc                        ← 속성 기반 마스킹
4. reproject (WGS84 표준화)  ← 핵심·난이도 상
5. resample (해상도 정합)    ← reproject 위에 빌드
6. visualize                ← 중간 산출물 PNG
7. pipeline + run_validation ← 전체 연결
8. 통합 스모크 + 결과 검토
```

**0단계가 결정적:** 환경이 없고 실파일을 아직 못 열어봤으므로, 첫 실행 단계에서 실제 좌표명/속성을 확인해 설계 가정(SMAP가 정말 정규격자인지, CMEMS에 투영이 있는지)을 검증한다. 가정이 틀리면 그 지점에서 설계 보정.

## 9. 환경 & 라이브러리

conda 환경 **`ncval`** (Python 3.10) — `environment.yml` 참조. 이 맥에는 micromamba로 생성.

| 용도 | 라이브러리 | 사용 |
|---|---|---|
| 입출력·연산 | xarray, netCDF4, numpy, scipy, pandas | ✅ |
| 재투영·리샘플 | rioxarray, rasterio, pyproj | ✅ |
| 시각화·지리정보 | matplotlib, cartopy | ✅ |
| 스와스 바인딩 | pyresample | ❌ 범위 외 |
| 모델 ESMF | xesmf, esmpy | ❌ 범위 외 |

## 10. 표준 규약 (요약)

| 항목 | 표준 |
|---|---|
| 좌표계 | WGS84 (EPSG:4326), lat/lon 도 단위 |
| 격자 | rectilinear, lat 오름차순, lon −180~180 |
| 분석 영역 | lat 24~38°N, lon 117~131°E (목표 격자로 반영) |
| 격자 판별 | lat/lon 간격 일정성 (`is_regular_grid`) |
| 기준 해상도 | 두 입력 중 저해상도 |
| 입력 | nc 전용 |
| 비정규격자 | 해커톤 범위 외 |
