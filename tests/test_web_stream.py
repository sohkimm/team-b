import os
import pytest
from src.web_stream import analyze_stream

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CM = os.path.join(ROOT, "dataset-sss-ssd-nrt-daily_20260101T1200Z_P20260122T0000Z.nc")
SM = os.path.join(ROOT, "SMAP_L3_SSS_20260101_8DAYS_V5.0.nc")
HAVE = os.path.exists(CM) and os.path.exists(SM)


@pytest.mark.skipif(not HAVE, reason="demo .nc absent")
def test_stream_lee():
    evs = list(analyze_stream(CM, SM))
    assert evs[-1]["event"] == "done"
    assert "error" not in [e["event"] for e in evs]
    done = {e["data"]["n"]: e["data"] for e in evs
            if e["event"] == "step" and e["data"]["status"] == "done"}
    assert set(done) == {1, 2, 3, 4, 5}
    assert done[2]["inspect"]["a"]["VAR"] == "sos"
    assert done[2]["inspect"]["b"]["VAR"] == "smap_sss"
    assert "cmems" in done[3]["maps"] and "smap" in done[3]["maps"]
    assert [m["label"] for m in done[5]["metrics"]] == ["N", "Bias", "RMSE", "MAE", "R", "R²"]
    sc = done[5]["scatter"]
    assert sc["hilo"]["stats"]["N"] == 1643   # lee average-resample 결과(회귀고정)
    assert sc["lohi"]["stats"]["N"] == 5704
    assert sc["hilo"]["refLabel"] == "SMAP" and sc["hilo"]["evalLabel"] == "CMEMS"
    assert sc["lohi"]["refLabel"] == "CMEMS" and sc["lohi"]["evalLabel"] == "SMAP"


def test_stream_bad_path():
    evs = list(analyze_stream("/no/a.nc", "/no/b.nc"))
    assert evs[-1]["event"] == "error"
