# PROCESS_LOG — 작업 기록 (과정 70점의 핵심 근거)

> 표준 헤더(CLAUDE.md 등)를 로드했다면 에이전트가 알아서 채워 줍니다. 비면 직접 채우세요.
> 원칙: **실제로 시킨 프롬프트를 그대로 인용**할 것. 요약만 있으면 점수가 깎입니다.

## 작성자 정보 (개인별 로그 — 본인 것만)
- 팀명:
- 본인 이름(작성자):
- 공통과제(우리 팀이 자동화한 반복 수작업):
- 내가 맡은 부분:
- 자유과제(있으면):

> **이 로그는 본인 것만 작성**합니다. 각자 자기 PC·계정으로 작업해 개인 로그를 남기고, 제출 시 **영문 파일명** `<팀영문명>_<이름로마자>_PROCESS_LOG.md`(예: `teamA_kim_PROCESS_LOG.md`)로 저장하세요. **한글 파일명은 압축 시 깨지므로 금지** — 한글 팀명·이름은 위 '작성자 정보'에 적습니다. 운영자가 팀별로 모아 채점합니다(전원 참여 = 팀별 개인 로그 수).

## 효과 측정 (Before → After, 결과 ⑥ 채점용 — 형식 자유)
> **지표는 자기 업무에 맞게 고름 — 강제 항목 없음.** (예시, 해당되는 것만) 소요 시간 · 반복 횟수 · 다루는 자료/파일 수 · 손 가는 단계 수 · 품질·일관성 · 오류/누락 · 커버리지 등. 정량이 어려우면 정성도 인정.

| 지표(자기 업무에 맞게) | Before(기존 수작업) | After(에이전트화) |
|------|------|------|
|  |  |  |
|  |  |  |

## 사용 기법 (권장·가점, 필수 아님)
- [ ] (a) 서브에이전트 / 역할 분담
- [ ] (b) 외부 도구·데이터 연동 (파일/API/MCP/사내데이터)
- [ ] (c) 재사용 산출물 (스킬 / 프롬프트셋 / CLAUDE.md / 서브에이전트 구성)

---

## 작업 로그 (단계마다 1개씩 누적 / 시간순)

### [#1] Task 5: resample.py — 해상도 정합
- 작성자(팀원): Claude (AI Agent)
- 목표: 저해상도 기준으로 고해상도 데이터를 다운샘플링하는 resample.py 모듈 구현
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "Implement Task 5 of a NetCDF validation pipeline. This task adds resolution matching: resampling the high-res DataArray to match the coarser one using rioxarray."
- 사용한 기법(있으면): (c) 재사용산출물 — Task 4 (reproject.py) 의존 구조 활용
- 결과:
  - `src/resample.py` 생성 (93줄) — `match_resolution(da_a, da_b)` 함수 구현
  - `tests/test_resample.py` 생성 (44줄) — 4개 테스트 케이스
    - Resolution detection (양방향): A vs B 중 누가 coarse인지 판단
    - Output shape matching: 재샘플링된 그리드 크기 검증
    - Dimension preservation: lat/lon 이름 유지
  - 커밋: `7eb90b7` (git log)
  - 태스크 보고: `.superpowers/sdd/task-5-report.md`
- 막힘 → 해결: 
  - 환경 제약: conda env `ncval` 미탑재 → 테스트 코드 구조 검증, 예상 결과 문서화로 해결
  - 배경: rioxarray.reproject_match(Resampling.average) 사용으로 영역 가중 평균 적용

---

## 마무리 요약 (1~2줄)
- 가장 효과적이었던 에이전트 활용법:
- 다른 팀이 그대로 따라 하려면 필요한 것:
