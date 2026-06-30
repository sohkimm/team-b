# NC 검증 파이프라인 — 설계 문서 (v3)

> 작성일: 2026-06-30 · 팀B (teamB) · 작성자: 김소희(ksh)
> 상태: 적대적 멀티에이전트 리뷰 **2회** + 실파일 재검증 반영(v3) → 구현 계획 단계
>
> **v3 변경 요약 (Round 2 비평 + 실파일 재검증 수용):**
> ① 기준격자 = **저해상도(SMAP) native 격자를 AOI로 크롭** — 합성 target grid 폐기,
>    ref는 항등 통과(재보간 안 함). 스냅 위상·linspace 간격오차·write_transform 문제 동시 소멸.
> ② CMEMS=0.125°/SMAP=0.25° **정수 2배** 확정 → MVP는 pure-xarray `coarsen(2,2).mean()`
>    (rasterio/cartopy 비의존), reproject_match(average)는 강화 경로.
> ③ 헤드라인 통계 = **대칭지표**(Bias·RMSE·MAE·Pearson R). NSE형 R²은 truth-가정
>    비대칭이라 양방향·캡션부 부차지표로 강등.
> ④ PROJECTED 분기 **삭제** → [3]에서 명시적 중단(범위 외). units 차단은 standard_name만.
> ⑤ cfg 스키마 표 정의, §0을 비규범 스냅샷으로 강등, NON-GOAL 격리 박스 추가.

---

## ⛔ NON-GOAL (범위 밖 — 코드 작성 금지선, 발표/백로그 전용)

> **writing-plans는 §8의 MVP 1~4단계만 작업항목(task)으로 변환한다. 아래는 task 금지.**
> - §11 오차 귀속(Error Attribution) 5항목 → **발표 슬라이드 텍스트**일 뿐 코드 아님
> - open-water/연안 마스킹, uncertainty 임계 마스킹 → 민감도 분석(stretch), 헤드라인 금지
> - 저→고(bilinear) 진단 방향 → 시간 남을 때만
> - PROJECTED/비정규격자 일반화 → 범위 외, [3]에서 중단만
> - reproject_match(rasterio) 정밀 경로 → MVP 통과 후 강화

---

## 0. 실파일 관측 스냅샷 (비규범 — 런타임 inspect_nc가 유일 분류 권위)

> ⚠️ 아래는 NetCDF 메타 추출로 얻은 **관측 스냅샷**이며 규범(normative)이 아니다.
> 분류·해상도의 **단일 진실 출처는 런타임 `inspect_nc`**. §8 step0은 이 표를 **재현하지 못하면 중단**한다.

| 항목 | CMEMS (`dataset-sss-ssd...`) | SMAP (`SMAP_L3_SSS_..._8DAYS`) |
|---|---|---|
| 좌표명 | `latitude`, `longitude` (1D, degrees) | `latitude`, `longitude` (1D, degrees) |
| **공간해상도** | **0.125°** (`grid_resolution`, "0.125 degrees") | **0.25°** ("0.25x0.25 deg grid") |
| 격자/투영 | 지리 WGS84, 투영 없음 | 지리 WGS84, 투영 없음 |
| 변수 | `sea_surface_salinity`(+error), `sea_surface_density`(+error) | `sea_surface_salinity`(+uncertainty), `sst`, wind, HYCOM_sss |
| 처리수준 | L4 다중센서 분석/보간 (Buongiorno Nardelli 2016) | L3 radiometer 8일 평균 |
| units(염분) | (불명확 — psu/1e-3) | `1e-3` |
| 시간 | nominal time(일별), time_bnds 없음 | time 좌표=interval midpoint, `time_coverage_start/end`, time_bnds 없음 |

**확정 함의:**
- **해상도 위계 확정:** CMEMS 0.125° = 고해상도(평가), SMAP 0.25° = **저해상도 = 기준(ref)**. 비율 **정확히 2배(정수)**.
- 정수 2배 → CMEMS를 SMAP 격자로 **`coarsen(2,2).mean()` 블록평균**이 (정렬 시) 가능 → **MVP는 rasterio 불필요**.
- 둘 다 WGS84 정규격자 → **투영/비정규 분기는 실행되지 않음**(삭제, [3]에서 중단만).
- units 문자열이 서로 다를 수 있음 → **차단은 standard_name만**.
- 시간 윈도우는 `time_coverage_start/end`(전역), 중심은 time 좌표 스칼라 → **time_bnds 의존 제거**.

