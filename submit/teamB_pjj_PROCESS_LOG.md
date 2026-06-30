# PROCESS_LOG — 작업 기록 (과정 70점의 핵심 근거)

> 표준 헤더(CLAUDE.md 등)를 로드했다면 에이전트가 알아서 채워 줍니다. 비면 직접 채우세요.
> 원칙: **실제로 시킨 프롬프트를 그대로 인용**할 것. 요약만 있으면 점수가 깎입니다.

## 작성자 정보 (개인별 로그 — 본인 것만)
- 팀명: TeamB
- 본인 이름(작성자): pjj  ← 본인 이름(로마자)으로 수정 필요
- 공통과제(우리 팀이 자동화한 반복 수작업): NetCDF 해양 관측 자료(SSS) 품질 검증 및 두 파일 간 통계 비교 — 기존 수작업을 에이전트 파이프라인으로 자동화
- 내가 맡은 부분: 범용 NC 검증 파이프라인 설계 및 구현 전체 (5단계: 입력검증 → NC파악+QC → WGS84표준화 → 해상도정합 → 통계검증)
- 자유과제: 서브에이전트 기반 TDD 구현 (단계별 독립 에이전트 + 코드 리뷰 자동화)

## 효과 측정 (Before → After, 결과 ⑥ 채점용 — 형식 자유)

| 지표 | Before(기존 수작업) | After(에이전트화) |
|------|------|------|
| NC 파일 검증 소요 시간 | 수 시간 (격자 파악, 좌표계 확인, 수동 플롯, 통계 계산 각각 수작업) | CLI 1줄 실행 (`python run_validation.py A.nc B.nc --var-a sss --var-b sss_smap`) |
| 다루는 파일 수 | 2개 파일 수작업 → 스크립트 없으면 매번 반복 | 어떤 NC 파일 쌍도 동일 절차로 자동 처리 |
| 산출물 수 | 산발적 (있으면 PNG 몇 장, 통계 메모) | 표준화된 7장 PNG + CSV 통계표 + report.md 자동 생성 |
| 일관성·재현성 | 사람마다 절차 달라짐 | 매 실행 동일 절차 보장 (WGS84 표준화·저해상도 기준 리샘플 고정) |

## 사용 기법 (권장·가점, 필수 아님)
- [x] (a) 서브에이전트 / 역할 분담 — 태스크별 구현 에이전트 + 코드 리뷰 에이전트 분리 (총 20+ 서브에이전트)
- [ ] (b) 외부 도구·데이터 연동
- [x] (c) 재사용 산출물 — superpowers 스킬(brainstorming, writing-plans, subagent-driven-development), 설계 스펙 문서, 구현 계획 문서

---

## 작업 로그 (단계마다 1개씩 누적 / 시간순)

---
### [#1] PIPELINE.MD 기반 브레인스토밍 및 설계 문서 작성
- 작성자(팀원): pjj
- 목표: PIPELINE.MD를 분석해 구현 가능한 설계로 구체화
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "PIPELINE.MD 파일을 토대로 plan 계획을 세워주고, 구현 단계 까지 검토 해줘. 구현 실행은 하지 말고"
- 사용한 기법: (c) superpowers:brainstorming 스킬
- 결과:
  - CLI 변수 지정 방식(`--var-a`, `--var-b`) 확정
  - 출력물: CSV + PNG + report.md 방식 결정
  - 모듈형 패키지 방식(src/ 분리) 채택
  - 설계 문서 저장: `docs/superpowers/specs/2026-06-30-nc-validation-pipeline-design.md`
- 막힘 → 해결: 없음

---
### [#2] 구현 계획서(Plan) 작성
- 작성자(팀원): pjj
- 목표: 9개 태스크로 분리된 TDD 구현 계획서 작성
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "그냥 앞으로 다 권장 사항으로 계획을 실행해줘"
- 사용한 기법: (c) superpowers:writing-plans 스킬
- 결과:
  - 9개 태스크, 각 태스크별 실제 코드 포함한 TDD 계획서 작성
  - 계획서 저장: `docs/superpowers/plans/2026-06-30-nc-validation-pipeline.md`
  - 전체 파일 구조 확정: src/io_nc.py, inspect_nc.py, qc.py, reproject.py, resample.py, metrics.py, visualize.py, pipeline.py + run_validation.py
- 막힘 → 해결: 없음

---
### [#3] Task 1: 프로젝트 스캐폴딩 + io_nc.py 구현
- 작성자(팀원): pjj
- 목표: src/ 디렉토리 구조, 공유 픽스처(conftest.py), NC 입력 검증 모듈 구현
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "task9까지 계속해서 진행해줘" (서브에이전트 주도 개발 방식 선택: "1")
- 사용한 기법: (a) 서브에이전트(구현 에이전트 + 리뷰 에이전트 분리)
- 결과:
  - `src/__init__.py`, `src/io_nc.py` — `open_nc(path) -> xr.Dataset`
  - `tests/conftest.py` — nc_high_res(0.05°), nc_low_res(0.25°), nc_with_fillvalue 픽스처
  - `tests/test_io_nc.py` — 3개 테스트
  - 커밋: 37c0255
- 막힘 → 해결: conda env `ncval` 미설치 → 코드 정합성 수동 리뷰로 대체

