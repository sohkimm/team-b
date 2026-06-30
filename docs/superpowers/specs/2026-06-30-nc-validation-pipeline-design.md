# NC 검증 파이프라인 — 설계 문서 (v2)

> 작성일: 2026-06-30 · 팀B (teamB) · 작성자: 김소희(ksh)
> 상태: 승인됨 → 적대적 멀티에이전트 리뷰 1회 반영(v2) → 구현 계획 단계
>
> **v2 변경 요약 (4개 비평 에이전트 + 실파일 재검증으로 수용):**
> 보간 불변식 정정([3]=무보간, [4] 1회), nodata 명시, rio accessor 전처리,
> build_target_grid 계약·경계 스냅, average 라벨 정정, R²=NSE 정의,
> 변수 standard_name 엄격일치, 시간 대표성/처리수준 한정(Caveats §11),
> environment.yml 경량화, MVP 수직슬라이스 우선 빌드순서, 저→고 진단용 강등,
> PROCESS_LOG 로깅 명문화.

## 0. 실파일 재검증으로 확정된 사실 (설계 가정 검증 완료)

NetCDF4/HDF5 메타데이터 직접 추출로 두 파일의 실제 구조를 확인했다. **0단계 introspection의 일부를 선수행한 결과:**

| 항목 | CMEMS (`dataset-sss-ssd...`) | SMAP (`SMAP_L3_SSS_..._8DAYS`) |
|---|---|---|
| 좌표명 | `latitude`, `longitude` (1D, degrees_north/east) | `latitude`, `longitude` (1D, degrees_north/east) |
| 격자/투영 | 지리 WGS84, **투영 없음** | 지리 WGS84 0.25°, **투영 없음** (Gaussian-weighted map gridding) |
| 변수 | `sea_surface_salinity`(+error), **`sea_surface_density`(+error)** | `sea_surface_salinity`(+uncertainty), `sea_surface_temperature`, wind, HYCOM_sss |
| 처리수준 | **L4 다중센서 분석/보간** ("Global Analysed", "interpolation of SMOS"), "Nominal time of L4 analysis" | **L3** radiometer **8일 평균** (L2B granule ~12/28~ 누적), "Midpoint of time interval" 존재 |

**설계에 미치는 함의:**
- 두 파일 모두 **WGS84 정규격자** → **투영 재투영 분기는 이 해커톤에서 실행되지 않는다**(골격만 유지, 1차 구현 생략).
- 좌표명이 `latitude/longitude` → rioxarray `.rio` accessor 인식을 위해 **rename/`set_spatial_dims` 전처리 필수**.
- CMEMS에 SSS와 SSD(밀도)가 공존 → 변수 자동탐지는 **`standard_name='sea_surface_salinity'` 엄격일치 필수**(밀도 오선택 차단).
- SMAP 8일합성 vs CMEMS L4 일별분석 → **시간 대표성·처리수준 불일치**가 통계에 혼입 → §11 Caveats로 한정 명기.

## 1. 목적 & 범위

두 NetCDF 해양 표층염분(SSS) 자료를 **동일한 절차**로 비교·검증한다.
모든 자료를 WGS84 정규격자로 표준화 → 저해상도 기준 리샘플 → 통계 검증.

**대상 파일:**

| 파일 | 설명 |
|---|---|
| `dataset-sss-ssd-nrt-daily_20260101T1200Z_P20260122T0000Z.nc` | CMEMS L4 분석 SSS/SSD 일별 (25 MB, NetCDF4) |
| `SMAP_L3_SSS_20260101_8DAYS_V5.0.nc` | SMAP L3 SSS 8일 합성 0.25° (11 MB, NetCDF4) |

**범위:** 정규격자(rectilinear)만. 비정규격자(곡선격자·스와스·모델 ESMF)는 범위 외 — 진입 시 경고 후 중단.
**"범용" 표현 정정:** 본 파이프라인은 **해커톤 2파일(정규격자 WGS84) 중심의 검증 골격**이다. AOI·기준해상도·시간인덱스는 cfg로 노출하되, 비정규격자/투영/타자료 일반화는 골격만 두고 1차 구현 범위 밖.

