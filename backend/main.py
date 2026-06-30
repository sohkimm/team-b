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

# 로컬 dev origin + 배포 프론트 origin(환경변수).
# FRONTEND_ORIGIN 은 콤마로 여러 개 지정 가능 (예: Vercel 프리뷰 + 프로덕션).
_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_env_origins = [o.strip() for o in os.environ.get("FRONTEND_ORIGIN", "").split(",") if o.strip()]
allow_origins = _default_origins + _env_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
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

    # SSE: 프록시 버퍼링 비활성화(X-Accel-Buffering) + 캐시 금지 → 이벤트 즉시 전달.
    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)
