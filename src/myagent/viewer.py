from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .store import RunStore
from .workspace import Workspace


def create_app(root: Path) -> FastAPI:
    store = RunStore(root)
    workspace = Workspace(root, store)
    app = FastAPI(title="MyAgent Run Studio", version=__version__)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"]
    )

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        if request.url.path in {"/docs", "/redoc"}:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'"
            )
        return response

    @app.exception_handler(ValueError)
    async def invalid(request: Request, exc: ValueError):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "version": __version__,
            "workspace": root.resolve().name,
            "read_only": True,
        }

    @app.get("/api/runs")
    def runs():
        return [
            {
                "id": run.id,
                "task": run.task,
                "status": run.status,
                "updated_at": run.updated_at,
                "provider": run.provider,
            }
            for run in store.list_runs()
        ]

    @app.get("/api/runs/{run_id}")
    def detail(run_id: str):
        run = store.load(run_id)
        # Do not expose the local absolute workspace or endpoint/credentials in the web presentation.
        data = run.model_dump(exclude={"workspace", "base_url", "messages", "pending_action"})
        return {
            "run": data,
            "events": store.events(run.id),
            "changes": store.diff(run.id, workspace.resolve),
            "has_pending_action": run.pending_action is not None,
        }

    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(static / "index.html")

    return app