**분석 영역(AOI):** lat 24~38°N, lon 117~131°E (양자강 하구·동중국해·황해·한반도 남서해안).
※ 이 영역은 위성 SSS 검증에 불리한 조건이 겹친다 — §11 Caveats 참조.

## 2. 확정 결정 사항 (v2 반영)

| 항목 | 결정 |
|---|---|
| 리샘플 라이브러리 | rioxarray `reproject_match`. 고→저는 `Resampling.average` (**동일가중 평균 집계 — 엄밀 conservative 아님**, §5[4]). xesmf 제외 |
| 비교 변수 | **`standard_name='sea_surface_salinity'` 엄격일치** 자동탐지(밀도 차단). 실패 시 후보 출력 + `--var-a/--var-b` |
| 시간 차원 | 각 파일 첫(유일) 공간장. **단, 시간 대표성 메타(SMAP midpoint / CMEMS nominal time)를 읽어 보고·한정**(§11) |
| 실행 환경 | 이 맥에 micromamba 설치 → 경량 `ncval`(§9). **0단계 30분 타임박스**, 초과 시 pip+venv 폴백 |
| 격자 판별 | inspect가 `grid_kind` enum을 **값으로** 보고(GEOGRAPHIC/PROJECTED/IRREGULAR), reproject·pipeline은 **읽기만** |
| 비정규격자 | 범위 외 — 명시적 중단 |
| 해상도 기준 | 두 입력 중 저해상도(coarser). pipeline이 두 InspectReport로 판정 |
| 검증 방향 | **고→저(권장, 헤드라인)**. 저→고(bilinear)는 **진단/비교용으로 강등**(§5-1) — 직접 RMSE 비교 아님, 시간 남으면 |
| 보간 불변식 | **보간은 [4]에서 자료당 1회.** [3]은 무보간(라벨 정규화 + CRS 부착만) |

## 3. 아키텍처 — 순수 변환부 + 명시적 IO 어댑터

각 변환 모듈은 `xarray` 객체를 입출력으로 받는 순수 함수. IO(파일 열기·PNG 쓰기)는 명시적 어댑터로 분리.

```
run_validation.py        # CLI: 경로, --var-a/--var-b, --aoi, --ref, --time-index, --outdir
src/
├── io_nc.py        [1]  open_nc(path) → xr.Dataset  (NetCDF 아니면 거부, decode_cf=True)
├── inspect_nc.py   [2-1] describe(ds) → InspectReport{grid_kind:Enum, dlat, dlon,
│                          coord_names, time_info, var_name, units} — 분류를 '값으로' 보고
├── qc.py           [2-2] apply_qc(da, ds) → da  (_FillValue/valid_range/flag 비트 → NaN)
├── reproject.py    [3]  to_wgs84(da, ds, report) → da  (무보간: rename→x/y, write_crs(4326),
│                          경도 −180~180 정규화·sortby, lat 오름차순, monotonic assert)
├── grid.py         [4a] build_target_grid(bounds, dlat, dlon, crs) → 빈 xr.DataArray 템플릿
├── resample.py     [4b] match_to(src, target) → reproject_match(target, Resampling.average)
├── metrics.py      [5]  stats(eval, ref) → {N,Bias,RMSE,MAE,R,R2}  (R2=NSE)
├── visualize.py         make_map / make_scatter → Figure 반환 (Agg 백엔드)
├── io_out.py            save_fig / save_csv → 디스크 IO 어댑터
└── pipeline.py          run(path_a, path_b, cfg) → results  ([1]→[5] 오케스트레이션·해상도판정)
```

**경계 결정 (v2):**
- **분류는 `inspect_nc`가 enum 값으로 단독 산출**. reproject·pipeline은 그 값을 읽기만(분기 행위는 하되 분류 출처는 한 곳).
- **CRS 의존 함수는 `(da, ds)` 시그니처** — `grid_mapping`이 별도 변수(ds)에 있으므로 da만으론 부족.
- **해상도 비교(coarser 판정)는 pipeline 책무**(2-입력 연산). resample은 "주어진 목표 격자에 정합"만.
- **visualize는 Figure 반환, 디스크 쓰기는 io_out**. 단위 테스트는 무(無)IO. `matplotlib.use("Agg")`로 헤드리스 안전.

## 4. 데이터 흐름 (보간 1회 불변식)