## 1. 목적 & 범위

CMEMS L4 분석 SSS(0.125°)와 SMAP L3 8일합성 SSS(0.25°)를 **동일 절차**로 비교·검증한다.
저해상도(SMAP) native 격자를 기준으로 고해상도(CMEMS)를 정합 → 통계 검증.

**범위:** 정규격자 WGS84 전용. 투영·비정규격자는 [3]에서 **명시적 중단**.
**"범용" 정정:** 본 파이프라인은 **해커톤 2파일 중심 검증 골격**이다(범용 일반화는 NON-GOAL).

**분석 영역(AOI):** lat 24~38°N, lon 117~131°E. (위성 SSS에 불리한 조건 — §11 오차 귀속 참조)

## 2. 확정 결정 사항 (v3)

| 항목 | 결정 |
|---|---|
| 기준 격자 | **저해상도(SMAP) native 격자를 AOI로 크롭한 것** = reproject 대상. ref는 **항등 통과(재보간 안 함)** |
| 해상도 판정 | dlat/dlon 비교로 coarser=ref. **동률(|Δ|<5%)이면 path_a를 ref로 결정적 타이브레이크.** 이 파일들은 2배라 SMAP=ref |
| 정합 방법 | MVP: 정수배·정렬 시 **`coarsen(2,2).mean()`**(pure xarray). 강화: `reproject_match(average)` (비정렬/일반 대비) |
| 비교 변수 | `standard_name='sea_surface_salinity'` 엄격일치 자동탐지(밀도 차단). 실패 시 후보+`--var` |
| units | 차단은 **standard_name만**. units는 등가집합 정규화 후 **경고만**(중단 금지) |
| 헤드라인 통계 | **대칭지표: N, Bias, RMSE, MAE, Pearson R**. R²(NSE)는 부차·양방향·"ref≠truth" 캡션 |
| 시간 | 각 파일 첫(유일) 공간장(`time` len=1 assert). 윈도우=`time_coverage_start/end`, 중심=time 스칼라 → `time_offset_days` 출력 |
| 투영/비정규 | [3]에서 명시적 중단 (범위 외) |
| 검증 방향 | 고→저(헤드라인). 저→고(bilinear)는 진단용(NON-GOAL) |

## 3. 아키텍처

순수 변환부 + 명시적 IO. **`pipeline.run`은 results 딕트(통계+Figure)만 반환(순수), 디스크 쓰기는 `run_validation.py`가 io_out로 수행.**

```
run_validation.py    # CLI → cfg 생성, pipeline.run 호출, io_out로 CSV/PNG 저장
src/
├── io_nc.py     [1]  open_nc(path) → ds  (NetCDF 아니면 거부, decode_cf)
├── inspect_nc.py[2-1] describe(ds) → InspectReport{grid_kind:Enum, dlat, dlon, coord_names,
│                       var_name, units, time_len, time_center, time_window} — 유일 분류권위
├── qc.py        [2-2] apply_qc(da, ds) → da
├── reproject.py [3]  to_wgs84(da, ds, report) → da  (GEOGRAPHIC만; PROJECTED/IRREGULAR 중단)
├── resample.py  [4]  to_ref_grid(eval_da, ref_da, method) → eval_on_ref  (ref는 손대지 않음)
├── metrics.py   [5]  stats(eval, ref) → {N, Bias, RMSE, MAE, R, R2_nse}
├── visualize.py      make_scatter / make_map → Figure (Agg 백엔드)
├── io_out.py         save_fig / save_csv → 디스크 IO
└── pipeline.py       run(path_a, path_b, cfg) → results 딕트 (해상도판정·오케스트레이션, 무(無)디스크)
```
※ MVP 동안 `resample`은 coarsen 블록평균만, `io_out`은 pipeline/CLI 인라인 허용 → 첫 PNG 후 분리.

**cfg 스키마 (dataclass):**

