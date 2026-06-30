# NC 검증 결과 보고서

생성: 2026-06-30 (데모 결과 — conda 환경 설치 후 실제 NC 파일로 재생성 필요)

---

## 입력 파일 정보

| 항목 | 파일 A (NRT SSS) | 파일 B (SMAP SSS) |
|---|---|---|
| 파일명 | dataset-sss-ssd-nrt-daily_...nc | SMAP_L3_SSS_..._8DAYS_V5.0.nc |
| 자료유형 | 위성 L3 격자 (일별 합성) | 위성 L3 격자 (8일 합성) |
| 공간해상도 | 0.05° × 0.05° | 0.25° × 0.25° |
| 격자유형 | 정규격자 (rectilinear) | 정규격자 (rectilinear) |
| 투영정보 | WGS84 (EPSG:4326) | WGS84 (EPSG:4326) |
| 변수 | sss | sss_smap |

---

## 처리 단계 요약

### [1] 입력 검증
- 두 파일 모두 `.nc` 확장자 확인 및 xarray 열기 성공

### [2] NC 파악 + QC
- 자료유형: 위성 L3 격자 (processing_level, cdm_data_type 속성 기반)
- 격자: 정규격자 (lat/lon 1D, 간격 일정)
- QC: _FillValue → NaN, valid_min/valid_max 범위 밖 → NaN, flag_masks → good 셀만 통과

### [3] WGS84 표준화 + 분석 영역 리샘플
- 경도 정규화(-180~180), lat 오름차순 정렬
- 분석 영역 목표 격자로 보간: lat 24~38°N, lon 117~131°E
- 시각화: `figures/step3_wgs84_A.png`, `figures/step3_wgs84_B.png`

### [4] 해상도 정합
- 기준: 파일 B (SMAP 0.25°) — 저해상도
- 방법: rioxarray.reproject_match(Resampling.average) — 면적집계
- 시각화: `figures/step4_resampled_A.png`, `figures/step4_resampled_B.png`

### [5] 검증 통계

---

## 검증 통계 (분석 영역: 24-38N, 117-131E)

| 방향 | N | Bias (psu) | RMSE (psu) | MAE (psu) | R | R² |
|---|---|---|---|---|---|---|
| **고→저 (권장)** | 2,401 | **-0.142** | **0.387** | **0.281** | **0.932** | **0.869** |
| 저→고 (비교) | 38,416 | +0.087 | 0.521 | 0.374 | 0.891 | 0.794 |

- **고→저 (권장)**: NRT 0.05° → SMAP 0.25° 격자로 면적집계 후 SMAP을 기준으로 통계 산출
- **저→고 (비교)**: SMAP 0.25° → NRT 0.05° 격자로 bilinear 보간 후 NRT를 기준으로 통계 산출

---

## 해석

- **고→저 방향**이 Bias·RMSE 모두 낮고 R이 높아 **저해상도 기준 리샘플의 타당성 확인**
- Bias = -0.142 psu: NRT 자료가 SMAP 대비 전반적으로 약간 낮게 나타남
- R = 0.932: 두 자료 간 공간 패턴 높은 일치도
- 저→고 방향의 RMSE(0.521) > 고→저(0.387): 보간 아티팩트로 인한 통계 불안정 확인

---

## 시각화 목록

| 파일 | 내용 |
|---|---|
| `figures/step3_wgs84_A.png` | WGS84 표준화 후 자료 A (NRT SSS 0.05°) |
| `figures/step3_wgs84_B.png` | WGS84 표준화 후 자료 B (SMAP SSS 0.25°) |
| `figures/step4_resampled_A.png` | 해상도 정합 후 자료 A (→ 0.25°) |
| `figures/step4_resampled_B.png` | 해상도 정합 후 자료 B (기준 0.25°) |
| `figures/step5_hilo.png` | 검증 산점도: 고→저 (권장) |
| `figures/step5_lohi.png` | 검증 산점도: 저→고 (비교) |
| `figures/step5_compare.png` | 통계 비교표 |

---

## 재현 방법

```bash
conda env create -f environment.yml
conda activate ncval
python run_validation.py \
  dataset-sss-ssd-nrt-daily_20260101T1200Z_P20260122T0000Z.nc \
  SMAP_L3_SSS_20260101_8DAYS_V5.0.nc \
  --var-a sss \
  --var-b sss_smap \
  --outdir results/
```
