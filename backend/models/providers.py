"""
Unified LLM interface supporting OpenAI, Anthropic, and Ollama.
All generators yield string chunks for WebSocket streaming.
"""

from typing import Generator, Optional
import requests
import config


def _resolve_model(agent: str, provider: str, model_override: Optional[str] = None) -> str:
    """Return the model string for a given agent + provider."""
    if model_override:
        return model_override
    override = config.AGENT_MODELS.get(agent, "")
    if override:
        return override
    return {
        "openai":    config.OPENAI_MODEL,
        "anthropic": config.ANTHROPIC_MODEL,
        "ollama":    config.OLLAMA_MODEL,
    }.get(provider, config.OLLAMA_MODEL)


def stream_openai(
    prompt: str,
    agent: str = "pm",
    system: str = "",
    model_override: Optional[str] = None,
) -> Generator[str, None, None]:
    """Stream via the Responses API — the endpoint purpose-built for reasoning
    models. We pass a per-agent `reasoning.effort` and use `max_output_tokens`;
    `temperature` and penalties are intentionally omitted (reasoning models
    reject or ignore them). If a model doesn't accept the `reasoning` param we
    gracefully retry without it."""
    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    model = _resolve_model(agent, "openai", model_override)

    kwargs = {
        "model": model,
        "input": prompt,
        "max_output_tokens": config.MAX_TOKENS_AGENT,
        "stream": True,
    }
    if system:
        kwargs["instructions"] = system

    effort = config.AGENT_REASONING_EFFORT.get(agent)
    try:
        stream = client.responses.create(**kwargs, reasoning={"effort": effort} if effort else {})
    except Exception:
        # Model doesn't support reasoning effort (e.g. a non-reasoning model) —
        # retry without it rather than failing the agent.
        stream = client.responses.create(**kwargs)

    for event in stream:
        if getattr(event, "type", "") == "response.output_text.delta":
            yield event.delta