| 필드 | 타입 | 기본값 | 의미 |
|---|---|---|---|
| `aoi` | (lat0,lat1,lon0,lon1) | (24,38,117,131) | 분석 영역 |
| `ref` | `"auto"`/`"a"`/`"b"` | `"auto"` | auto=coarser 자동판정. a/b 지정 시 **자동판정 무시(수동 override)** |
| `var_a`,`var_b` | str/None | None | None=standard_name 탐지 |
| `time_index` | int | 0 | 사용할 time 슬라이스 |
| `method` | `"coarsen"`/`"average"`/`"bilinear"` | `"coarsen"` | 정합 방법 |
| `outdir` | path | `results/` | 출력 위치 |

**경계 결정:** 분류는 inspect_nc enum 단독 산출(소비자는 읽기만) · CRS 의존 함수는 `(da, ds)` · 해상도 판정은 pipeline · visualize는 Figure 반환 · **단계별 PNG는 오케스트레이터가 visualize→io_out 호출로 생성**(변환 모듈은 IO 안 함).

## 4. 데이터 흐름

```
A.nc ─[1]open─[2-1]describe─[2-2]QC─[3]to_wgs84(무보간)─┐
B.nc ─[1]open─[2-1]describe─[2-2]QC─[3]to_wgs84(무보간)─┘
                                     │
        pipeline: dlat/dlon 비교 → ref=저해상도(SMAP), eval=고해상도(CMEMS)
                                     │
        ref_aoi = ref.sel(AOI)            ← ref native 격자, AOI 크롭, **재보간 없음**
        eval_on_ref = to_ref_grid(eval, ref_aoi, method)
            MVP   : eval.coarsen(x=2,y=2).mean() 후 ref_aoi에 정렬 (정수배·정렬 전제)
            강화  : eval.rio.reproject_match(ref_aoi, Resampling.average)
                                     │
        [5] stats(eval_on_ref, ref_aoi)   ← 둘 다 유효 셀만 마스킹
            대칭지표 + (부차) NSE 양방향
                                     ▼
        results 딕트 → run_validation.py가 io_out로 CSV/PNG 저장
        (오케스트레이터가 visualize 호출: step3 지도, 산점도+통계박스)
```

**핵심:** 기준은 **ref의 native 격자**이므로 ref는 절대 재보간되지 않는다(도메인 BLOCKER 해소). 보간은 eval에만 1회. 합성 target grid를 만들지 않으므로 스냅 위상·linspace 간격오차·write_transform 문제가 발생하지 않는다(아키/래스터 BLOCKER 해소).

## 5. 단계별 명세

### [1] 입력 검증 — `io_nc.py`
magic(`CDF`/`HDF`) 확인 후 `xr.open_dataset(decode_cf=True)`. 아니면 중단.

### [2-1] NC 파악 (보고 전용, 유일 분류권위) — `inspect_nc.py`
`grid_kind` enum(GEOGRAPHIC/PROJECTED/IRREGULAR), dlat/dlon, 좌표명, var_name, units, **time_len(=1 확인), time_center(time 스칼라), time_window(time_coverage_start/end)**. `is_regular_grid(lat,lon,rtol=1e-4)`. **step0은 §0 스냅샷(해상도·grid_kind)을 재현 못 하면 중단.**

### [2-2] QC — `qc.py`
`_FillValue`/`missing_value`→NaN, `valid_range`/`valid_min/max` 밖→NaN, flag 비트마스크 good만. 동반 QC 변수 없으면 자동 건너뜀.

### [3] WGS84 표준화 (무보간) — `reproject.py`
1. `grid_kind != GEOGRAPHIC`(PROJECTED 또는 IRREGULAR) → **범위 외, 명시적 중단**. (4326 하드코딩·무조건 경도정규화로 투영자료 오염시키는 골격 제거)
2. `rename({"longitude":"x","latitude":"y"})` **단일 경로** 후 `set_spatial_dims(x_dim="x", y_dim="y")`, `write_crs("EPSG:4326")`.
3. 경도 −180~180 정규화 → `sortby("x")`, `sortby("y")` 오름차순.
4. `encoding.pop("_FillValue", None)` 후 `write_nodata(np.nan, encoded=False)` — attrs/encoding 중복 제거 + NaN 보존.
5. 진입부 `assert time_len==1`, 정렬 후 `assert np.all(np.diff(x)>0) and np.all(np.diff(y)>0)`.
시각화(오케스트레이터): `step3_wgs84_A/B.png`.