---
### [#4] Task 2: inspect_nc.py — NC 파악 모듈 구현
- 작성자(팀원): pjj
- 목표: 자료유형·격자·해상도·투영 자동 판별 기능
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "앞으로 yes로 계속진행해"
- 사용한 기법: (a) 서브에이전트
- 결과:
  - `src/inspect_nc.py` — `is_regular_grid()`, `inspect()` 구현
  - `tests/test_inspect_nc.py` — 5개 테스트
  - 커밋: 4836a42
- 막힘 → 해결: 없음

---
### [#5] Task 3: qc.py — 속성 기반 QC 모듈 구현
- 작성자(팀원): pjj
- 목표: FillValue·valid_range·QC flag 기반 NaN 마스킹
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "task9까지 모두 yes로 진행해줘"
- 사용한 기법: (a) 서브에이전트
- 결과:
  - `src/qc.py` — `apply_qc(ds, var) -> xr.DataArray`
  - `tests/test_qc.py` — 4개 테스트
  - 커밋: 2505f2d
- 막힘 → 해결: 없음

---
### [#6] Task 4: reproject.py — WGS84 표준화 + 분석 영역 리샘플
- 작성자(팀원): pjj
- 목표: 경도 정규화, WGS84 재투영, 분석 영역(24~38N, 117~131E) 목표 격자로 interp
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "task9까지 계속해서 진행해줘"
- 사용한 기법: (a) 서브에이전트
- 결과:
  - `src/reproject.py` — `to_wgs84_region(da, info) -> xr.DataArray`
  - 비정규격자 `NotImplementedError`로 처리
  - `tests/test_reproject.py` — 4개 테스트
  - 커밋: b034cd8
- 막힘 → 해결: 없음

---
### [#7] Task 5: resample.py — 저해상도 기준 해상도 정합
- 작성자(팀원): pjj
- 목표: rioxarray.reproject_match(Resampling.average)로 고해상도→저해상도 면적집계
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "task9까지 계속해서 진행해줘"
- 사용한 기법: (a) 서브에이전트
- 결과:
  - `src/resample.py` — `match_resolution(da_a, da_b) -> (coarse, fine_resampled, label)`
  - `tests/test_resample.py` — 4개 테스트
  - 커밋: 7eb90b7
- 막힘 → 해결: 없음

---
### [#8] Task 6: metrics.py — 통계량 6개 계산
- 작성자(팀원): pjj
- 목표: N, Bias(eval-ref), RMSE, MAE, R, R² 계산. NaN 셀 제외, scipy.stats.linregress 사용
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "task9까지 계속해서 진행해줘"
- 사용한 기법: (a) 서브에이전트
- 결과:
  - `src/metrics.py` — `compute_stats(ref, eval_da) -> dict`
  - `tests/test_metrics.py` — 5개 테스트
  - 커밋: 11bdc5e
- 막힘 → 해결: 없음

---
### [#9] Task 7: visualize.py — 단계별 PNG 저장
- 작성자(팀원): pjj
- 목표: cartopy 지도(save_map), 산점도(save_scatter), 비교표(save_compare_table) 저장
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "task9까지 계속해서 진행해줘"
- 사용한 기법: (a) 서브에이전트
- 결과:
  - `src/visualize.py` — 3개 함수
  - 리뷰에서 파일 크기 검증 누락 발견 → 픽스 후 재승인
  - `tests/test_visualize.py` — 3개 테스트
  - 커밋: 54e9545 + 5c04c22(픽스)
- 막힘 → 해결: 리뷰 에이전트가 `getsize()` 누락 발견 → 픽스 에이전트로 수정

---
### [#10] Task 8: pipeline.py — 전체 오케스트레이션 + report.md 생성
- 작성자(팀원): pjj
- 목표: [1]~[5] 단계 순차 실행, 7장 PNG + CSV + report.md 자동 생성
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "task9까지 모두 yes로 진행해줘"
- 사용한 기법: (a) 서브에이전트
- 결과:
  - `src/pipeline.py` — `run(cfg) -> {"report", "csv", "figures"}`
  - 고→저(권장) + 저→고(비교) 양방향 통계 수행
  - `tests/test_pipeline.py` — 3개 테스트
  - 커밋: c0c3eab
- 막힘 → 해결: 없음

---
### [#11] Task 9: run_validation.py — CLI 진입점 + 통합 테스트
- 작성자(팀원): pjj
- 목표: `python run_validation.py A.nc B.nc --var-a sss --var-b sss_smap` CLI 완성
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "task9 까지 계속해서 진행해줘"
- 사용한 기법: (a) 서브에이전트
- 결과:
  - `run_validation.py` — argparse CLI, 예외처리 후 exit code 0/1 반환
  - `tests/test_cli.py` — 3개 테스트 (help, 잘못된 확장자, end-to-end)
  - 커밋: ff0ac41
- 막힘 → 해결: 없음

---

## 마무리 요약 (1~2줄)
- 가장 효과적이었던 에이전트 활용법: **서브에이전트 분리**(구현 에이전트 + 리뷰 에이전트를 태스크별로 독립 실행) — 구현 오류를 즉시 탐지·수정해 품질이 크게 향상됨
- 다른 팀이 그대로 따라 하려면 필요한 것: superpowers 플러그인, PIPELINE.MD 수준의 상세 설계 문서, conda env `ncval` (`environment.yml`로 설치)
