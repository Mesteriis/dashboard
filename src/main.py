from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = BASE_DIR / "templates" / "index.html"

app = FastAPI(title="janus-dashboard")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root() -> Response:
    if not INDEX_FILE.exists():
        return PlainTextResponse(
            "Frontend build not found. Build frontend first (npm run build).",
            status_code=503,
        )
    return FileResponse(INDEX_FILE)
