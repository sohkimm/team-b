import os
import pytest
from src.pipeline import run


def test_pipeline_creates_outputs(nc_high_res, nc_low_res, tmp_path):
    path_a, _ = nc_high_res
    path_b, _ = nc_low_res
    cfg = {
        "file_a": path_a,
        "file_b": path_b,
        "var_a": "sss",
        "var_b": "sss_smap",
        "outdir": str(tmp_path / "results"),
    }
    result = run(cfg)
    assert os.path.exists(result["report"])
    assert os.path.exists(result["csv"])
    assert os.path.isdir(result["figures"])


def test_pipeline_figures_exist(nc_high_res, nc_low_res, tmp_path):
    path_a, _ = nc_high_res
    path_b, _ = nc_low_res
    cfg = {
        "file_a": path_a,
        "file_b": path_b,
        "var_a": "sss",
        "var_b": "sss_smap",
        "outdir": str(tmp_path / "results"),
    }
    result = run(cfg)
    fig_dir = result["figures"]
    expected = [
        "step3_wgs84_A.png", "step3_wgs84_B.png",
        "step4_resampled_A.png", "step4_resampled_B.png",
        "step5_hilo.png", "step5_lohi.png", "step5_compare.png",
    ]
    for fname in expected:
        assert os.path.exists(os.path.join(fig_dir, fname)), f"누락: {fname}"


def test_pipeline_invalid_var_raises(nc_high_res, nc_low_res, tmp_path):
    path_a, _ = nc_high_res
    path_b, _ = nc_low_res
    cfg = {
        "file_a": path_a,
        "file_b": path_b,
        "var_a": "nonexistent_var",
        "var_b": "sss_smap",
        "outdir": str(tmp_path / "results"),
    }
    with pytest.raises(KeyError):
        run(cfg)
