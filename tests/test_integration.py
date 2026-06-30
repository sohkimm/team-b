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
