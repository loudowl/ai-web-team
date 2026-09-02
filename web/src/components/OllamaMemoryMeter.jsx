import { useEffect, useState } from 'react';
import { getOllamaMemory } from '../services/api';

function formatGB(bytes) {
  if (!bytes) return '0 GB';
  return `${(bytes / 1e9).toFixed(1)} GB`;
}

function meterColor(pct) {
  if (pct >= 75) return '#f85149';
  if (pct >= 50) return '#d29922';
  return '#3fb950';
}

export default function OllamaMemoryMeter({ pollMs = 4000 }) {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const load = () => {
      getOllamaMemory()
        .then(data => {
          if (cancelled) return;
          setStats(data);
          setError(data.available ? null : data.error || 'Ollama unreachable');
        })
        .catch(e => {
          if (!cancelled) setError(e.message || 'Failed to load memory stats');
        });
    };

    load();
    const id = setInterval(load, pollMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [pollMs]);

  if (error) {
    return (
      <div className="memory-meter memory-meter-error">
        <div className="memory-meter-label">Ollama memory</div>
        <div className="hint">{error}</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="memory-meter">
        <div className="center-row" style={{ padding: 12 }}><span className="spinner blue" /></div>
      </div>
    );
  }

  const pct = stats.loaded_pct || 0;
  const fill = stats.system_ram_bytes
    ? Math.min(100, pct)
    : stats.loaded_bytes
      ? Math.min(100, (stats.loaded_bytes / 32e9) * 100)
      : 0;
  const color = meterColor(fill);
  const loadedLabel = formatGB(stats.loaded_bytes);
  const totalLabel = stats.system_ram_bytes ? formatGB(stats.system_ram_bytes) : 'system RAM';
  const status = stats.running?.length
    ? `${stats.running.length} model${stats.running.length === 1 ? '' : 's'} loaded`
    : 'Idle — no models loaded';

  return (
    <div className="memory-meter">
      <div className="memory-meter-header">
        <div>
          <div className="memory-meter-label">Ollama memory</div>
          <div className="memory-meter-value">
            <span style={{ color }}>{loadedLabel}</span>
            {stats.system_ram_bytes ? (
              <span className="memory-meter-total"> / {totalLabel} system</span>
            ) : null}
          </div>
        </div>
        <div className="memory-meter-pct" style={{ color }}>{fill.toFixed(0)}%</div>
      </div>

      <div className="memory-bar" aria-label={`Ollama using ${loadedLabel}`}>
        <div className="memory-bar-fill" style={{ width: `${fill}%`, background: color }} />
      </div>

      <div className="memory-meter-meta">{status}</div>

      {stats.running?.length > 0 && (
        <div className="memory-model-list">
          {stats.running.map(m => (
            <div key={m.name} className="memory-model-row">
              <span className="memory-model-name">{m.name}</span>
              <span className="memory-model-size">{formatGB(m.vram_bytes || m.size_bytes)}</span>
            </div>
          ))}
        </div>
      )}

      {stats.installed_bytes > 0 && (
        <div className="hint" style={{ marginTop: 8 }}>
          {formatGB(stats.installed_bytes)} on disk across installed models
        </div>
      )}
    </div>
  );
}
