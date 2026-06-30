import subprocess
import sys
import os
import pathlib
import pytest

# Project root is one level above this file (tests/)
PROJECT_ROOT = str(pathlib.Path(__file__).parent.parent)


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "run_validation.py", "--help"],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0
    assert "--var-a" in result.stdout


def test_cli_invalid_extension(tmp_path):
    bad_file = tmp_path / "data.txt"
    bad_file.write_text("not nc")
    result = subprocess.run(
        [sys.executable, "run_validation.py",
         str(bad_file), str(bad_file),
         "--var-a", "sss", "--var-b", "sss",
         "--outdir", str(tmp_path / "out")],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode != 0
    assert "NetCDF" in result.stderr or "NetCDF" in result.stdout


def test_cli_end_to_end(nc_high_res, nc_low_res, tmp_path):
    path_a, _ = nc_high_res
    path_b, _ = nc_low_res
    outdir = str(tmp_path / "results")
    result = subprocess.run(
        [sys.executable, "run_validation.py",
         path_a, path_b,
         "--var-a", "sss", "--var-b", "sss_smap",
         "--outdir", outdir],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert os.path.exists(os.path.join(outdir, "report.md"))
    assert os.path.exists(os.path.join(outdir, "tables", "stats.csv"))
