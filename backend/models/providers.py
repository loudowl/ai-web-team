"""
Unified LLM interface supporting OpenAI, Anthropic, and Ollama.
All generators yield string chunks for WebSocket streaming.
"""

from typing import Generator, Optional
import requests
import config


def _resolve_model(agent: str, provider: str) -> str:
    """Return the model string for a given agent + provider."""
    override = config.AGENT_MODELS.get(agent, "")
    if override:
        return override
    return {
        "openai":    config.OPENAI_MODEL,
        "anthropic": config.ANTHROPIC_MODEL,
        "ollama":    config.OLLAMA_MODEL,
    }.get(provider, config.OLLAMA_MODEL)


def stream_openai(prompt: str, agent: str = "pm", system: str = "") -> Generator[str, None, None]:
    """Stream via the Responses API — the endpoint purpose-built for reasoning
    models. We pass a per-agent `reasoning.effort` and use `max_output_tokens`;
    `temperature` and penalties are intentionally omitted (reasoning models
    reject or ignore them). If a model doesn't accept the `reasoning` param we
    gracefully retry without it."""
    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    model = _resolve_model(agent, "openai")

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


def stream_anthropic(prompt: str, agent: str = "pm", system: str = "") -> Generator[str, None, None]:
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    model = _resolve_model(agent, "anthropic")

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


def stream_ollama(prompt: str, agent: str = "pm", system: str = "") -> Generator[str, None, None]:
    import json
    model = _resolve_model(agent, "ollama")
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    temperature = 0.2 if agent == "senior_dev" else 0.6
    timeout = 600 if agent == "senior_dev" else 180
    payload = {
        "model":   model,
        "prompt":  full_prompt,
        "stream":  True,
        "options": {
            "temperature": temperature,
            "num_predict": config.MAX_TOKENS_AGENT,
            "num_ctx": config.OLLAMA_NUM_CTX,
        },
    }
    resp = requests.post(
        f"{config.OLLAMA_BASE_URL}/api/generate",
        json=payload,
        stream=True,
        timeout=timeout,
    )
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
) -> Generator[str, None, None]:
    """Route to the correct provider."""
    if provider == "openai":
        yield from stream_openai(prompt, agent, system)
    elif provider == "anthropic":
        yield from stream_anthropic(prompt, agent, system)
    else:
        yield from stream_ollama(prompt, agent, system)


# ── Ollama model management ────────────────────────────────────────────────────

def ollama_list_models() -> list:
    try:
        r = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        return r.json().get("models", [])
    except Exception:
        return []


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