def stream_anthropic(
    prompt: str,
    agent: str = "pm",
    system: str = "",
    model_override: Optional[str] = None,
) -> Generator[str, None, None]:
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    model = _resolve_model(agent, "anthropic", model_override)

    # Prompt caching: the system prompt is stable across every call for an
    # agent, so mark it with cache_control to read it back at ~10% of input
    # cost on subsequent requests instead of re-billing it each time.
    system_blocks = [{
        "type": "text",
        "text": system or "You are a helpful AI assistant.",
        "cache_control": {"type": "ephemeral"},
    }]

    with client.messages.stream(
        model=model,
        max_tokens=config.MAX_TOKENS_AGENT,
        system=system_blocks,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def stream_ollama(
    prompt: str,
    agent: str = "pm",
    system: str = "",
    model_override: Optional[str] = None,
) -> Generator[str, None, None]:
    import json
    model = _resolve_model(agent, "ollama", model_override)
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    temperature = 0.2 if agent == "senior_dev" else 0.6
    timeout = 600 if agent == "senior_dev" else 180
    options = {
        "temperature": temperature,
        "num_predict": config.MAX_TOKENS_AGENT,
        "num_ctx": config.OLLAMA_NUM_CTX,
    }
    if config.OLLAMA_NUM_THREAD:
        options["num_thread"] = config.OLLAMA_NUM_THREAD

    payload = {
        "model":   model,
        "prompt":  full_prompt,
        "stream":  True,
        "options": options,
    }
    if config.OLLAMA_KEEP_ALIVE is not None:
        keep = config.OLLAMA_KEEP_ALIVE.strip()
        if keep == "0":
            payload["keep_alive"] = 0
        elif keep:
            payload["keep_alive"] = keep
    resp = requests.post(
        f"{config.OLLAMA_BASE_URL}/api/generate",
        json=payload,
        stream=True,
        timeout=timeout,
    )
    if resp.status_code == 404:
        try:
            detail = resp.json().get("error") or resp.text
        except Exception:
            detail = resp.text
        if "not found" in str(detail).lower():
            raise RuntimeError(ollama_model_error_message(model)) from None
        raise RuntimeError(f"Ollama request failed ({resp.status_code}): {detail}") from None
    resp.raise_for_status()
    for line in resp.iter_lines():
        if line:
            data = json.loads(line)
            token = data.get("response", "")
            if token:
                yield token
            if data.get("done"):
                break


def stream_response(
    prompt: str,
    provider: str,
    agent: str = "pm",
    system: str = "",
    model: Optional[str] = None,
) -> Generator[str, None, None]:
    """Route to the correct provider."""
    if provider == "openai":
        yield from stream_openai(prompt, agent, system, model_override=model)
    elif provider == "anthropic":
        yield from stream_anthropic(prompt, agent, system, model_override=model)
    else:
        yield from stream_ollama(prompt, agent, system, model_override=model)


# ── Ollama model management ────────────────────────────────────────────────────

def ollama_list_models() -> list:
    try:
        r = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        return r.json().get("models", [])
    except Exception:
        return []


def ollama_model_error_message(requested: str) -> str:
    """Human-readable hint when a requested Ollama tag is missing."""
    info = ollama_missing_info(requested)
    return info["message"]


def ollama_missing_info(requested: str) -> dict:
    """Structured payload for UI when an Ollama model is not installed."""
    from models.model_catalog import OLLAMA_CODING_MODELS, lookup_model_display

    installed = ollama_list_models()
    names = [m.get("name") for m in installed if m.get("name")]
    base = (requested or "").split(":")[0].lower()
    pull_cmd = f"ollama pull {base}" if base else "ollama pull codestral"
    display = lookup_model_display(requested) or requested or "model"
    ram_hint = ""
    for row in OLLAMA_CODING_MODELS:
        if row.get("id", "").split(":")[0].lower() == base:
            pull_cmd = row.get("pull") or pull_cmd
            display = row.get("display") or display
            ram_hint = row.get("ram_hint") or ""
            break
    pull_tag = pull_cmd.replace("ollama pull ", "").strip() if pull_cmd.startswith("ollama pull ") else base
    return {
        "code": "ollama_model_missing",
        "model": requested or "",
        "pull_tag": pull_tag or base,
        "pull_command": pull_cmd,
        "display": display,
        "ram_hint": ram_hint,
        "installed_models": names,
        "message": (
            f"Ollama model '{requested}' is not installed locally. "
            f"Installed: {', '.join(names) or 'none'}. "
            f"Install with: {pull_cmd}"
        ),
    }


def resolve_ollama_model(requested: str | None = None, *, allow_fallback: bool = False) -> str:
    """Return an installed Ollama tag for the requested catalog id or name."""
    from models.model_catalog import _find_installed_variant
    from models.coding_agents import pick_best_installed

    installed = ollama_list_models()
    if requested:
        variant = _find_installed_variant(requested, installed)
        if variant:
            return variant["name"]
        exact = {(m.get("name") or "").lower(): m.get("name") for m in installed}
        hit = exact.get(requested.lower())
        if hit:
            return hit

    if allow_fallback or not requested:
        fallback = (
            pick_best_installed(installed)
            or config.SENIOR_DEV_MODEL
            or config.OLLAMA_MODEL
        )
        if fallback:
            variant = _find_installed_variant(fallback, installed)
            if variant:
                return variant["name"]
            exact = {(m.get("name") or "").lower(): m.get("name") for m in installed}
            hit = exact.get(str(fallback).lower())
            if hit:
                return hit

    raise RuntimeError(ollama_model_error_message(requested or "default"))


def ollama_pull_model(model_name: str) -> Generator[str, None, None]:
    """Stream pull progress for a model."""
    import json
    payload = {"name": model_name, "stream": True}
    resp = requests.post(
        f"{config.OLLAMA_BASE_URL}/api/pull",
        json=payload,
        stream=True,
        timeout=600,
    )
    resp.raise_for_status()
    for line in resp.iter_lines():
        if line:
            data = json.loads(line)
            status = data.get("status", "")
            total  = data.get("total", 0)
            completed = data.get("completed", 0)
            pct = int(completed / total * 100) if total else 0
            yield json.dumps({"status": status, "pct": pct})


def ollama_delete_model(model_name: str) -> bool:
    try:
        r = requests.delete(
            f"{config.OLLAMA_BASE_URL}/api/delete",
            json={"name": model_name},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def _system_total_ram_bytes() -> int:
    """Best-effort total system RAM (macOS/Linux)."""
    import platform
    import subprocess

    try:
        if platform.system() == "Darwin":
            return int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
        if platform.system() == "Linux":
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) * 1024
    except Exception:
        pass
    return 0


CONTEXT_OVERHEAD_BYTES = 2 * 1024 ** 3


def ollama_memory_status(model: str | None = None, in_progress: int = 0) -> dict:
    """Return loaded model memory, installed disk footprint, system RAM, and budget."""
    running = []
    loaded_bytes = 0
    error = None

    try:
        r = requests.get(f"{config.OLLAMA_BASE_URL}/api/ps", timeout=5)
        r.raise_for_status()
        for model_row in r.json().get("models", []):
            vram = model_row.get("size_vram") or model_row.get("size") or 0
            loaded_bytes += vram
            running.append({
                "name": model_row.get("name", ""),
                "size_bytes": model_row.get("size") or 0,
                "vram_bytes": vram,
                "context_length": model_row.get("context_length"),
            })
    except Exception as e:
        error = str(e)

    installed_bytes = sum(m.get("size", 0) for m in ollama_list_models())
    system_ram = _system_total_ram_bytes()
    loaded_pct = round(loaded_bytes / system_ram * 100, 1) if system_ram and loaded_bytes else 0

    in_progress = max(0, int(in_progress or 0))
    per_ticket_bytes = 0
    model_display = ""
    budgeted_bytes = loaded_bytes
    reserve_bytes = 0

    if model:
        from models.model_catalog import estimate_model_ram_bytes, lookup_model_display

        per_ticket_bytes = estimate_model_ram_bytes(model, running)
        model_display = lookup_model_display(model)
        if in_progress > 0 and per_ticket_bytes:
            if in_progress == 1:
                budgeted_bytes = max(loaded_bytes, per_ticket_bytes)
            else:
                budgeted_bytes = max(
                    loaded_bytes,
                    per_ticket_bytes + (in_progress - 1) * CONTEXT_OVERHEAD_BYTES,
                )
            reserve_bytes = max(0, budgeted_bytes - loaded_bytes)

    remaining_bytes = max(0, system_ram - budgeted_bytes) if system_ram else 0
    budget_pct = round(budgeted_bytes / system_ram * 100, 1) if system_ram and budgeted_bytes else 0

    return {
        "available": error is None,
        "error": error,
        "loaded_bytes": loaded_bytes,
        "installed_bytes": installed_bytes,
        "system_ram_bytes": system_ram,
        "loaded_pct": loaded_pct,
        "running": running,
        "model": model or "",
        "model_display": model_display or model or "",
        "in_progress": in_progress,
        "per_ticket_bytes": per_ticket_bytes,
        "context_overhead_bytes": CONTEXT_OVERHEAD_BYTES,
        "budgeted_bytes": budgeted_bytes,
        "reserve_bytes": reserve_bytes,
        "remaining_bytes": remaining_bytes,
        "budget_pct": budget_pct,
    }
