"""ai-web-team backend — FastAPI entry point."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database as db
from routes.projects import router as projects_router
from routes.models   import router as models_router
from routes.ws       import router as ws_router

app = FastAPI(title="ai-web-team API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
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
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 3001)), reload=True)
