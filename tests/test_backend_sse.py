import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app, _format_sse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CM = os.path.join(ROOT, "dataset-sss-ssd-nrt-daily_20260101T1200Z_P20260122T0000Z.nc")
HAVE = os.path.exists(CM)
client = TestClient(app)


def test_format_sse():
    assert _format_sse({"event": "step", "data": {"n": 1, "status": "active"}}) == \
        'event: step\ndata: {"n": 1, "status": "active"}\n\n'


def test_health():
    assert client.get("/api/health").json() == {"ok": True}


@pytest.mark.skipif(not HAVE, reason="demo .nc absent")
def test_analyze_demo():
    r = client.post("/api/analyze", data={"demo": "true"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    body = r.text
    assert '"n": 5, "status": "done"' in body
    assert body.rstrip().endswith('data: {"ok": true}')