### [4] 해상도 정합 — `resample.py`
`to_ref_grid(eval_da, ref_aoi, method)`. **ref_aoi는 입력으로만 받고 변형하지 않음**(ref 항등).
- `method="coarsen"`(MVP): 정수배(2)·정렬 확인 후 `eval_da.coarsen(x=2,y=2, boundary="trim").mean()`, ref_aoi 좌표에 정렬 assert. **rasterio 불필요.**
- `method="average"`(강화): `eval_da.rio.reproject_match(ref_aoi, Resampling.average)`. `src_nodata=np.nan` 명시.
- `method="bilinear"`(진단, NON-GOAL): reproject_match bilinear.
시각화: `step4_resampled_A/B.png`.

### [5] 검증 — `metrics.py`
둘 다 유효 셀만 1:1. **헤드라인(대칭): N, Bias(=평가−기준), RMSE, MAE, R(Pearson).** 부차: `R²=1−SSE/SST`(NSE) — ref=truth 가정이라 **양방향 NSE(A→B, B→A) 병기 + "ref는 reference이지 truth 아님" 캡션**, 음수 허용. units는 등가정규화 후 경고만, 차단은 standard_name 불일치만.

## 6. 에러 처리 & 가드

| 단계 | 가드 | 동작 |
|---|---|---|
| [1] | NetCDF 아님 | `nc 파일만 지원` 중단 |
| [2-1] | 좌표 미발견 / time_len≠1 / §0 스냅샷 불일치 | 명시 중단 |
| [2-2] | SSS standard_name 탐지 실패 | 후보 목록+`--var` |
| [3] | PROJECTED 또는 IRREGULAR | 범위 외 중단 |
| [3] | 정렬 후 비단조 좌표 | assert 실패 |
| [4] | coarsen 정수배·정렬 불성립 | average 경로로 폴백 또는 경고 |
| [4] | AOI ∩ 자료 = 빈 | `유효데이터 없음` 중단 |
| [5] | 공통 유효 N<10 | 신뢰불가 경고 |
| [5] | standard_name 불일치 | 중단(밀도 차단). units는 경고만 |

**원칙:** 비정규/투영=중단 · NaN 전파(0/Fill 금지) · ref 무변형 · 부분 산출물 보존(production 한정).

## 7. 테스트 & 검증

| 모듈 | 테스트 |
|---|---|
| `metrics` | 손계산 벡터 → 대칭지표 + NSE(음수 케이스) 수치 일치 (최우선) |
| `qc` | FillValue/valid_range/flag → NaN 위치 |
| `reproject` | 경도정규화·lat정렬, rename→x/y 후 `.rio` 인식, time_len assert |
| `resample` | **정렬된 2×2 정수배 블록 coarsen=블록평균**, 결측 포함 블록(NaN 처리), ref 무변형 확인 |
| 통합 | 실제 2개 nc → 무중단 완주 + results 딕트 + CSV/PNG |

합성 픽스처엔 `write_crs`+`set_spatial_dims` 헬퍼. **완료검증:** "완료" 전 (a) pytest 통과 출력, (b) run 실행 → CSV/PNG 존재 확인.

## 8. 빌드 순서 — MVP 수직 슬라이스 (pure-xarray, rasterio/cartopy 비의존)

