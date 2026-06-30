"""FastAPI 백엔드 — NetCDF 2개 → 단계별(SSE) 비교 결과 스트림.

실행:
  ./.venv/bin/uvicorn backend.main:app --reload --port 8000   (프로젝트 루트에서)
"""
import json
import os
import sys
import tempfile

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.web_stream import analyze_stream  # noqa: E402

DEMO_A = os.path.join(ROOT, "dataset-sss-ssd-nrt-daily_20260101T1200Z_P20260122T0000Z.nc")
DEMO_B = os.path.join(ROOT, "SMAP_L3_SSS_20260101_8DAYS_V5.0.nc")

app = FastAPI(title="NC Validation Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


def _format_sse(ev):
    return f"event: {ev['event']}\ndata: {json.dumps(ev['data'])}\n\n"


async def _save_upload(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1] or ".nc"
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(await upload.read())
    return path


@app.post("/api/analyze")
async def api_analyze(
    file_a: UploadFile = File(None),
    file_b: UploadFile = File(None),
    demo: str = Form("false"),
):
    tmp = []
    if demo == "true":
        path_a, path_b = DEMO_A, DEMO_B
    else:
        path_a = await _save_upload(file_a)
        path_b = await _save_upload(file_b)
        tmp = [path_a, path_b]

    def gen():
        try:
            for ev in analyze_stream(path_a, path_b):
                yield _format_sse(ev)
        finally:
            for p in tmp:
                try:
                    os.remove(p)
                except OSError:
                    pass

    return StreamingResponse(gen(), media_type="text/event-stream")