```
A.nc ─[1]open─[2-1]describe─[2-2]QC─┐
                                     ├─▶ [3] to_wgs84: 무보간
B.nc ─[1]open─[2-1]describe─[2-2]QC─┘     (rename x/y, write_crs, 경도 정규화·정렬,
                                            write_nodata(NaN))  → "WGS84 라벨·CRS 확정"
                                            📊 step3_wgs84_A/B.png
                                     │
        pipeline: 두 dlat·dlon 비교 → 저해상도(coarser) 판정
                                     │
        [4a] build_target_grid(AOI, 저해상도 간격, EPSG:4326)
              = 빈 DataArray 템플릿 (중심좌표 linspace, set_spatial_dims, write_crs,
                AOI 경계를 소스 셀 경계에 스냅 → 반픽셀 시프트 방지)
                                     │
        [4b] 각 자료 reproject_match(target)  ← 여기서 보간 1회 (재투영 필요시도 동일 1워프)
              고→저: Resampling.average / (진단) 저→고: bilinear
              📊 step4_resampled_A/B.png
                                     │
        [5] stats(평가 on 기준격자, 기준)  ← 둘 다 유효 셀만 마스킹
              비교 테이블 + step5 산점도/지도
                                     ▼
        results/tables/*.csv, results/figures/*.png
```

**불변식 (v2 정정):** 보간은 **[4] reproject_match에서만, 자료당 1회**. [3]은 좌표 라벨/CRS만 확정하고 **절대 보간하지 않는다**(투영 자료여도 재투영을 [3]에서 하지 않고, [4]가 소스CRS≠목표CRS를 단일 워프로 처리). 이 해커톤 두 파일은 이미 WGS84라 [3]은 정렬·CRS부착뿐 → 보간 0회 + [4] 1회.

## 5. 단계별 명세

### [1] 입력 검증 — `io_nc.py`
파일 magic(`CDF`/`HDF`) 확인 후 `xr.open_dataset(decode_cf=True)`. 아니면 명확한 에러로 중단.

### [2-1] NC 파악 (보고 전용) — `inspect_nc.py`
`grid_kind` enum(GEOGRAPHIC/PROJECTED/IRREGULAR)을 **계산해 InspectReport에 담는다**. 그 외: 자료유형, dlat/dlon, 좌표명, **시간 정보**(`time_coverage_start/end`·`time_bnds`·midpoint/nominal time), 변수명·units. `is_regular_grid(lat, lon, rtol=1e-4)`로 정규/비정규 판정. **자료유형 4분류는 보고 장식이므로 1차 최소화**(좌표·해상도·시간·grid_kind만 필수).

### [2-2] QC — `qc.py`
`_FillValue`/`missing_value` → NaN, `valid_range`/`valid_min/max` 밖 → NaN, QC flag(`flag_masks`&`flag_values` 비트마스크) good만 통과. **동반 QC 변수 없으면 자동 건너뜀.** SMAP는 SSS uncertainty 변수가 있으므로 임계 마스킹 옵션 가능(stretch).

### [3] WGS84 표준화 (무보간) — `reproject.py`
1. `grid_kind==IRREGULAR` → 범위 외, 중단.
2. 좌표 `longitude→x, latitude→y` rename(또는 `set_spatial_dims`), `write_crs("EPSG:4326")`.
3. 경도 −180~180 정규화 → `sortby(x)`, lat `sortby(y)` 오름차순.
4. `write_nodata(np.nan, encoded=False)` — reproject 시 NaN 보존·0누수 방지.
5. 진입부 `assert np.all(np.diff(x)>0) and np.all(np.diff(y)>0)` (정렬 누락 조기 실패).
6. **재투영은 하지 않음**(PROJECTED여도 CRS 부착만; 실제 워프는 [4]).
시각화: `step3_wgs84_A/B.png`.

