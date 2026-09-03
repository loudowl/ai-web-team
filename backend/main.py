"""ai-web-team backend — FastAPI entry point."""

from pathlib import Path

import config
import database as db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.models import router as models_router
from routes.projects import router as projects_router
from routes.board import router as board_router
from routes.board_global import router as board_global_router
from routes.ws import router as ws_router

app = FastAPI(title="ai-web-team API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(board_router)
app.include_router(board_global_router)
app.include_router(models_router)
app.include_router(ws_router)


@app.on_event("startup")
def on_startup():
    db.init()
    print("✅ ai-web-team backend ready")


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    backend_root = Path(__file__).resolve().parent
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.PORT,
        reload=config.RELOAD,
        # Watch Python package dirs only — never data/worktrees (Jira agent writes files there).
        reload_dirs=[
            str(backend_root / "agents"),
            str(backend_root / "routes"),
            str(backend_root / "models"),
            str(backend_root / "utils"),
        ],
        reload_excludes=[
            "data/worktrees/**",
            "data/*.db",
            "data/*.db-*",
        ],
    )
