import { API_URL } from '../services/api';

/** Parse axios/FastAPI error for structured Ollama missing-model payload. */
export function parseOllamaMissingError(err) {
  const detail = err?.response?.data?.detail;
  if (detail && typeof detail === 'object' && detail.code === 'ollama_model_missing') {
    return detail;
  }
  if (typeof detail === 'string' && detail.includes('not installed locally')) {
    const match = detail.match(/Ollama model '([^']+)'/);
    const model = match?.[1] || '';
    const base = model.split(':')[0];
    return {
      code: 'ollama_model_missing',
      model,
      pull_tag: base,
      pull_command: `ollama pull ${base}`,
      display: model,
      message: detail,
    };
  }
  return null;
}

/** Check model install status before launching a ticket run. */
export async function checkOllamaModel(model) {
  const resp = await fetch(
    `${API_URL}/api/models/ollama/check?${new URLSearchParams({ model })}`,
  );
  if (!resp.ok) throw new Error('Failed to check Ollama model');
  return resp.json();
}

/**
 * Stream Ollama model pull progress from the backend SSE endpoint.
 * Returns a promise that resolves on success or rejects on error/cancel.
 */
export function streamOllamaPull(model, { onProgress, signal } = {}) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (fn, value) => {
      if (settled) return;
      settled = true;
      fn(value);
    };

    fetch(`${API_URL}/api/models/pull`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model }),
      signal,
    })
      .then(async (resp) => {
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(text || `Pull failed (${resp.status})`);
        }
        const reader = resp.body?.getReader();
        if (!reader) throw new Error('Streaming not supported');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data:')) continue;
            try {
              const data = JSON.parse(line.slice(5).trim());
              if (data.error) throw new Error(data.error);
              if (data.status === 'complete') {
                onProgress?.({ status: 'Complete', pct: 100, done: true });
                finish(resolve, data);
                return;
              }
              onProgress?.({
                status: data.status || '',
                pct: data.pct || 0,
                done: false,
              });
            } catch (parseErr) {
              if (parseErr.message && parseErr.message !== 'Unexpected end of JSON input') {
                throw parseErr;
              }
            }
          }
        }
        finish(resolve, { status: 'complete' });
      })
      .catch((err) => {
        if (err.name === 'AbortError') {
          finish(reject, new Error('Download cancelled'));
          return;
        }
        finish(reject, err);
      });
  });
}