```
0. micromamba(경량 env) 설치 + 실파일 introspection [30분 타임박스]
   └ §0 스냅샷 재현 확인(해상도 2배·WGS84·변수명) → /log [필수]
─── MVP (둘 다 WGS84·정수2배 → coarsen으로 정합, rasterio 불요) ───
1. io_nc + inspect(좌표/해상도/시간/grid_kind/var) + metrics(손계산 검증)
2. reproject 최소(rename→x/y, write_crs, 경도정렬, time assert) — 무보간
3. resample.to_ref_grid(coarsen) — CMEMS를 SMAP(AOI크롭) 격자로 블록평균
4. pipeline → metrics → visualize.make_scatter(최소) → **산점도+통계박스 PNG 1장 저장**
      ★여기서 "도는 결과" — make_scatter·저장까지 MVP에 포함 [필수 /log: 첫 PNG]
─── 강화 (시간 남는 만큼) ───
5. QC(_FillValue/valid_range)
6. visualize 확장(AOI 지도 2장) + io_out 분리
7. 가드(투영/비정규 중단, units, N<10) + reproject_match(average) 강화경로 + 통합 스모크
8. (NON-GOAL) 저→고 진단 / 오차귀속 발표자료
```
**로깅: 필수 3개**(step0, 첫 PNG, 막힘→해결)는 인용형 즉시, 나머지는 세션 끝 일괄 보정 허용.

## 9. 환경 & 라이브러리

micromamba `ncval`(Python 3.10). **MVP는 `xarray netCDF4 numpy scipy pandas matplotlib`만으로 완주**(coarsen·산점도). rasterio/rioxarray·cartopy는 **강화 단계 의존**.

```
MVP 필수 : xarray netCDF4 numpy scipy pandas matplotlib
강화/선택: rioxarray rasterio>=1.3,<2 pyproj  (reproject_match 강화경로; GDAL는 rasterio가 동반)
지도(선택): cartopy (visualize try/except, 실패 시 plain matplotlib pcolormesh(shading="nearest") 폴백)
폴백: 0단계 solve 30분 초과 시 pip+venv로 MVP 6종만 설치(전부 순수휠 → 맥에서 안전)
```

## 10. 표준 규약

| 항목 | 표준 |
|---|---|
| 좌표계 | WGS84(EPSG:4326), 차원명 `x`/`y`(rename 후) |
| 격자 | rectilinear, lat 오름차순, lon −180~180, 픽셀중심 |
| 기준 격자 | **저해상도 자료의 native 격자를 AOI로 크롭**(합성 안 함, ref 무변형) |
| 정합 | 정수배·정렬 시 coarsen 블록평균(MVP) / reproject_match average(강화), nodata=NaN |
| 헤드라인 통계 | 대칭(Bias·RMSE·MAE·Pearson R); NSE는 부차·양방향·캡션 |
| 입력 | nc 전용 / 투영·비정규 [3]에서 중단 |

## 11. 오차 귀속 (Error Attribution) — 발표 전용(NON-GOAL, 코드 아님)

> 결함 고백이 아니라 **"파이프라인이 메타데이터에서 불일치 원인을 구조적으로 귀속한다"는 차별화 기능**으로 프레이밍.
> 헤드라인 = 숫자 한 줄(Bias/RMSE/R) + "이 중 X는 아래 구조적 요인의 상한".

1. **시간 평활:** SMAP 8일평균 vs CMEMS L4 일별. `time_offset_days`(중심차 ~3.5일)를 출력해 RMSE에 시간평활 기여가 섞임을 정량 표기. (midpoint=명목중심, 실제 관측가중과 다름 한 줄 명기)
2. **처리수준/깊이:** SMAP L3 radiometer(~1cm skin) vs CMEMS L4 분석장(bulk/보간). Bias 일부는 성층·정의 차이.
3. **AOI 조건:** 동중국해/황해 연안 = RFI·육지오염·1월 저수온 민감도·플룸 변동. open-water/uncertainty 마스킹은 **사전등록·전AOI 병기·제거율 보고** 시에만 민감도 분석으로(검열편향 주의).
4. **정합 근사:** coarsen=정수배 정확 블록평균(이 파일들은 2배라 정확). average는 동일가중 근사.
5. **저→고 비교불가:** N 팽창·자기상관 → 직접 RMSE 비교 금지(진단용).

## 12. 채점 정렬 (과정 70 : 결과 30)

`submit/PROCESS_LOG.md` 기반 객관채점. **필수 로그 3개**(step0 introspection, MVP 첫 PNG, 막힘→해결)는 실제 프롬프트 핵심 인용 + 팀원 이름으로 즉시 기록, 나머지는 일괄 보정. 작업 전 `submit/BEFORE_AFTER.md` Before(기존 SSS 검증 방식) 채우기.