### [4] 해상도 정합 — `grid.py` + `resample.py`
- `build_target_grid(bounds, dlat, dlon, crs)` → `xr.DataArray(np.nan, coords={y,x})`에 `set_spatial_dims`+`write_crs`. 중심좌표는 **명시적 셀수**(round((hi-lo)/d))로 생성, **AOI 경계를 저해상도 셀 경계에 스냅**.
- `reproject_match(target, resampling=Resampling.average)`로 고해상도를 목표 격자에 정합.
- **average는 동일가중 평균 집계(소스 중심이 대상 셀에 떨어지는 픽셀 평균) — 엄밀 면적가중 conservative가 아님.** 목표 간격을 소스의 정수배로 스냅하면 면적평균에 수렴. 비정수 배율이면 로그에 "conservative 근사" 경고.
시각화: `step4_resampled_A/B.png`.

### [5] 검증 — `metrics.py`
둘 다 유효한 셀만 1:1 매칭. 통계 6개: `N`, `Bias`(=평가−기준), `RMSE`, `MAE`, `R`(Pearson), **`R²` = 1 − SSE/SST (Nash–Sutcliffe형 결정계수, 음수 허용)** — bias·스케일 오차까지 벌함. R과 명확히 구분(R²≠R²of corr). 변수 `units`·`standard_name` 일치 확인, 불일치 시 경고/중단.

### 5-1. 저→고 방향 — 진단용 (강등)
저→고 bilinear는 보간 셀이 공간 자기상관된 중복표본이라 **N이 부풀고 유효자유도는 저해상도에 묶임** → 고→저와 한 표에서 RMSE 직접 비교 금지. **시각적 진단(보간 아티팩트 지도)** 또는 N·유효DOF 병기로만 사용. 시간 남으면 수행(stretch). 헤드라인은 고→저.

## 6. 에러 처리 & 가드

| 단계 | 가드 | 동작 |
|---|---|---|
| [1] | NetCDF 아님/open 실패 | `nc 파일만 지원` 중단 |
| [2-1] | 좌표 후보 미발견 | 못 찾은 좌표 명시 중단 |
| [2-2] | SSS(standard_name) 자동탐지 실패 | 후보 목록 + `--var` 안내 |
| [3] | IRREGULAR | 범위 외 경고 후 중단 |
| [3] | 정렬 후 비단조 좌표 | assert 조기 실패 |
| [4] | AOI ∩ 자료 = 빈 영역 | `분석 영역 유효데이터 없음` 중단 |
| [4] | nodata 미설정 상태로 reproject | `write_nodata(NaN)` 강제(누락 시 경고) |
| [5] | 공통 유효 N < 10 | 통계 내되 신뢰불가 경고 |
| [5] | 두 변수 units/standard_name 불일치 | 경고/중단(밀도 오선택 차단) |

**원칙:** 비정규=명시적 중단 · NaN 전파(0/Fill 금지, `write_nodata`로 reproject 경계 보존) · 부분 산출물 보존(production 경로 한정, 테스트는 무IO).

## 7. 테스트 & 검증

