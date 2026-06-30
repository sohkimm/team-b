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
    # 기본 --grid both → 두 방식 별도 산점도 + 비교 테이블
    assert (out / "tables" / "stats_compare.csv").exists()
    figs = list((out / "figures").glob("scatter_*deg.png"))
    assert len(figs) == 2, f"두 방식 산점도 2개 기대, got {figs}"


def test_cli_single_grid(tmp_path):
    # 원래 방식(coarse)만 단독 산출도 가능
    out = tmp_path / "results"
    r = subprocess.run(
        [sys.executable, "run_validation.py", A, B, "--grid", "coarse", "--outdir", str(out)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (out / "tables" / "stats_compare.csv").exists()
    figs = list((out / "figures").glob("scatter_coarse_*deg.png"))
    assert len(figs) == 1
