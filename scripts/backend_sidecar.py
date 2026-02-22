from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Oko FastAPI backend as desktop sidecar")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-level", default="warning")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not getattr(sys, "frozen", False):
        script_path = Path(__file__).resolve()
        src_candidates = (
            script_path.parents[1] / "backend",
            script_path.parents[1],
            Path.cwd() / "backend",
            Path.cwd(),
        )
        src_dir = next((candidate for candidate in src_candidates if (candidate / "main.py").exists()), None)
        if src_dir is None:
            raise RuntimeError("Unable to resolve backend directory with main.py")

        src_dir_raw = os.fspath(src_dir)
        if src_dir_raw not in sys.path:
            sys.path.insert(0, src_dir_raw)

    from main import app as fastapi_app

    uvicorn.run(
        fastapi_app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=False,
        access_log=False,
    )


if __name__ == "__main__":
    main()
