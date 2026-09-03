import { useEffect, useState } from 'react';
import { getOllamaMemory } from '../services/api';
import { formatGB, meterColor } from '../utils/memoryFormat';

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

  const systemRam = stats.system_ram_bytes || 0;
  const budgetedBytes = stats.budgeted_bytes ?? stats.loaded_bytes ?? 0;
  const remainingBytes = stats.remaining_bytes
    ?? (systemRam ? Math.max(0, systemRam - budgetedBytes) : 0);
  const pct = systemRam
    ? Math.min(100, (budgetedBytes / systemRam) * 100)
    : stats.loaded_pct || 0;
  const color = meterColor(pct);
  const loadedLabel = formatGB(stats.loaded_bytes);
  const totalLabel = systemRam ? formatGB(systemRam) : 'system RAM';
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
            {systemRam ? (
              <span className="memory-meter-total"> / {totalLabel} system</span>
            ) : null}
          </div>
          {systemRam > 0 && (
            <div className="memory-meter-remaining">{formatGB(remainingBytes)} remaining</div>
          )}
        </div>
        <div className="memory-meter-pct" style={{ color }}>{pct.toFixed(0)}%</div>
      </div>

      <div className="memory-bar" aria-label={`Ollama using ${loadedLabel}`}>
        <div className="memory-bar-fill" style={{ width: `${pct}%`, background: color }} />
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