| 모듈 | 테스트 |
|---|---|
| `metrics` | 손계산 벡터 → Bias/RMSE/R/**NSE형 R²(음수 케이스 포함)** 수치 일치 (최우선, 0의존성) |
| `qc` | FillValue/valid_range/flag 합성 → NaN 위치 |
| `reproject` | 0~360→−180~180 정렬, lat 뒤집기, **rename/write_crs/spatial_dims 후 `.rio` 인식** |
| `grid`/`resample` | **CRS 부여 헬퍼** 사용, 정수배 블록 average, **결측 포함 2×2 블록**(nodata 제외 확인), reproject_match 격자·셀경계 정렬 |
| 통합 | 실제 2개 nc → 무중단 완주 + CSV/PNG 생성 |

**합성 픽스처엔 `write_crs`+`set_spatial_dims` 부여 헬퍼 필수**(없으면 `MissingSpatialDimensionError`). 투영 경로는 실파일에 없으므로 1차 무검증 허용(골격만).
**완료검증:** "완료" 주장 전 (a) `pytest` 통과 출력, (b) `run_validation.py` 실행 → CSV/PNG 존재 확인. 증거 없이 완료선언 금지.

## 8. 빌드 순서 — MVP 수직 슬라이스 우선 (v2 재배치)

가장 어려운 reproject를 핵심 경로에서 빼고, **오전 안에 화면에 그림 1장**을 목표로 end-to-end를 먼저 완성.

```
0. micromamba(경량 env) 설치 + 실파일 introspection [30분 타임박스, 초과 시 pip+venv 폴백]
   └ 변수명·좌표명·dlat/dlon·시간메타 확인(일부 §0에서 선수행 완료) → /log
─── MVP 수직 슬라이스 (둘 다 WGS84 확인됨 → reproject 재투영 불필요) ───
1. io_nc + inspect(최소: 좌표/해상도/시간/grid_kind) + metrics(손계산 검증)
2. reproject 최소(rename→x/y, write_crs, 경도정렬, write_nodata) — 무보간
3. grid.build_target_grid + resample.match_to(average) — 두 자료 AOI 저해상도 정합
4. pipeline 연결 → metrics → **산점도+통계박스 PNG 1장** ★여기서 "도는 결과"
─── 점진 강화 ───
5. QC(_FillValue/valid_range, 필요시 flag/uncertainty)
6. visualize 확장(AOI 지도 2장) + io_out 분리
7. 가드(비정규 중단, units 불일치, N<10) + 통합 스모크
8. (stretch) 저→고 진단 방향 + Caveats 반영 발표자료
```
**각 단계 완료마다 `/log` 1항목 append**(§아래). 0단계·MVP 첫 PNG·막힘→해결은 반드시 인용형 기록.

## 9. 환경 & 라이브러리 (경량화)

micromamba로 `ncval`(Python 3.10) 생성. **범위 외 `xesmf/esmpy/pyresample`·`dask`·`gdal` 제거**(solve 폭탄 방지).

```
필수: xarray netCDF4 numpy scipy pandas rioxarray rasterio pyproj matplotlib
지도: cartopy (visualize에서 try/except import, 실패 시 plain matplotlib pcolormesh 폴백)
```

## 10. 표준 규약

| 항목 | 표준 |
|---|---|
| 좌표계 | WGS84(EPSG:4326), 도 단위, 차원명 `x`/`y`(rename 후) |
| 격자 | rectilinear, lat 오름차순, lon −180~180, 픽셀중심 등록 |
| AOI | lat 24~38°N, lon 117~131°E, 셀 경계 스냅 |
| 기준 해상도 | 두 입력 중 저해상도 |
| 보간 | [4]에서 1회, nodata=NaN |
| 입력 | nc 전용 / 비정규 범위 외 |

## 11. 과학적 한정 (Caveats) — 결과 해석·발표에 명기

실파일 메타로 확인된 **구조적 불일치**. 무시하면 통계를 오독한다.

1. **시간 대표성 불일치:** SMAP=8일 평균(저역통과), CMEMS=L4 일별 분석. 8일 윈도우 midpoint와 CMEMS nominal time의 시간 무게중심 차이를 보고하고, **RMSE는 "시간 평활 + 진오차"의 상한 추정치**로 한정.
2. **처리수준/깊이 불일치:** SMAP=L3 radiometer 표층(~1cm skin), CMEMS=L4 다중센서 분석장(bulk/보간). Bias의 일부는 모델오차가 아니라 **near-surface 성층·정의 차이**. depth/units 보고 + 한정.
3. **AOI 최악조건:** 동중국해/황해 연안은 위성 SSS에 RFI·육지오염·1월 저수온 민감도 저하·플룸 극변동이 겹침. 헤드라인 통계와 별도로, 가능하면 **연안 마스크/uncertainty 임계로 open-water 부분집합** 통계 병기(stretch).
4. **average≈conservative 근사:** 엄밀 면적가중 아님. 정수배 스냅 시 수렴, 비정수 배율은 근사임을 명기.
5. **저→고 통계 비교불가:** N 팽창·자기상관으로 직접 RMSE 비교 금지(진단용).

## 12. 채점 정렬 (과정 70 : 결과 30)

과정 70점은 `submit/PROCESS_LOG.md` 기반 AI 객관채점. **구현 계획에 단계별 로깅을 명문화:**
- 빌드 순서 0~8 각 완료마다 `/log`로 항목 1개 append(실제 지시/프롬프트 핵심 인용 + 팀원 이름).
- 0단계 introspection 결과, MVP 첫 PNG, 막힘→해결 순간은 필수 기록.
- 작업 전 `submit/BEFORE_AFTER.md`의 Before(기존 SSS 검증을 어떻게/얼마나 들여 했는지) 채우기.
