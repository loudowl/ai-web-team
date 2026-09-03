"""Routes for Ollama model management."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models.providers import ollama_list_models, ollama_pull_model, ollama_delete_model, ollama_memory_status, resolve_ollama_model, ollama_missing_info
from models.coding_agents import (
    get_recommended_models,
    get_excluded_models,
    pick_best_installed,
    is_excluded_model,
)
from models.model_catalog import get_provider_choices, validate_model_choice
import config

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
def list_models():
    """List all installed Ollama models plus configured remote providers."""
    ollama_models = ollama_list_models()
    return {
        "ollama": ollama_models,
        "providers": {
            "openai":    {"available": bool(config.OPENAI_API_KEY),    "model": config.OPENAI_MODEL},
            "anthropic": {"available": bool(config.ANTHROPIC_API_KEY), "model": config.ANTHROPIC_MODEL},
            "ollama":    {"available": True,                           "model": config.OLLAMA_MODEL},
        }
    }


@router.get("/ollama/memory")
def ollama_memory(
    model: str | None = Query(None, description="Project model for per-ticket budget"),
    in_progress: int = Query(0, ge=0, description="Tickets currently in the In Progress lane"),
):
    """Live Ollama RAM usage from /api/ps plus optional concurrent-ticket budget."""
    return ollama_memory_status(model=model, in_progress=in_progress)


@router.get("/ollama/check")
def check_ollama_model(model: str = Query(..., description="Catalog id or Ollama tag")):
    """Return whether a model is installed locally, plus pull metadata if missing."""
    try:
        tag = resolve_ollama_model(model, allow_fallback=False)
        return {"installed": True, "model": model, "tag": tag}
    except RuntimeError:
        return {**ollama_missing_info(model), "installed": False}


@router.get("/provider-choices")
def provider_model_choices():
    """Curated model options per provider for the New Project page."""
    return get_provider_choices()


@router.get("/coding-agents")
def list_coding_agents():
    """Recommended open-weights coding models + what's installed locally."""
    installed = ollama_list_models()
    recommended = get_recommended_models()
    excluded = get_excluded_models()
    best = pick_best_installed(installed)

    installed_clean = []
    for m in installed:
        name = m.get("name", "")
        installed_clean.append({
            **m,
            "excluded": is_excluded_model(name),
        })

    return {
        "recommended": recommended,
        "excluded_by_policy": excluded,
        "installed": installed_clean,
        "best_for_jira_mode": best,
        "jira_api_configured": bool(config.JIRA_BASE_URL and config.JIRA_EMAIL and config.JIRA_API_TOKEN),
    }


class PullRequest(BaseModel):
    model: str


@router.post("/pull")
def pull_model(req: PullRequest):
    """Stream Ollama model pull progress (SSE-style)."""
    def _generate():
        try:
            for chunk in ollama_pull_model(req.model):
                yield f"data: {chunk}\n\n"
            yield "data: {\"status\":\"complete\"}\n\n"
        except Exception as e:
            yield f"data: {{\"error\": \"{e}\"}}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")


class DeleteRequest(BaseModel):
    model: str


@router.delete("")
def delete_model(req: DeleteRequest):
    ok = ollama_delete_model(req.model)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete model")
    return {"deleted": req.model}
